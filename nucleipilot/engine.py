"""The v2 agent loop: profile -> decide -> authorize -> scan -> verify.

Wires the Phase-2 components (profiler, policy gate, scanner, verifier) under one
planner. Every proposal is independently authorized in code before anything runs,
the validation budget (with one slot reserved for a follow-up) is enforced here,
and every step is written to a trace. A stop switch can halt the loop at once.

The loop decides ONE validation at a time for up to `budget` rounds. Because only
one validation is committed per round and later rounds are reactive, the first
round never spends more than `budget - 1` -- the "reserve one slot for the
follow-up" rule -- and the LLM's later rounds see the evidence from earlier ones.

The engine never consults the sandbox answer key; it uses evidence only. Scoring
against ground truth happens separately in the experiment harness.
"""
from __future__ import annotations

import time

from . import policy, profiler, scanner, verifier


def _candidate(vid: str, endpoint: str, business_importance, catalog) -> dict:
    spec = catalog[vid]
    return {
        "validation": vid,
        "endpoint": endpoint,
        "business_importance": business_importance,
        "tech_severity": spec.severity,
        "indicator": spec.validates,
        "purpose": spec.purpose,
        "possible_false_positive": spec.possible_false_positive,
    }


def _build_pool(profile, catalog) -> list[dict]:
    pool = []
    for ep, info in profile.endpoints.items():
        bi = info.get("business_importance")
        for vid in info.get("candidate_validations", []):
            pool.append(_candidate(vid, ep, bi, catalog))
    return pool


def _finding_for_endpoint(ep, info, catalog, run_validations):
    """Resolve (indicator, issue, validation) for an endpoint, then build a Finding."""
    fired = info.get("fired_indicators", [])
    cands = info.get("candidate_validations", [])
    bi = info.get("business_importance")
    if cands:
        vid = next((c for c in cands if c in run_validations), cands[0])   # report the one actually run
        spec = catalog[vid]
        indicator, issue, validation, sev = spec.validates, spec.issue, vid, spec.severity
    elif fired:
        indicator = fired[0]
        issue = catalog[indicator].issue if indicator in catalog else None
        validation, sev = None, None
    else:
        indicator = issue = validation = sev = None
    vres = run_validations.get(validation) if validation else None
    return verifier.make_finding(
        endpoint=ep, issue=issue, indicator=indicator, indicator_fired=bool(fired),
        validation=validation, validation_result=vres, tech_severity=sev,
        business_importance=bi,
    )


def run(asset, catalog, planner, *, profile=None, nuclei_bin=None, scan_fn=None, should_stop=None):
    base_url = asset.get("base_url")
    scanner.assert_in_scope(base_url)                 # scope guard up front, always
    scan = scan_fn or (lambda t, p: scanner.run_template(t, p, nuclei_bin=nuclei_bin))
    if profile is None:
        profile = profiler.profile_target(asset, catalog, nuclei_bin=nuclei_bin)

    trace: list[dict] = []
    t0 = time.monotonic()
    pool = _build_pool(profile, catalog)
    exhaustive = getattr(planner, "exhaustive", False)
    budget = len(pool) if exhaustive else profile.budget
    context = {"base_url": base_url, "budget": profile.budget, "tech_facts": profile.tech_facts}

    run_validations: dict = {}     # vid -> ScanResult
    evidence: list = []            # for the LLM's evidence-aware later decisions
    rejections = 0
    budget_remaining = budget

    while budget_remaining > 0:
        if should_stop and should_stop():
            trace.append({"step": "stop_switch", "detail": {"halted": True}})
            break
        pending = [c for c in pool if c["validation"] not in run_validations]
        if not pending:
            break

        decision = planner.decide(pending, evidence, budget_remaining, context)
        trace.append({"step": "decision", "detail": {
            "planner": planner.name, "chosen": decision.chosen, "reason": decision.reason,
            "confidence": decision.confidence, "stop_reason": decision.stop_reason,
            "raw": decision.raw}})

        eligible = [c["validation"] for c in pending]
        pr = policy.validate_choice(decision.chosen, eligible, catalog)
        trace.append({"step": "policy", "detail": {
            "chosen": decision.chosen, "ok": pr.ok, "reason": pr.reason}})

        if decision.chosen is None:                   # planner chose to stop
            break
        if not pr.ok:                                 # blocked -> run nothing, fail safe
            rejections += 1
            trace.append({"step": "action", "detail": {
                "validation": decision.chosen, "executed": False, "blocked_reason": pr.reason}})
            break

        spec = catalog[decision.chosen]
        res = scan(base_url, policy.template_path(decision.chosen, catalog))
        run_validations[decision.chosen] = res
        budget_remaining -= spec.cost                 # validations cost 1
        status = verifier.verdict(True, res)
        evidence.append({"validation": decision.chosen, "endpoint": spec.endpoint,
                         "status": status, "matched": res.matched})
        trace.append({"step": "action", "detail": {
            "validation": decision.chosen, "endpoint": spec.endpoint, "executed": True,
            "status": status, "matched": res.matched, "matched_at": res.matched_at,
            "error": res.error}})

    findings = [_finding_for_endpoint(ep, info, catalog, run_validations)
                for ep, info in profile.endpoints.items()]
    trace.append({"step": "reassess", "detail": {"findings": [f.to_dict() for f in findings]}})
    elapsed = time.monotonic() - t0

    return {
        "planner": planner.name,
        "asset_id": asset.get("id"),
        "base_url": base_url,
        "budget": profile.budget,
        "exhaustive": exhaustive,
        "profile": profile.to_dict(),
        "findings": [f.to_dict() for f in findings],
        "chosen_order": [e["validation"] for e in evidence],
        "metrics": {
            "n_indicators_run": len(policy.indicators(catalog)),   # discovery runs all indicators
            "n_validations_run": len(run_validations),
            "validation_budget_used": sum(catalog[v].cost for v in run_validations),
            "policy_rejections": rejections,
            "decision_loop_elapsed_s": round(elapsed, 3),
        },
        "trace": trace,
    }
