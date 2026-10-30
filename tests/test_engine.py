"""The v2 engine end to end, with a deterministic FAKE scanner (no Nuclei, no LLM).

Proves the full E1 story for the non-LLM methods: under budget 2, B2 confirms the
business-important issues while B1 chases severity (and wastes a slot on the trap),
A finds everything, the trap is NOT_CONFIRMED, and a hallucinated id is blocked.
"""
import copy
import os
import unittest
from types import SimpleNamespace

from nucleipilot import policy, registry, profiler, engine, planners
from nucleipilot.scanner import ScanResult, ScopeError

BASE = "http://127.0.0.1:8777"


def _discovery():
    def SR(urls):
        return SimpleNamespace(matched=True, raw=[{"matched-at": u} for u in urls],
                               matched_at=urls[0])
    return {
        "toy-admin-indicator": SR([BASE + "/payments"]),
        "toy-debug-indicator": SR([BASE + "/docs", BASE + "/health"]),
        "toy-pii-indicator": SR([BASE + "/account/export"]),
    }


def _fake_scan(target, template_path):
    tid = os.path.splitext(os.path.basename(template_path))[0]
    matched = tid != "toy-health-debug-validation"      # /health is the benign trap
    return ScanResult(template_id=tid, target=target, matched=matched,
                      matched_at=(target if matched else None))


def _statuses(result):
    return {f["endpoint"]: f["status"] for f in result["findings"]}


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.cat = policy.toy_catalog()
        self.asset = registry.get_asset(registry.load_registry(), "toy-app")
        self.profile = profiler.build_profile(self.asset, self.cat, _discovery(), base_url=BASE)

    def _run(self, planner):
        return engine.run(self.asset, self.cat, planner, profile=self.profile, scan_fn=_fake_scan)

    def test_B2_context_rule_spends_budget_on_business_important(self):
        r = self._run(planners.ContextRulePlanner())
        self.assertEqual(r["chosen_order"], ["toy-admin-validation", "toy-pii-validation"])
        s = _statuses(r)
        self.assertEqual(s["/payments"], "CONFIRMED")
        self.assertEqual(s["/account"], "CONFIRMED")
        self.assertEqual(s["/docs"], "UNVERIFIED")      # fired, but out of budget
        self.assertEqual(s["/health"], "UNVERIFIED")
        self.assertEqual(s["/home"], "NO_INDICATOR")
        self.assertEqual(r["metrics"]["validation_budget_used"], 2)

    def test_B1_severity_rule_chases_severity_and_hits_the_trap(self):
        r = self._run(planners.SeverityRulePlanner())
        self.assertEqual(r["chosen_order"], ["toy-docs-debug-validation", "toy-health-debug-validation"])
        s = _statuses(r)
        self.assertEqual(s["/docs"], "CONFIRMED")
        self.assertEqual(s["/health"], "NOT_CONFIRMED")   # slot wasted on the benign trap
        self.assertEqual(s["/payments"], "UNVERIFIED")    # business-critical issue missed
        self.assertEqual(s["/account"], "UNVERIFIED")

    def test_A_fixed_finds_everything_and_rejects_the_trap(self):
        r = self._run(planners.FixedPlanner())
        s = _statuses(r)
        self.assertEqual(s["/payments"], "CONFIRMED")
        self.assertEqual(s["/docs"], "CONFIRMED")
        self.assertEqual(s["/account"], "CONFIRMED")
        self.assertEqual(s["/health"], "NOT_CONFIRMED")
        self.assertEqual(s["/home"], "NO_INDICATOR")
        self.assertEqual(r["metrics"]["n_validations_run"], 4)

    def test_hallucinated_id_is_blocked_by_the_gate(self):
        class Bogus(planners.Planner):
            name = "bogus"
            def decide(self, pending, evidence, remaining_budget, context=None):
                return planners.Decision("not-a-real-template", "hallucinated")
        r = self._run(Bogus())
        self.assertGreaterEqual(r["metrics"]["policy_rejections"], 1)
        self.assertNotIn("CONFIRMED", _statuses(r).values())

    def test_llm_path_runs_with_a_mock_client(self):
        class FakeClient:
            model = "fake"
            def __init__(self): self.n = 0
            def chat_json(self, system, user):
                self.n += 1
                pick = ["toy-admin-validation", "toy-pii-validation"][min(self.n - 1, 1)]
                return ({"chosen": pick, "reason": "mock", "confidence": 0.9,
                         "stop_reason": None}, "raw", {"prompt_tokens": 1}, None)
        r = self._run(planners.LLMPlanner(client=FakeClient()))
        self.assertEqual(r["chosen_order"], ["toy-admin-validation", "toy-pii-validation"])
        self.assertEqual(_statuses(r)["/payments"], "CONFIRMED")

    # --- E5 safety properties ---------------------------------------------
    def test_out_of_scope_asset_refused_before_scanning(self):
        evil = copy.deepcopy(self.asset)
        evil["base_url"] = "http://attacker.example.com"
        with self.assertRaises(ScopeError):
            engine.run(evil, self.cat, planners.ContextRulePlanner(),
                       profile=self.profile, scan_fn=_fake_scan)

    def test_malformed_llm_json_stops_safe(self):
        class BadClient:
            model = "stub"
            def chat_json(self, system, user):
                return (None, "garbage", None, "could not parse JSON")
        r = self._run(planners.LLMPlanner(client=BadClient()))
        self.assertNotIn("CONFIRMED", _statuses(r).values())
        self.assertEqual(r["metrics"]["n_validations_run"], 0)

    def test_budget_never_exceeded(self):
        r = self._run(planners.ContextRulePlanner())
        n_pool = sum(len(v["candidate_validations"]) for v in self.profile.endpoints.values())
        self.assertGreater(n_pool, self.profile.budget)                 # more eligible than budget
        self.assertEqual(r["metrics"]["n_validations_run"], self.profile.budget)


if __name__ == "__main__":
    unittest.main()
