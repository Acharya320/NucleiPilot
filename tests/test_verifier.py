"""The evidence verifier: the five code-assigned statuses, incl. the benign trap
(NOT_CONFIRMED) and the rule that a failed scan is never a false negative."""
import unittest
from types import SimpleNamespace

from nucleipilot import verifier


def R(matched=False, error=None):
    return SimpleNamespace(matched=matched, error=error,
                           matched_at="http://127.0.0.1/x", matcher_name="m")


class TestVerifier(unittest.TestCase):
    def test_no_indicator(self):
        self.assertEqual(verifier.verdict(False, None), verifier.NO_INDICATOR)
        # even a (hypothetical) match is irrelevant if the indicator never fired
        self.assertEqual(verifier.verdict(False, R(matched=True)), verifier.NO_INDICATOR)

    def test_unverified(self):
        self.assertEqual(verifier.verdict(True, None), verifier.UNVERIFIED)

    def test_confirmed(self):
        self.assertEqual(verifier.verdict(True, R(matched=True)), verifier.CONFIRMED)

    def test_not_confirmed_is_the_trap(self):
        self.assertEqual(verifier.verdict(True, R(matched=False)), verifier.NOT_CONFIRMED)

    def test_test_error_not_counted_as_negative(self):
        self.assertEqual(verifier.verdict(True, R(matched=False, error="timeout")),
                         verifier.TEST_ERROR)

    def test_make_finding_carries_status_and_evidence(self):
        f = verifier.make_finding(
            endpoint="/health", issue="debug", indicator="toy-debug-indicator",
            indicator_fired=True, validation="toy-health-debug-validation",
            validation_result=R(matched=False), tech_severity="high",
            business_importance="low",
        )
        self.assertEqual(f.status, verifier.NOT_CONFIRMED)
        self.assertEqual(f.evidence["matched"], False)
        self.assertEqual(f.business_importance, "low")


if __name__ == "__main__":
    unittest.main()
