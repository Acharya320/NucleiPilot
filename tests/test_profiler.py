"""The context profiler's pure assembly (no Nuclei): the shared debug indicator
must fan out to BOTH /docs and /health with the correct per-endpoint validations."""
import unittest
from types import SimpleNamespace

from nucleipilot import policy, registry, profiler


def SR(matched, urls):
    return SimpleNamespace(matched=matched, raw=[{"matched-at": u} for u in urls],
                           matched_at=(urls[0] if urls else None))


class TestProfiler(unittest.TestCase):
    def setUp(self):
        self.cat = policy.toy_catalog()
        self.asset = registry.get_asset(registry.load_registry(), "toy-app")

    def test_endpoint_for_url(self):
        eps = ["/payments", "/account", "/docs", "/health", "/home"]
        self.assertEqual(profiler._endpoint_for_url("http://127.0.0.1:8777/account/export", eps), "/account")
        self.assertEqual(profiler._endpoint_for_url("http://127.0.0.1:8777/docs", eps), "/docs")
        self.assertEqual(profiler._endpoint_for_url("http://127.0.0.1:8777/payments", eps), "/payments")
        self.assertIsNone(profiler._endpoint_for_url("http://127.0.0.1:8777/nope", eps))

    def test_build_profile_maps_shared_debug_indicator_to_both_endpoints(self):
        base = "http://127.0.0.1:8777"
        discovery = {
            "toy-admin-indicator": SR(True, [base + "/payments"]),
            "toy-debug-indicator": SR(True, [base + "/docs", base + "/health"]),
            "toy-pii-indicator": SR(True, [base + "/account/export"]),
        }
        prof = profiler.build_profile(self.asset, self.cat, discovery, base_url=base)
        eps = prof.endpoints
        self.assertEqual(eps["/payments"]["candidate_validations"], ["toy-admin-validation"])
        self.assertEqual(eps["/docs"]["candidate_validations"], ["toy-docs-debug-validation"])
        self.assertEqual(eps["/health"]["candidate_validations"], ["toy-health-debug-validation"])
        self.assertEqual(eps["/account"]["candidate_validations"], ["toy-pii-validation"])
        self.assertEqual(eps["/home"]["fired_indicators"], [])
        self.assertEqual(prof.budget, 2)
        self.assertEqual(eps["/payments"]["business_importance"], "critical")
        self.assertEqual(eps["/docs"]["business_importance"], "low")

    def test_no_indicator_means_no_candidates(self):
        discovery = {"toy-admin-indicator": SR(False, [])}
        prof = profiler.build_profile(self.asset, self.cat, discovery)
        self.assertEqual(prof.endpoints["/payments"]["fired_indicators"], [])
        self.assertEqual(prof.endpoints["/payments"]["candidate_validations"], [])


if __name__ == "__main__":
    unittest.main()
