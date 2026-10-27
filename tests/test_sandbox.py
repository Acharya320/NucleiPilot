"""The toy sandbox: ground truth and the all-important 'benign' trap."""
import unittest

from nucleipilot import sandbox


class TestSandbox(unittest.TestCase):
    def test_ground_truth(self):
        self.assertEqual(sandbox.ground_truth("admin"), {"admin_auth_missing"})
        self.assertEqual(sandbox.ground_truth("debug"), {"debug_exposed"})
        self.assertEqual(sandbox.ground_truth("benign"), set())
        self.assertEqual(sandbox.ground_truth("clean"), set())
        self.assertEqual(sandbox.ground_truth("both"),
                         {"admin_auth_missing", "debug_exposed"})

    def test_unknown_profile_raises(self):
        with self.assertRaises(ValueError):
            sandbox.ground_truth("bogus")

    def test_benign_indicator_without_exposure(self):
        # The crux: debug indicator fires, but exposure is NOT real.
        r = sandbox._responses("benign")
        self.assertEqual(r["/debug/config"]["debug"], "true")
        self.assertEqual(r["/debug/confirm"]["debug_exposure"], "not-exposed")

    def test_clean_all_absent(self):
        r = sandbox._responses("clean")
        self.assertEqual(r["/metadata"]["management_surface"], "absent")
        self.assertEqual(r["/debug/config"]["debug"], "false")


if __name__ == "__main__":
    unittest.main()
