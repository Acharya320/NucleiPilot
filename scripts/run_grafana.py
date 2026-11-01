"""E4 -- NucleiPilot on live Grafana 8.3.0, using the REAL ~14k-template corpus.

One end-to-end run, the SAME engine as the toy (E1-E3):

  1. FINGERPRINT  detect the live container's version via /api/health (-> 8.3.0).
  2. CURATE       from the real corpus, take the grafana-tagged CVEs a `-tags grafana`
                  rule gathers (config/grafana_corpus.json, extracted by
                  scripts/build_grafana_fixture.py).
  3. SELECT       which CVEs actually apply to 8.3.0? Compare a TAG rule, a naive
                  VERSION parser, and the LLM -> precision / recall / F1 vs
                  config/grafana_ground_truth.json. (This is where the LLM beats rules:
                  affected versions are inconsistent free text.)
  4. VALIDATE LIVE  the LLM's applicable pick, IF it is on the read-only SAFE allowlist,
                  is run against the container through the SAME engine
                  (policy gate -> Nuclei -> code verdict). An intrusive pick is REFUSED
                  by the gate -- the "model proposes, code authorizes" guarantee.

Needs: Docker, Nuclei v3, an OpenRouter key in .env, and a local nuclei-templates
checkout (--corpus, default ~/nuclei-templates) for the real community template in step 4.
Outputs to results/reproduced/ by default (results/final/ holds the committed reference).

    python scripts/run_grafana.py
"""
import os, sys, json, re, time, argparse, subprocess, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from nucleipilot import policy, scanner, verifier, engine, planners   # noqa: E402
from nucleipilot.profiler import Profile                              # noqa: E402

PORT = 3000
BASE = f"http://127.0.0.1:{PORT}"
NAME = "np-grafana"
IMAGE = "grafana/grafana:8.3.0"
TARGET_STR = "Grafana 8.3.0"
TARGET = (8, 3, 0)
DEFAULT_OUT = os.path.join("results", "reproduced")
N_REPEATS = 3
_VER = re.compile(r"\b(\d+)\.(\d+)(?:\.(\d+))?\b")


# ---------- live container ----------
def _health_version(timeout=2):
    try:
        with urllib.request.urlopen(BASE + "/api/health", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace")).get("version")
    except Exception:
        return None


def ensure_grafana():
    v = _health_version()
    if v:
        print(f"[1] Fingerprint: Grafana {v} already running on {BASE}")
        return v
    print(f"[1] Starting {IMAGE} on 127.0.0.1:{PORT} ...")
    subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)
    rc = subprocess.run(["docker", "run", "-d", "--name", NAME,
                         "-p", f"127.0.0.1:{PORT}:3000", IMAGE], capture_output=True, text=True)
    if rc.returncode != 0:
        print("    Could not start Grafana via Docker:\n" + (rc.stderr or ""))
        print(f"    Start it manually: docker run -d --name {NAME} -p 127.0.0.1:{PORT}:3000 {IMAGE}")
        sys.exit(2)
    for _ in range(40):
        v = _health_version()
        if v:
            break
        time.sleep(0.75)
    if not v:
        print("    Grafana did not become healthy in time."); sys.exit(2)
    print(f"[1] Fingerprint: Grafana {v} (live container)")
    return v


# ---------- selection (step 3) ----------
def versions_in(text):
    return [(int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)) for m in _VER.finditer(text or "")]


def select_tag(pool):
    return [t["id"] for t in pool]                     # a tag rule gathers them all


def select_version(pool):
    """Naive parser: highest version mentioned = upper bound; include if target <= it;
    include when unparseable (a cautious scanner would run it)."""
    sel = []
    for t in pool:
        vers = versions_in(t["description"])
        if not vers or TARGET <= max(vers):
            sel.append(t["id"])
    return sel


_LLM_SYSTEM = (
    "You are a security assistant deciding whether each listed CVE affects a SPECIFIC target "
    "version. Read each template's name and description, infer the affected version range, and "
    "decide whether the target falls inside it. A CVE in a feature newer than the target does not "
    "apply. Respond with STRICT JSON only, no prose, no code fences:\n"
    '{"decisions": [{"id": "<cve id>", "applies": true|false, "reason": "<short>"}]}'
)


def select_llm(pool, client):
    lines = [f"- id={t['id']} | name={t['name']}\n    description: {t['description']}" for t in pool]
    user = (f"TARGET: {TARGET_STR}\n\nCANDIDATE TEMPLATES (decide applies true/false for each):\n"
            + "\n".join(lines) + "\n\nReturn the JSON now.")
    parsed, raw, usage, error = client.chat_json(_LLM_SYSTEM, user)
    if error or not isinstance(parsed, dict):
        return None, {"error": error, "raw": raw}
    decisions = parsed.get("decisions", [])
    return [d.get("id") for d in decisions if d.get("applies") is True], {"decisions": decisions}


def score(selected, applies_set, all_ids):
    s = set(selected)
    tp, fp, fn = len(s & applies_set), len(s - applies_set), len(applies_set - s)
    tn = len(set(all_ids) - s - applies_set)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"selected": sorted(s), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3)}


# ---------- live validation via the SAME engine (step 4) ----------
def validate_live(ids, pool_by_id, corpus):
    """Run each given template id against the live container THROUGH engine.run, using the
    real community template from the corpus. Returns the engine result dict."""
    catalog = {}
    for cid in ids:
        rel = pool_by_id[cid]["file"]
        abspath = os.path.join(corpus, rel)
        catalog[cid] = policy.TemplateSpec(
            id=cid, filename=abspath, issue="grafana-cve", kind="validation",
            purpose=pool_by_id[cid]["name"], severity=pool_by_id[cid].get("severity", "high"),
            validates="grafana-version-indicator", cost=1, endpoint="/")
    prof = Profile(
        asset_id="grafana-local", base_url=BASE, budget=len(ids),
        endpoints={"/": {"business_importance": "high",
                         "fired_indicators": ["grafana-version-indicator"],
                         "candidate_validations": list(ids)}},
        tech_facts={"product": "grafana", "version": TARGET_STR})
    asset = {"id": "grafana-local", "base_url": BASE}
    # FixedPlanner runs the (already LLM-selected, safety-gated) picks; same engine loop.
    return engine.run(asset, catalog, planners.FixedPlanner(), profile=prof)


def main(argv=None):
    ap = argparse.ArgumentParser(description="E4: NucleiPilot on live Grafana 8.3.0 using the real 14k corpus.")
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help="output dir (default: results/reproduced; results/final = committed reference).")
    ap.add_argument("--corpus", default=os.environ.get("NUCLEIPILOT_TEMPLATES_DIR",
                    os.path.join(os.path.expanduser("~"), "nuclei-templates")),
                    help="path to a nuclei-templates checkout (for the real community template in step 4).")
    args = ap.parse_args(argv)
    out_dir = args.out if os.path.isabs(args.out) else os.path.join(REPO, args.out)
    os.makedirs(out_dir, exist_ok=True)

    corpus = json.load(open(os.path.join(REPO, "config", "grafana_corpus.json"), encoding="utf-8"))
    gt = json.load(open(os.path.join(REPO, "config", "grafana_ground_truth.json"), encoding="utf-8"))
    pool = corpus["templates"]
    pool_by_id = {t["id"]: t for t in pool}
    all_ids = [t["id"] for t in pool]
    applies = set(gt["applies"])
    safe = set(gt.get("read_only_safe", []))

    print(f"=== E4: NucleiPilot on live {TARGET_STR}, using the real ~14k corpus ===\n")
    version = ensure_grafana()
    print(f"[2] Curate: {len(pool)} grafana-tagged CVEs from the corpus (config/grafana_corpus.json)")

    # ---- step 3: selection, measured ----
    print(f"\n[3] Select -- which of the {len(pool)} CVEs apply to {TARGET_STR}? "
          f"(ground truth: {sorted(applies)})")
    results = {"TAG": score(select_tag(pool), applies, all_ids),
               "VERSION": score(select_version(pool), applies, all_ids)}
    print(f"      TAG rule     F1={results['TAG']['f1']:.2f}  (selects all {results['TAG']['tp']+results['TAG']['fp']})")
    print(f"      VERSION rule F1={results['VERSION']['f1']:.2f}  (selects {len(results['VERSION']['selected'])})")

    client = None
    try:
        from nucleipilot.llm_client import LLMClient
        c = LLMClient()
        client = c if c.api_key else None
    except Exception:
        client = None

    llm_runs, llm_pick = [], []
    if client:
        for k in range(N_REPEATS):
            sel, _ = select_llm(pool, client)
            if sel is None:
                continue
            llm_runs.append(score(sel, applies, all_ids))
            if k == 0:
                llm_pick = sorted(set(sel))
        if llm_runs:
            f1s = [r["f1"] for r in llm_runs]
            stable = len({tuple(r["selected"]) for r in llm_runs}) == 1
            print(f"      LLM          F1={sum(f1s)/len(f1s):.2f}  over {len(llm_runs)} runs "
                  f"(stable: {'YES' if stable else 'NO'})  -> picked: {llm_pick}")
    else:
        print("      LLM: skipped (no OpenRouter key in .env). TAG/VERSION still shown.")

    # ---- step 4: validate the LLM pick live, through the engine, read-only gate ----
    print(f"\n[4] Validate live (read-only safe allowlist = {sorted(safe)}):")
    to_run = [cid for cid in llm_pick if cid in safe]
    refused = [cid for cid in llm_pick if cid not in safe]
    live = None
    corpus_dir = args.corpus
    if refused:
        print(f"      REFUSED by read-only gate (not executed): {refused}")
    if to_run and not os.path.isdir(corpus_dir):
        print(f"      Corpus not found at {corpus_dir}; cannot run the real template. "
              f"Pass --corpus <path>. (Selection above is unaffected.)")
    elif to_run:
        missing = [c for c in to_run if not os.path.exists(os.path.join(corpus_dir, pool_by_id[c]["file"]))]
        if missing:
            print(f"      Template file(s) not in corpus: {missing}; skipping live run.")
        else:
            live = validate_live(to_run, pool_by_id, corpus_dir)
            for f in live["findings"]:
                print(f"      {f['validation']} -> {f['status']} "
                      f"(matched_at={f['evidence'].get('matched_at')})")
    elif not to_run and llm_pick:
        print("      LLM pick is not on the read-only allowlist; nothing executed (safe).")

    # ---- write evidence ----
    out = {"target": TARGET_STR, "detected_version": version, "candidates": all_ids,
           "ground_truth_applies": sorted(applies), "read_only_safe": sorted(safe),
           "selection": {"TAG": results["TAG"], "VERSION": results["VERSION"], "LLM_runs": llm_runs,
                         "LLM_pick": llm_pick},
           "live_validation": {"executed": to_run, "refused_by_gate": refused,
                               "findings": (live["findings"] if live else []),
                               "trace": (live["trace"] if live else [])}}
    with open(os.path.join(out_dir, "e4_grafana_run.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    md = [f"# E4 - NucleiPilot on live {TARGET_STR}, using the real ~14k corpus", "",
          f"*Generated by `scripts/run_grafana.py`. Same engine as E1-E3. Candidate pool = "
          f"{len(pool)} grafana-tagged CVEs from the real nuclei-templates corpus "
          f"(`config/grafana_corpus.json`). Detected version: {version}.*", "",
          "## Step 3 - selection (which CVEs apply to 8.3.0?)", "",
          "| Method | Precision | Recall | F1 | Selected |", "|---|---:|---:|---:|---:|",
          f"| TAG rule | {results['TAG']['precision']:.2f} | {results['TAG']['recall']:.2f} | {results['TAG']['f1']:.2f} | {len(results['TAG']['selected'])} |",
          f"| VERSION rule | {results['VERSION']['precision']:.2f} | {results['VERSION']['recall']:.2f} | {results['VERSION']['f1']:.2f} | {len(results['VERSION']['selected'])} |"]
    for i, r in enumerate(llm_runs):
        md.append(f"| LLM run {i+1} | {r['precision']:.2f} | {r['recall']:.2f} | {r['f1']:.2f} | {len(r['selected'])} |")
    md += ["", f"LLM pick: **{', '.join(llm_pick) or '(none)'}**  ·  ground truth: **{', '.join(sorted(applies))}**",
           "", "## Step 4 - live validation (read-only safe gate)", ""]
    if live:
        for f in live["findings"]:
            md.append(f"- `{f['validation']}` -> **{f['status']}** (matched_at `{f['evidence'].get('matched_at')}`)")
    if refused:
        md.append(f"- Refused by the read-only gate (not executed): {', '.join(refused)}")
    md += ["", "**Reading it:** a tag rule gathers every grafana CVE but cannot tell which applies to "
           "8.3.0; the version parser trips on inconsistent/missing ranges; the LLM reads the prose and "
           "picks the applicable one, then the SAME engine runs that real community template live and "
           "code assigns the verdict. Intrusive CVEs are refused by the read-only gate. One product / "
           "version: a demonstration, not a breadth guarantee."]
    with open(os.path.join(out_dir, "e4_grafana_summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")

    print(f"\nSaved -> {os.path.join(out_dir, 'e4_grafana_summary.md')}")
    print(f"Saved -> {os.path.join(out_dir, 'e4_grafana_run.json')}")
    print(f"\nContainer left running for the demo. Stop with:  docker rm -f {NAME}")


if __name__ == "__main__":
    main()
