"""Pretty-print the full audit trace of a saved NucleiPilot run.

    python scripts/show_trace.py [results/day2_llm_both_budget1.json] [--run llm]

ASCII-only so it renders cleanly in any console or screen recording. Handles both
single-run files and files that bundle several runs (e.g. {"rule":..., "llm":...}).
Scanner-only files (results/*_scan.json) have no agent trace and are reported as such.
"""
import os, sys, json, argparse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAR, SUB = "=" * 80, "-" * 80


def find_runs(data):
    """Return [(label, run_dict), ...] for every workflow run in the file."""
    if isinstance(data, dict) and "trace" in data:
        return [("", data)]
    out = []
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict) and "trace" in v:
                out.append((k, v))
    return out


def show(label, run):
    print(BAR)
    print("FULL AGENT TRACE" + (f"  [{label}]" if label else ""))
    print(BAR)
    print(f"Target  : {run.get('target')}")
    print(f"Planner : {run.get('planner')}      Budget: {run.get('budget')} follow-up(s)")
    ctx = run.get("target_context") or {}
    if ctx:
        print("Target context:")
        print("   " + json.dumps(ctx, indent=2).replace("\n", "\n   "))
    print(SUB)
    n = 0
    for e in run.get("trace", []):
        s, d = e.get("step"), e.get("detail", {})
        if s == "discovery":
            n += 1
            hit = "MATCH" if d.get("matched") else "no match"
            print(f"[{n}] OBSERVE   (discovery scan: {d.get('template')})")
            print(f"        -> {hit}" + (f"   @ {d.get('evidence_at')}" if d.get("matched") else ""))
            if d.get("error"):
                print(f"        !! error: {d.get('error')}")
        elif s == "decision":
            n += 1
            raw = d.get("raw") or {}
            print(f"[{n}] REASON    ({d.get('planner')} planner decides)")
            print(f"        proposes   : {d.get('proposed')}")
            print(f"        reason     : {d.get('reason')}")
            print(f"        confidence : {d.get('confidence')}")
            if d.get("stop_reason"):
                print(f"        stop_reason: {d.get('stop_reason')}")
            if raw.get("model"):
                print(f"        [model={raw.get('model')}  tokens={raw.get('usage')}]")
        elif s == "policy":
            n += 1
            print(f"[{n}] AUTHORIZE (policy guard, independent of the model)")
            print(f"        verdict    : {'APPROVED' if d.get('ok') else 'BLOCKED'}")
            print(f"        detail     : {d.get('reason')}")
        elif s == "action":
            n += 1
            if d.get("executed"):
                hit = "MATCH" if d.get("matched") else "no match"
                print(f"[{n}] ACT       (run approved template: {d.get('template')})")
                print(f"        -> {hit}" + (f"   @ {d.get('evidence_at')}" if d.get("matched") else ""))
            else:
                print(f"[{n}] ACT       -> BLOCKED; nothing executed ({d.get('blocked_reason')})")
        elif s == "reassess":
            n += 1
            print(f"[{n}] REASSESS  (final per-issue verdict)")
            for issue, verdict in (d.get("assessment") or {}).items():
                print(f"        {issue:8}: {verdict}")
    print(SUB)
    print(f"Templates run: {run.get('n_templates_run')}  ->  {', '.join(run.get('templates_run', []))}")
    print(f"Wall-clock   : {run.get('elapsed_s')}s\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?",
                    default=os.path.join(REPO, "results", "day2_llm_both_budget1.json"))
    ap.add_argument("--run", default=None, help="show only this run (e.g. llm) if the file bundles several")
    args = ap.parse_args()
    path = args.path if os.path.isabs(args.path) else os.path.join(REPO, args.path)
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    runs = find_runs(data)
    if not runs:
        print(f"No agent trace found in {path}")
        print("(scanner-only files like *_scan.json have no workflow trace.)")
        return
    for label, run in runs:
        if args.run and label and label != args.run:
            continue
        show(label, run)


if __name__ == "__main__":
    main()
