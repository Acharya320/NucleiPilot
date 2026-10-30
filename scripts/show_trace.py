"""Pretty-print the full audit trace of a saved NucleiPilot run.

    python scripts/show_trace.py [results/final/traces/e1_C_run0.json]

Reads a trace written by `engine.run` (step types: decision -> policy -> action,
repeated per round, then a final reassess). ASCII-only so it renders cleanly in
any console or screen recording.
"""
import os, sys, json, argparse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAR, SUB = "=" * 80, "-" * 80


def find_runs(data):
    """Return [(label, run_dict), ...] for every run in the file."""
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
    print(f"Target  : {run.get('base_url')}  (asset: {run.get('asset_id')})")
    print(f"Planner : {run.get('planner')}      Budget: {run.get('budget')} validation(s)")
    print(SUB)
    n = 0
    for e in run.get("trace", []):
        s, d = e.get("step"), e.get("detail", {})
        if s == "decision":
            n += 1
            raw = d.get("raw") or {}
            print(f"[{n}] REASON    ({d.get('planner')} planner proposes)")
            print(f"        proposes   : {d.get('chosen')}")
            print(f"        reason     : {d.get('reason')}")
            if d.get("confidence") is not None:
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
                print(f"[{n}] ACT       (run approved template: {d.get('validation')})")
                print(f"        -> {hit}   [verdict: {d.get('status')}]"
                      + (f"   @ {d.get('matched_at')}" if d.get("matched") else ""))
                if d.get("error"):
                    print(f"        !! error: {d.get('error')}")
            else:
                print(f"[{n}] ACT       -> nothing executed ({d.get('reason') or d.get('status')})")
        elif s == "reassess":
            n += 1
            print(f"[{n}] REASSESS  (final per-endpoint verdict)")
            for f in (d.get("findings") or []):
                extra = f"   ({f.get('validation')})" if f.get("validation") else ""
                print(f"        {f.get('endpoint',''):12}: {f.get('status')}{extra}")
    print(SUB)
    m = run.get("metrics", {})
    print(f"Validations run: {m.get('n_validations_run')}  "
          f"(budget used {m.get('validation_budget_used')}/{run.get('budget')}, "
          f"policy rejections {m.get('policy_rejections')})")
    print(f"Chosen order   : {' -> '.join(run.get('chosen_order', [])) or '(none)'}")
    print(f"Decision loop  : {m.get('decision_loop_elapsed_s')}s\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?",
                    default=os.path.join(REPO, "results", "final", "traces", "e1_C_run0.json"))
    ap.add_argument("--run", default=None, help="show only this run if the file bundles several")
    args = ap.parse_args()
    path = args.path if os.path.isabs(args.path) else os.path.join(REPO, args.path)
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    runs = find_runs(data)
    if not runs:
        print(f"No agent trace found in {path}")
        return
    for label, run in runs:
        if args.run and label and label != args.run:
            continue
        show(label, run)


if __name__ == "__main__":
    main()
