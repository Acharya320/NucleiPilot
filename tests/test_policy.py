"""The policy guard: approve legitimate choices, block everything else."""
import unittest

from nucleipilot import policy


class TestPolicyGuard(unittest.TestCase):
    def test_allow_eligible(self):
        r = policy.validate_choice("demo-admin-validation", ["demo-admin-validation"])
        self.assertTrue(r.ok)

    def test_block_unknown_template(self):
        r = policy.validate_choice("demo-everything-rce", ["demo-admin-validation"])
        self.assertFalse(r.ok)

    def test_block_not_eligible_this_step(self):
        r = policy.validate_choice("demo-debug-validation", ["demo-admin-validation"])
        self.assertFalse(r.ok)

    def test_stop_is_always_allowed(self):
        self.assertTrue(policy.validate_choice(None, []).ok)

    def test_template_path_unknown_raises(self):
        with self.assertRaises(KeyError):
            policy.template_path("not-a-real-template")


if __name__ == "__main__":
    unittest.main()
