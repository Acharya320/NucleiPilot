"""The planners' decisions -- most importantly, the DIVERGENCE: given the same
candidates, the severity rule (B1) and the context rule (B2) pick DIFFERENT first
validations. This is the whole experiment, proven deterministically (no Nuclei/LLM)."""
import unittest

from nucleipilot import planners

# The four toy candidates, as the engine would hand them to a planner.
CANDIDATES = [
    {"validation": "toy-admin-validation", "endpoint": "/payments",
     "business_importance": "critical", "tech_severity": "medium"},
    {"validation": "toy-pii-validation", "endpoint": "/account",
     "business_importance": "high", "tech_severity": "medium"},
    {"validation": "toy-docs-debug-validation", "endpoint": "/docs",
     "business_importance": "low", "tech_severity": "high"},
    {"validation": "toy-health-debug-validation", "endpoint": "/health",
     "business_importance": "low", "tech_severity": "high"},
]


class TestPlanners(unittest.TestCase):
    def test_severity_rule_picks_highest_severity(self):
        d = planners.SeverityRulePlanner().decide(CANDIDATES, [], 2)
        # both debug validations are 'high'; stable tie-break -> docs (alphabetical)
        self.assertEqual(d.chosen, "toy-docs-debug-validation")

    def test_context_rule_picks_most_business_critical(self):
        d = planners.ContextRulePlanner().decide(CANDIDATES, [], 2)
        self.assertEqual(d.chosen, "toy-admin-validation")

    def test_the_two_rules_DIVERGE(self):
        b1 = planners.SeverityRulePlanner().decide(CANDIDATES, [], 2).chosen
        b2 = planners.ContextRulePlanner().decide(CANDIDATES, [], 2).chosen
        self.assertNotEqual(b1, b2)   # the divergence the toy is designed to create

    def test_planners_stop_when_nothing_pending(self):
        for P in (planners.FixedPlanner, planners.SeverityRulePlanner, planners.ContextRulePlanner):
            self.assertIsNone(P().decide([], [], 2).chosen)

    def test_llm_planner_parses_choice(self):
        class FakeClient:
            model = "fake"
            def chat_json(self, system, user):
                return ({"chosen": "toy-admin-validation", "reason": "r",
                         "confidence": 0.9, "stop_reason": None}, "raw", None, None)
        d = planners.LLMPlanner(client=FakeClient()).decide(CANDIDATES, [], 2)
        self.assertEqual(d.chosen, "toy-admin-validation")

    def test_llm_planner_stops_safe_on_bad_output(self):
        class BadClient:
            model = "fake"
            def chat_json(self, system, user):
                return (None, "garbage", None, "could not parse JSON")
        d = planners.LLMPlanner(client=BadClient()).decide(CANDIDATES, [], 2)
        self.assertIsNone(d.chosen)
        self.assertEqual(d.stop_reason, "llm_invalid_output")


if __name__ == "__main__":
    unittest.main()
