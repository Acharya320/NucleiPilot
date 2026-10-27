"""Tests for the scoring definitions in evaluate.py."""
import unittest

from nucleipilot import evaluate


class TestEvaluate(unittest.TestCase):
    def test_gt_issues(self):
        self.assertEqual(evaluate.gt_issues({"admin_auth_missing"}), {"admin"})
        self.assertEqual(evaluate.gt_issues(set()), set())

    def test_true_positive(self):
        run = {"assessment": {"admin": "CONFIRMED", "debug": "CLEAN"}}
        sc = evaluate.score_run(run, {"admin"})
        self.assertEqual((sc["tp"], sc["fp"], sc["fn"]), (1, 0, 0))

    def test_false_positive(self):
        run = {"assessment": {"admin": "CONFIRMED", "debug": "CLEAN"}}
        sc = evaluate.score_run(run, set())   # nothing truly present
        self.assertEqual((sc["tp"], sc["fp"], sc["fn"]), (0, 1, 0))

    def test_false_negative_under_budget(self):
        run = {"assessment": {"admin": "UNVERIFIED", "debug": "CONFIRMED"}}
        sc = evaluate.score_run(run, {"admin", "debug"})
        self.assertEqual((sc["tp"], sc["fp"], sc["fn"]), (1, 0, 1))

    def test_precision_recall_na_on_zero(self):
        self.assertIsNone(evaluate.precision(0, 0))
        self.assertIsNone(evaluate.recall(0, 0))
        self.assertEqual(evaluate.fmt(None), "N/A")
        self.assertEqual(evaluate.fmt(1.0), "1.00")


if __name__ == "__main__":
    unittest.main()
