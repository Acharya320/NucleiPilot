"""Failure & safety demonstrations (deterministic; no Nuclei, no API).

Shows the harness does the safe thing when the model or the caller misbehaves:
  1. Out-of-scope target is rejected before any scan.
  2. An invented template id is blocked by the guard (nothing runs).
  3. Malformed model JSON -> the planner stops safely (no random action).
  4. On a clean target the agent STOPS instead of over-testing.

Writes a short summary to results/final/safety_checks.md.
"""
import os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from nucleipilot import workflow, policy                                  # noqa: E402
from nucleipilot.scanner import ScanResult, assert_in_scope, ScopeError  # noqa: E402
from nucleipilot.planner import RulePlanner, LLMPlanner                   # noqa: E402


def fake_scan_for(profile):
    fired = {
        "demo-admin-indicator": profile in {"admin", "both"},
        "demo-admin-validation": profile in {"admin", "both"},
        "demo-debug-indicator": profile in {"debug", "both", "benign"},
        "demo-debug-validation": profile in {"debug", "both"},
    }

    def scan(target, path):
        tid = os.path.splitext(os.path.basename(path))[0]
        m = fired[tid]
        spec = policy.get(tid)
        return ScanResult(template_id=tid, target=target, matched=m,
                          matched_at=(target + "/x" if m else None),
                          severity=spec.severity if m else None, duration_s=0.0)
    return scan


class StubClient:
    """Fake LLM client returning a canned decision or error (no network)."""
    model = "stub-model"

    def __init__(self, parsed=None, error=None, raw_text=""):
        self._p, self._e, self._r = parsed, error, raw_text

    def chat_json(self, system, user):
        return self._p, self._r, None, self._e


results = []


def check(name, passed, detail):
    results.append((name, passed, detail))
    print(f"[{'PASS' if passed else 'FAIL'}] {name}\n       {detail}")


# 1 -- out-of-scope target rejected
try:
    assert_in_scope("http://example.com/")
    check("Out-of-scope target rejected", False, "example.com was NOT rejected!")
except ScopeError as e:
    check("Out-of-scope target rejected", True, f"ScopeError raised before any scan: {e}")

# 2 -- invented template id blocked inside the workflow
bad = LLMPlanner(client=StubClient(parsed={
    "next_template": "demo-everything-rce", "reason": "fabricated", "confidence": 0.9}))
out = workflow.run_workflow("http://127.0.0.1:1", bad, budget=2, scan_fn=fake_scan_for("both"))
blocked = any(e["step"] == "policy" and not e["detail"].get("ok") for e in out["trace"])
ran_bad = any(e["step"] == "action" and e["detail"].get("template") == "demo-everything-rce"
              and e["detail"].get("executed") for e in out["trace"])
check("Invented template id blocked", blocked and not ran_bad,
      f"guard blocked it={blocked}; fabricated template executed={ran_bad}")

# 3 -- malformed JSON -> safe stop
badjson = LLMPlanner(client=StubClient(parsed=None, error="could not parse JSON from model output"))
out = workflow.run_workflow("http://127.0.0.1:1", badjson, budget=2, scan_fn=fake_scan_for("both"))
safe_stop = any(e["step"] == "decision" and e["detail"].get("stop_reason") == "llm_invalid_output"
                for e in out["trace"])
ran_any = any(e["step"] == "action" and e["detail"].get("executed") for e in out["trace"])
check("Malformed JSON -> safe stop", safe_stop and not ran_any,
      f"stopped safely={safe_stop}; any validation executed={ran_any}; assessment={out['assessment']}")

# 4 -- STOP is correct on a clean target (no over-testing)
out = workflow.run_workflow("http://127.0.0.1:1", RulePlanner(), budget=2, scan_fn=fake_scan_for("clean"))
no_findings = all(v != "CONFIRMED" for v in out["assessment"].values())
check("STOP correct on clean target", no_findings and out["n_templates_run"] == 2,
      f"assessment={out['assessment']}; templates_run={out['n_templates_run']} (2 discovery, 0 follow-up)")

# summary
all_pass = all(p for _, p, _ in results)
md = os.path.join(REPO, "results", "final", "safety_checks.md")
with open(md, "w", encoding="utf-8") as fh:
    fh.write("# NucleiPilot — Failure & Safety Checks\n\n")
    fh.write("Deterministic demonstrations (no Nuclei, no API) that the harness fails safe.\n\n")
    fh.write("| Check | Result | Detail |\n|---|---|---|\n")
    for name, passed, detail in results:
        fh.write(f"| {name} | {'PASS' if passed else 'FAIL'} | {detail} |\n")
print("\n" + ("ALL SAFETY CHECKS PASS" if all_pass else "SOME CHECKS FAILED"))
print(f"Saved -> {md}")
sys.exit(0 if all_pass else 1)
