"""One real LLM decision, checked by the policy guard.
Hard case: profile 'both' (two real signals), budget=1 (confirm only one).
Severity rule -> debug (high). Target context -> admin is business-critical.
    python scripts/llm_decision_demo.py
Needs Nuclei + an OpenRouter key in .env.
"""
import sys, os, json, threading

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from http.server import ThreadingHTTPServer                      # noqa: E402
from nucleipilot.sandbox import make_handler                     # noqa: E402
from nucleipilot.planner import RulePlanner, LLMPlanner          # noqa: E402
from nucleipilot import workflow                                 # noqa: E402

PORT = 8782
TARGET = f"http://127.0.0.1:{PORT}"
CONTEXT = {
    "environment": "authorized local sandbox",
    "assets": {
        "admin": "The management surface fronts a PAYMENTS service (business-critical).",
        "debug": "The debug flag is on a static documentation microservice (low impact).",
    },
    "note": "Only ONE follow-up is permitted (budget=1). Prioritize business impact.",
}


def pull(trace, step, planner=None):
    for e in trace:
        if e["step"] == step and (planner is None or e["detail"].get("planner") == planner):
            return e["detail"]
    return {}


def main():
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), make_handler("both"))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        print("=== RULE planner (budget=1) ===")
        r = workflow.run_workflow(TARGET, RulePlanner(), budget=1, target_context=CONTEXT)
        rd = pull(r["trace"], "decision", "rule")
        print(f"  chose: {rd.get('proposed')}  reason: {rd.get('reason')}")
        print(f"  assessment: {r['assessment']}   templates_run={r['n_templates_run']}")

        print("\n=== LLM planner (budget=1) ===  [real OpenRouter call]")
        l = workflow.run_workflow(TARGET, LLMPlanner(), budget=1, target_context=CONTEXT)
        ld, lp = pull(l["trace"], "decision", "llm"), pull(l["trace"], "policy")
        raw = ld.get("raw") or {}
        print(f"  model: {raw.get('model')}   usage: {raw.get('usage')}")
        print(f"  chose: {ld.get('proposed')}")
        print(f"  reason: {ld.get('reason')}")
        print(f"  confidence: {ld.get('confidence')}")
        print(f"  POLICY GUARD: ok={lp.get('ok')}  ({lp.get('reason')})")
        print(f"  assessment: {l['assessment']}   templates_run={l['n_templates_run']}")

        out = os.path.join(REPO, "results", "day2_llm_both_budget1.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({"rule": r, "llm": l}, fh, indent=2, default=str)
        print(f"\nSaved -> {out}")
    finally:
        httpd.shutdown(); httpd.server_close()


if __name__ == "__main__":
    main()
