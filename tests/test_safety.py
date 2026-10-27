"""Regression tests for the safety invariants (deterministic; no Nuclei/API)."""
import os
import unittest

from nucleipilot import policy, workflow
from nucleipilot.scanner import ScanResult, assert_in_scope, ScopeError
from nucleipilot.planner import LLMPlanner, RulePlanner


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
    model = "stub"

    def __init__(self, parsed=None, error=None):
        self._p, self._e = parsed, error

    def chat_json(self, system, user):
        return self._p, "", None, self._e


class TestSafety(unittest.TestCase):
    def test_out_of_scope_rejected(self):
        with self.assertRaises(ScopeError):
            assert_in_scope("http://example.com/")
        assert_in_scope("http://127.0.0.1:8765")  # localhost is fine

    def test_invented_template_blocked(self):
        p = LLMPlanner(client=StubClient(parsed={
            "next_template": "demo-everything-rce", "reason": "x", "confidence": 0.9}))
        out = workflow.run_workflow("http://127.0.0.1:1", p, budget=2,
                                    scan_fn=fake_scan_for("both"))
        self.assertTrue(any(e["step"] == "policy" and not e["detail"]["ok"] for e in out["trace"]))
        self.assertFalse(any(e["step"] == "action" and e["detail"].get("executed")
                             and e["detail"].get("template") == "demo-everything-rce"
                             for e in out["trace"]))

    def test_malformed_json_safe_stop(self):
        p = LLMPlanner(client=StubClient(parsed=None, error="bad json"))
        out = workflow.run_workflow("http://127.0.0.1:1", p, budget=2,
                                    scan_fn=fake_scan_for("both"))
        self.assertTrue(any(e["step"] == "decision"
                            and e["detail"].get("stop_reason") == "llm_invalid_output"
                            for e in out["trace"]))
        self.assertFalse(any(e["step"] == "action" and e["detail"].get("executed")
                             for e in out["trace"]))

    def test_stop_on_clean_target(self):
        out = workflow.run_workflow("http://127.0.0.1:1", RulePlanner(), budget=2,
                                    scan_fn=fake_scan_for("clean"))
        self.assertTrue(all(v != "CONFIRMED" for v in out["assessment"].values()))
        self.assertEqual(out["n_templates_run"], 2)


if __name__ == "__main__":
    unittest.main()
