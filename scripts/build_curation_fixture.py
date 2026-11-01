"""Build the E7 curation fixture by MECHANICALLY extracting metadata for every
Grafana-tagged CVE template from a real nuclei-templates corpus.

This exists so the fixture is auditable and reproducible: it is not hand-picked.
Point it at a local nuclei-templates checkout; it writes config/curation_corpus.json.

    python scripts/build_curation_fixture.py --corpus "C:/Users/you/nuclei-templates"

Selection rule (deliberately simple and stated): a template is included iff its
info.tags contains "grafana" AND it has a CVE id (info.classification.cve-id or a
CVE-named file). That is exactly the set a fair `-tags grafana` rule would gather,
restricted to version-bound CVEs. Only metadata is extracted (name, severity, tags,
description, cve-id) -- not the template logic -- since the experiment is about
SELECTION, not scanning.
"""
import os, sys, json, argparse, re

def norm_tags(t):
    if t is None:
        return []
    if isinstance(t, list):
        return [str(x).strip().lower() for x in t]
    return [x.strip().lower() for x in str(t).split(",") if x.strip()]

def main():
    ap = argparse.ArgumentParser(description="Extract Grafana-tagged CVE metadata into the curation fixture.")
    default_corpus = os.path.join(os.path.expanduser("~"), "nuclei-templates")
    ap.add_argument("--corpus", default=os.environ.get("NUCLEIPILOT_TEMPLATES_DIR", default_corpus),
                    help="path to a nuclei-templates checkout (default: ~/nuclei-templates)")
    ap.add_argument("--out", default=None, help="output JSON (default: config/curation_corpus.json)")
    args = ap.parse_args()

    try:
        import yaml
    except ImportError:
        print("PyYAML required (pip install -r requirements.txt)"); sys.exit(2)

    corpus = args.corpus
    if not os.path.isdir(corpus):
        print(f"corpus not found: {corpus}\nPass --corpus <path-to-nuclei-templates>."); sys.exit(2)

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = args.out or os.path.join(repo, "config", "curation_corpus.json")

    rows = []
    for root, _dirs, files in os.walk(corpus):
        for fn in files:
            if not fn.endswith((".yaml", ".yml")):
                continue
            p = os.path.join(root, fn)
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except Exception:
                continue
            if "grafana" not in text.lower():        # fast pre-filter
                continue
            try:
                data = yaml.safe_load(text)
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            info = data.get("info", {}) or {}
            tags = norm_tags(info.get("tags"))
            if "grafana" not in tags:                # fair `-tags grafana` membership
                continue
            cve = (info.get("classification", {}) or {}).get("cve-id")
            m = re.search(r"CVE-\d{4}-\d+", fn, re.I)
            if not cve and m:
                cve = m.group(0).upper()
            if not cve:                              # version-bound CVEs only
                continue
            rows.append({
                "id": data.get("id") or os.path.splitext(fn)[0],
                "file": os.path.relpath(p, corpus).replace("\\", "/"),
                "cve_id": cve.upper(),
                "name": (info.get("name") or "").strip(),
                "severity": (info.get("severity") or "").strip(),
                "tags": tags,
                "description": " ".join((info.get("description") or "").split()),
            })

    rows.sort(key=lambda r: r["cve_id"])
    doc = {
        "_comment": ("Grafana-tagged CVE templates, mechanically extracted by "
                     "scripts/build_curation_fixture.py (not hand-picked). Candidate pool a fair "
                     "`-tags grafana` rule returns (CVEs only); metadata only -- E7 is about "
                     "SELECTION, not scanning."),
        "source": ("ProjectDiscovery nuclei-templates (public, ~89 MB -- NOT bundled in this repo). "
                   "Fetch: `nuclei -update-templates`, or "
                   "`git clone --branch <version> https://github.com/projectdiscovery/nuclei-templates`. "
                   "Regenerate this fixture: `python scripts/build_curation_fixture.py --corpus <path>`. "
                   "The pinned version used for the committed fixture is recorded in "
                   "results/final/e7_curation_note.md."),
        "target": "Grafana 8.3.0",
        "count": len(rows),
        "templates": rows,
    }
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
    print(f"Wrote {len(rows)} Grafana-tagged CVE templates -> {out}")
    for r in rows:
        print(f"  {r['cve_id']:16} [{r['severity']:8}] {r['name']}")

if __name__ == "__main__":
    main()
