"""Run the Fixed and Rule planners through the real agent loop against every
sandbox profile, and compare template count + accuracy vs ground truth.
    python scripts/compare_rule_vs_fixed.py
Needs Nuclei (no API key).
"""
import sys, os, threading

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from http.server import ThreadingHTTPServer                      # noqa: E402
from nucleipilot.sandbox import make_handler, ground_truth       # noqa: E402
from nucleipilot.planner import FixedPlanner, RulePlanner        # noqa: E402
from nucleipilot import workflow                                 # noqa: E402

PORT = 8771
COND_TO_ISSUE = {"admin_auth_missing": "admin", "debug_exposed": "debug"}


def gt_issues(profile):
    return {COND_TO_ISSUE[c] for c in ground_truth(profile)}


def main():
    print(f"{'profile':8} {'planner':6} {'tmpls':5}  {'assessment':40} {'ground truth':16} {'FP':4} {'FN':4}")
    print("-" * 96)
    for profile in ["clean", "benign", "admin", "both"]:
        gt = gt_issues(profile)
        httpd = ThreadingHTTPServer(("127.0.0.1", PORT), make_handler(profile))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            for Planner in (FixedPlanner, RulePlanner):
                out = workflow.run_workflow(f"http://127.0.0.1:{PORT}", Planner(), budget=2)
                a = out["assessment"]
                confirmed = {i for i, s in a.items() if s == "CONFIRMED"}
                fp, fn = confirmed - gt, gt - confirmed
                astr = ", ".join(f"{i}:{s}" for i, s in a.items())
                print(f"{profile:8} {out['planner']:6} {out['n_templates_run']:^5}  "
                      f"{astr:40} {str(sorted(gt)) or '[]':16} "
                      f"{'!'+str(sorted(fp)) if fp else 'ok':4} {'!'+str(sorted(fn)) if fn else 'ok':4}")
        finally:
            httpd.shutdown(); httpd.server_close()
        print()


if __name__ == "__main__":
    main()
