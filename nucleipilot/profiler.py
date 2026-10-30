"""Context profiler: assembles the structured, per-endpoint context the planners
consume -- WITHOUT an LLM and WITHOUT raw page content.

Two steps, deliberately separated so the assembly is unit-testable without Nuclei:
  * discover(base_url, catalog)              -> runs the cheap indicator templates (cost 0)
  * build_profile(asset, catalog, discovery) -> pure function -> a Profile

The Profile is what the planner sees: for each endpoint, its business importance
(from the asset registry, set by a human), which indicators fired, and the
candidate validations available. Sending this structured summary -- not raw HTML
-- is also a security choice: the model never ingests raw target output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

from nucleipilot import policy, registry, scanner


@dataclass
class Profile:
    asset_id: str
    base_url: str
    budget: int
    endpoints: dict          # endpoint -> {business_importance, fired_indicators, candidate_validations}
    tech_facts: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "base_url": self.base_url,
            "budget": self.budget,
            "tech_facts": self.tech_facts,
            "endpoints": self.endpoints,
        }


def _endpoint_for_url(url: str, endpoints) -> str | None:
    """Longest-prefix match of a match URL's path to a registry endpoint."""
    path = urlsplit(url).path if "://" in (url or "") else (url or "")
    path = path.rstrip("/") or "/"
    best = None
    for ep in endpoints:
        if path == ep or path.startswith(ep.rstrip("/") + "/"):
            if best is None or len(ep) > len(best):
                best = ep
    return best


def discover(base_url: str, catalog: dict, *, nuclei_bin=None, **kw) -> dict:
    """Run every indicator (cost 0) against the target. Returns indicator_id -> ScanResult."""
    results = {}
    for ind in policy.indicators(catalog):
        results[ind.id] = scanner.run_template(
            base_url, policy.template_path(ind.id, catalog), nuclei_bin=nuclei_bin, **kw
        )
    return results


def build_profile(asset: dict, catalog: dict, discovery: dict, *, base_url=None, tech_facts=None) -> Profile:
    """Pure assembly: registry business context + catalog + discovery -> Profile."""
    eps = registry.endpoints(asset)
    prof = {
        ep: {
            "business_importance": meta.get("business_importance"),
            "fired_indicators": [],
            "candidate_validations": [],
        }
        for ep, meta in eps.items()
    }
    for ind_id, res in discovery.items():
        if not getattr(res, "matched", False):
            continue
        urls = [o.get("matched-at") or o.get("host") for o in (res.raw or [])]
        if not urls and getattr(res, "matched_at", None):
            urls = [res.matched_at]
        for url in urls:
            ep = _endpoint_for_url(url, prof.keys())
            if ep is None:
                continue
            if ind_id not in prof[ep]["fired_indicators"]:
                prof[ep]["fired_indicators"].append(ind_id)
            val = policy.validation_for_endpoint(ind_id, ep, catalog)
            if val and val.id not in prof[ep]["candidate_validations"]:
                prof[ep]["candidate_validations"].append(val.id)
    return Profile(
        asset_id=asset.get("id"),
        base_url=base_url or asset.get("base_url"),
        budget=registry.budget(asset),
        endpoints=prof,
        tech_facts=tech_facts or {},
    )


def profile_target(asset: dict, catalog: dict, *, nuclei_bin=None, **kw) -> Profile:
    """Convenience: discover + build_profile against a live target."""
    base_url = asset.get("base_url")
    disc = discover(base_url, catalog, nuclei_bin=nuclei_bin, **kw)
    return build_profile(asset, catalog, disc, base_url=base_url)


def profile_grafana(asset: dict, catalog: dict, *, base_url=None, timeout=5) -> Profile:
    """Fingerprint a real app (Grafana) via /api/health and present ALL catalog CVE
    candidates for the planner to reason over. Same Profile shape as the toy, so the
    SAME engine runs it -- a new target is just another asset + catalog. The detected
    version goes in tech_facts; the planner (or a rule) must decide which CVE applies.
    """
    import json as _json
    import urllib.request
    base = base_url or asset.get("base_url")
    version = None
    try:
        with urllib.request.urlopen(base.rstrip("/") + "/api/health", timeout=timeout) as r:
            version = _json.loads(r.read().decode("utf-8", "replace")).get("version")
    except Exception:
        version = None
    ep = next(iter(asset.get("endpoints", {"/": {}})), "/")
    candidates = [t.id for t in policy.validations(catalog)]
    endpoints = {ep: {
        "business_importance": registry.business_importance(asset, ep),
        "fired_indicators": ["grafana-version-indicator"],   # the fingerprint, not a Nuclei template
        "candidate_validations": candidates,
    }}
    return Profile(
        asset_id=asset.get("id"), base_url=base, budget=registry.budget(asset),
        endpoints=endpoints, tech_facts={"product": "grafana", "version": version},
    )
