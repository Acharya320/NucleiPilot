"""The full agent loop, driven by a DETERMINISTIC fake scanner (no Nuclei/API).

The fake reproduces the sandbox's match logic so we can assert end-to-end
assessments: confirmations, the benign non-false-positive, adaptivity, and
budget-limited prioritization.
"""
import os
import unittest

from nucleipilot import policy, workflow
from nucleipilot.planner import FixedPlanner, RulePlanner
from nucleipilot.scanner import ScanResult


def _matches(profile, tid):
    return {
        "demo-admin-indicator": profile in {"admin", "both"},
        "demo-admin-validation": profile in {"admin", "both"},
        "demo-debug-indicator": profile in {"debug", "both", "benign"},
        "demo-debug-validation": profile in {"debug", "both"},
    }[tid]


def fake_scan_for(profile):
    def scan(target, template_path):
        tid = os.path.splitext(os.path.basename(template_path))[0]
        m = _matches(profile, tid)
        spec = policy.get(tid)
        return ScanResult(
            template_id=tid, target=target, matched=m,
            matched_at=(target + "/evidence" if m else None),
            severity=spec.severity if m else None, duration_s=0.0,
        )
    return scan


class TestWorkflow(unittest.TestCase):
    def _run(self, profile, planner, budget=2):
        return workflow.run_workflow(
            "http://127.0.0.1:1", planner, budget=budget,
            scan_fn=fake_scan_for(profile),
        )

    def test_admin_confirmed(self):
        out = self._run("admin", RulePlanner())
        self.assertEqual(out["assessment"]["admin"], "CONFIRMED")
        self.assertEqual(out["assessment"]["debug"], "CLEAN")

    def test_benign_no_false_positive(self):
        out = self._run("benign", RulePlanner())
        self.assertNotEqual(out["assessment"]["debug"], "CONFIRMED")  # the trap
        self.assertEqual(out["assessment"]["admin"], "CLEAN")

    def test_clean_rule_runs_fewer_than_fixed(self):
        rule = self._run("clean", RulePlanner())
        fixed = self._run("clean", FixedPlanner())
        self.assertLess(rule["n_templates_run"], fixed["n_templates_run"])

    def test_both_confirmed_with_full_budget(self):
        out = self._run("both", RulePlanner(), budget=2)
        self.assertEqual(out["assessment"]["admin"], "CONFIRMED")
        self.assertEqual(out["assessment"]["debug"], "CONFIRMED")

    def test_both_budget1_rule_prioritizes_highest_severity(self):
        out = self._run("both", RulePlanner(), budget=1)
        # debug validation is 'high' > admin 'medium'
        self.assertEqual(out["assessment"]["debug"], "CONFIRMED")
        self.assertEqual(out["assessment"]["admin"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
