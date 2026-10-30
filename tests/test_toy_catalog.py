"""Phase 2 consistency guards for the scaled toy: the catalog, the asset registry,
and the answer key must all agree with each other and with the template YAML."""
import json
import os
import unittest

import yaml

from nucleipilot import policy, registry
from nucleipilot.toyapp import ANSWER_KEY

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(REPO, "templates")


def _yaml_severity(filename):
    with open(os.path.join(TEMPLATES, filename), encoding="utf-8") as fh:
        return yaml.safe_load(fh)["info"]["severity"]


class TestToyCatalog(unittest.TestCase):
    def setUp(self):
        self.cat = policy.toy_catalog()

    def test_catalog_has_seven_toy_templates(self):
        self.assertEqual(len(self.cat), 7)

    def test_catalog_files_exist_and_severity_matches_yaml(self):
        for tid, spec in self.cat.items():
            path = os.path.join(TEMPLATES, spec.filename)
            self.assertTrue(os.path.exists(path), f"{tid}: missing {spec.filename}")
            self.assertEqual(
                spec.severity, _yaml_severity(spec.filename),
                f"{tid}: catalog severity != YAML severity",
            )

    def test_cost_model(self):
        for spec in self.cat.values():
            if spec.kind == "indicator":
                self.assertEqual(spec.cost, 0, f"{spec.id}: indicators cost 0")
            else:
                self.assertEqual(spec.cost, 1, f"{spec.id}: validations cost 1")

    def test_shared_debug_indicator_resolves_per_endpoint(self):
        docs = policy.validation_for_endpoint("toy-debug-indicator", "/docs", self.cat)
        health = policy.validation_for_endpoint("toy-debug-indicator", "/health", self.cat)
        self.assertEqual(docs.id, "toy-docs-debug-validation")
        self.assertEqual(health.id, "toy-health-debug-validation")
        # the shared indicator itself has no single endpoint
        self.assertIsNone(self.cat["toy-debug-indicator"].endpoint)

    def test_answer_key_references_live_in_catalog(self):
        for iid, spec in ANSWER_KEY.items():
            self.assertIn(spec["indicator"], self.cat, f"{iid} indicator not in catalog")
            self.assertIn(spec["validation"], self.cat, f"{iid} validation not in catalog")

    def test_divergence_present(self):
        admin = ANSWER_KEY["ISSUE-ADMIN"]["tech_severity"]
        debug = ANSWER_KEY["ISSUE-DEBUG"]["tech_severity"]
        rank = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        self.assertLess(rank[admin], rank[debug],
                        "divergence broken: business-critical admin must be lower severity than docs-debug")

    def test_toyapp_answer_key_matches_config_json(self):
        with open(os.path.join(REPO, "config", "toy_answer_key.json"), encoding="utf-8") as fh:
            akj = json.load(fh)["issues"]
        self.assertEqual(set(akj), set(ANSWER_KEY))
        for iid, spec in ANSWER_KEY.items():
            for field in ("endpoint", "real", "tech_severity", "indicator", "validation"):
                self.assertEqual(akj[iid].get(field), spec.get(field), f"{iid}.{field} mismatch")

    def test_asset_registry_loads_with_business_importance(self):
        reg = registry.load_registry()
        asset = registry.get_asset(reg, "toy-app")
        self.assertEqual(registry.budget(asset), 2)
        self.assertEqual(registry.business_importance(asset, "/payments"), "critical")
        self.assertEqual(registry.business_importance(asset, "/docs"), "low")
        # the divergence as the registry sees it: /payments outranks /docs on business
        self.assertGreater(
            registry.importance_rank(registry.business_importance(asset, "/payments")),
            registry.importance_rank(registry.business_importance(asset, "/docs")),
        )

    def test_gate_accepts_toy_and_rejects_unknown(self):
        ok = policy.validate_choice("toy-admin-validation", ["toy-admin-validation"], self.cat)
        self.assertTrue(ok.ok)
        bad = policy.validate_choice("not-a-real-template", ["toy-admin-validation"], self.cat)
        self.assertFalse(bad.ok)


if __name__ == "__main__":
    unittest.main()
