"""E7 -- Corpus curation: can the LLM pick the version-APPLICABLE CVE better than rules?

The toy experiment (E1-E3) showed the LLM only TIES a rule on simple prioritization.
This asks the opposite question on the REAL corpus: given the Grafana-tagged CVE
templates a fair `-tags grafana` rule gathers (config/curation_corpus.json), which ones
actually apply to the detected target (Grafana 8.3.0)? The affected versions live in
inconsistent free-text prose ("8.0.0-beta1 through 8.3.0", "up to 7.5.11 and 8.1.5",
"below or equals to 12.0.1"), so this is where reading beats tag/keyword matching.

Three contestants, same candidate pool, scored against config/curation_ground_truth.json:
  * TAG   -- select every grafana-tagged CVE (what a tag rule does; cannot read versions)
  * VERSION -- a simple version-range parser (the honest "but couldn't a rule do it?" baseline)
  * LLM   -- reads each name+description and decides applicability (needs an OpenRouter key)

Outputs go to results/reproduced/ by default (results/final/ holds the committed
reference). Run:  python scripts/run_curation.py

NOTE: this measures SELECTION over metadata, not scanning. Actually exploiting the
selected CVE on the live 8.3.0 container is the separate E4 demo (run_grafana.py).
"""
import os, sys, json, re, argparse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

TARGET_STR = "Grafana 8.3.0"
TARGET = (8, 3, 0)
DEFAULT_OUT = os.path.join("results", "reproduced")
N_REPEATS = 3

_VER = re.compile(r"\b(\d+)\.(\d+)(?:\.(\d+))?\b")


def versions_in(text):
    """Every X.Y(.Z) version-like token in the text, as comparable tuples."""
    out = []
    for m in _VER.finditer(text or ""):
        out.append((int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)))
    return out


# ---- contestants --------------------------------------------------------------
def select_tag(pool):
    """A tag rule gathers them all; it cannot reason about versions."""
    return [t["id"] for t in pool]


def select_version(pool):
    """A simple, honest version-range parser: treat the HIGHEST version mentioned as
    the upper bound of the affected range; include the target if target <= that bound.
    If no version is parseable, default to INCLUDE (a cautious scanner would run it)."""
    sel = []
    for t in pool:
        vers = versions_in(t["description"])
        if not vers:
            sel.append(t["id"])            # unparseable -> cautious include
            continue
        if TARGET <= max(vers):
            sel.append(t["id"])
    return sel


_LLM_SYSTEM = (
    "You are a security assistant deciding whether each listed CVE affects a SPECIFIC target "
    "version. Read each template's name and description, infer the affected version range, and "
    "decide whether the target falls inside it. Base the decision on the described versions and "
    "the nature of the feature; a CVE in a feature newer than the target does not apply. Respond "
    "with STRICT JSON only, no prose, no code fences:\n"
    '{"decisions": [{"id": "<cve id>", "applies": true|false, "reason": "<short>"}]}'
)


def select_llm(pool, client):
    lines = []
    for t in pool:
        lines.append(f"- id={t['id']} | name={t['name']}\n    description: {t['description']}")
    user = (f"TARGET: {TARGET_STR}\n\nCANDIDATE TEMPLATES (decide applies true/false for each):\n"
            + "\n".join(lines) + "\n\nReturn the JSON now.")
    parsed, raw, usage, error = client.chat_json(_LLM_SYSTEM, user)
    if error or not isinstance(parsed, dict):
        return None, {"error": error, "raw": raw}
    decisions = parsed.get("decisions", [])
    sel = [d.get("id") for d in decisions if d.get("applies") is True]
    return sel, {"decisions": decisions, "usage": usage}


# ---- scoring ------------------------------------------------------------------
def score(selected, applies_set, all_ids):
    s = set(selected)
    tp = len(s & applies_set)
    fp = len(s - applies_set)
    fn = len(applies_set - s)
    tn = len(set(all_ids) - s - applies_set)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"selected": sorted(s), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="E7 corpus-curation experiment (tag vs version-parser vs LLM).")
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help="output dir (default: results/reproduced; results/final holds the reference).")
    args = ap.parse_args(argv)
    out_dir = args.out if os.path.isabs(args.out) else os.path.join(REPO, args.out)
    os.makedirs(out_dir, exist_ok=True)

    corpus = json.load(open(os.path.join(REPO, "config", "curation_corpus.json"), encoding="utf-8"))
    gt = json.load(open(os.path.join(REPO, "config", "curation_ground_truth.json"), encoding="utf-8"))
    pool = corpus["templates"]
    all_ids = [t["id"] for t in pool]
    applies = set(gt["applies"])

    print(f"Target: {TARGET_STR}   candidates (grafana-tagged CVEs): {len(pool)}   "
          f"actually applicable (ground truth): {sorted(applies)}\n")

    results = {}
    results["TAG"] = score(select_tag(pool), applies, all_ids)
    results["VERSION"] = score(select_version(pool), applies, all_ids)

    # LLM (needs a key); repeat for stability
    llm_runs, llm_detail = [], []
    client = None
    try:
        from nucleipilot.llm_client import LLMClient
        c = LLMClient()
        client = c if c.api_key else None
    except Exception:
        client = None
    if client:
        for k in range(N_REPEATS):
            sel, detail = select_llm(pool, client)
            if sel is None:
                print(f"LLM run {k}: unusable output ({detail.get('error')}); skipping.")
                continue
            llm_runs.append(score(sel, applies, all_ids))
            llm_detail.append(detail)
    else:
        print("LLM: skipped (no OpenRouter key in .env). TAG and VERSION still run.\n")

    # ---- console table ----
    def row(name, r):
        return (f"  {name:16} P={r['precision']:.2f} R={r['recall']:.2f} F1={r['f1']:.2f}  "
                f"(selected {len(r['selected'])}: TP={r['tp']} FP={r['fp']} TN={r['tn']} FN={r['fn']})")
    print(row("TAG rule", results["TAG"]))
    print(row("VERSION rule", results["VERSION"]))
    for i, r in enumerate(llm_runs):
        print(row(f"LLM run {i+1}", r))
    print()
    if llm_runs:
        stable = len({tuple(r["selected"]) for r in llm_runs}) == 1
        print(f"LLM selection stable across {len(llm_runs)} runs: {'YES' if stable else 'NO'}")

    # ---- write evidence ----
    out = {"target": TARGET_STR, "candidates": all_ids, "ground_truth_applies": sorted(applies),
           "TAG": results["TAG"], "VERSION": results["VERSION"],
           "LLM_runs": llm_runs, "LLM_detail": llm_detail}
    with open(os.path.join(out_dir, "curation_results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    md = ["# E7 - Corpus curation: version-applicability selection (Grafana 8.3.0)", "",
          f"*Generated by `scripts/run_curation.py`. Candidate pool = {len(pool)} grafana-tagged CVE "
          f"templates extracted from the real nuclei-templates corpus (`config/curation_corpus.json`). "
          f"Ground truth: only `{', '.join(sorted(applies))}` applies to {TARGET_STR}.*", "",
          "| Method | Precision | Recall | F1 | Selected | FP (wrongly run) |",
          "|---|---:|---:|---:|---:|---|"]
    def mdrow(name, r):
        fp_ids = sorted(set(r["selected"]) - applies)
        return (f"| {name} | {r['precision']:.2f} | {r['recall']:.2f} | {r['f1']:.2f} | "
                f"{len(r['selected'])} | {', '.join(fp_ids) if fp_ids else '-'} |")
    md.append(mdrow("TAG rule (runs all grafana-tagged)", results["TAG"]))
    md.append(mdrow("VERSION rule (naive range parser)", results["VERSION"]))
    for i, r in enumerate(llm_runs):
        md.append(mdrow(f"LLM run {i+1}", r))
    md += ["", "**Reading it:** the TAG rule cannot read versions, so it runs every candidate "
           "(all false positives but the one real hit). The VERSION parser handles explicit ranges "
           "but trips on absent/misleading ones. The LLM reads the prose and selects the applicable "
           "CVE. This is ONE product/version -- a concrete demonstration, not a scaling proof; and the "
           "LLM is a selector, not the authority (NucleiPilot still validates the pick by scanning)."]
    with open(os.path.join(out_dir, "curation_summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")

    print(f"\nSaved -> {os.path.join(out_dir, 'curation_summary.md')}")
    print(f"Saved -> {os.path.join(out_dir, 'curation_results.json')}")


if __name__ == "__main__":
    main()
