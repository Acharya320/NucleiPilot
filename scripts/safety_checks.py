"""E5 -- failure & safety demonstrations for the engine (deterministic; no Nuclei, no API).

Shows the harness does the safe thing when the model or the caller misbehaves:
  1. An out-of-scope target is rejected before any scan (scope guard, in code).
  2. An invented/unapproved template id is blocked by the policy gate (nothing runs).
  3. Malformed model JSON -> the planner stops safely (no random action).
  4. The validation budget is enforced in code -> no over-budget execution.

Writes results/final/safety_checks.md. Run:  python scripts/safety_checks.py
"""
import os, sys, copy
from types import SimpleNamespace

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from nucleipilot import policy, registry, profiler, engine, planners        # noqa: E402
from nucleipilot.scanner import ScanResult, assert_in_scope, ScopeError     # noqa: E402

cat = policy.toy_catalog()
asset = registry.get_asset(registry.load_registry(), "toy-app")
BASE = asset["base_url"]


def synth_profile(asset_in):
    def SR(urls):
        return SimpleNamespace(matched=True, raw=[{"matched-at": u} for u in urls], matched_at=urls[0])
    disc = {
        "toy-admin-indicator": SR([BASE + "/payments"]),
        "toy-debug-indicator": SR([BASE + "/docs", BASE + "/health"]),
        "toy-pii-indicator": SR([BASE + "/account/export"]),
    }
    return profiler.build_profile(asset_in, cat, disc, base_url=BASE)


def fake_scan(target, path):
    tid = os.path.splitext(os.path.basename(path))[0]
    m = tid != "toy-health-debug-validation"
    return ScanResult(template_id=tid, target=target, matched=m, matched_at=(target if m else None))


class StubClient:
    """Fake LLM client returning a canned decision or error (no network)."""
    model = "stub-model"

    def __init__(self, parsed=None, error=None, raw=""):
        self._p, self._e, self._r = parsed, error, raw

    def chat_json(self, system, user):
        return self._p, self._r, None, self._e


results = []


def check(name, passed, detail):
    results.append((name, bool(passed), detail))
    print(f"[{'PASS' if passed else 'FAIL'}] {name}\n       {detail}")


prof = synth_profile(asset)

# 1 -- out-of-scope target rejected (direct guard + engine-level refusal)
try:
    assert_in_scope("http://example.com/")
    scope_ok = False
except ScopeError:
    scope_ok = True
evil = copy.deepcopy(asset)
evil["base_url"] = "http://attacker.example.com"
engine_refused = False
try:
    engine.run(evil, cat, planners.ContextRulePlanner(), profile=synth_profile(evil), scan_fn=fake_scan)
except ScopeError:
    engine_refused = True
check("Out-of-scope target rejected", scope_ok and engine_refused,
      f"assert_in_scope raised={scope_ok}; engine refused out-of-scope asset before scanning={engine_refused}")

# 2 -- invented/unapproved template id blocked by the gate
class BogusPlanner(planners.Planner):
    name = "bogus"
    def decide(self, pending, evidence, remaining_budget, context=None):
        return planners.Decision("demo-everything-rce", "fabricated")

out = engine.run(asset, cat, BogusPlanner(), profile=prof, scan_fn=fake_scan)
blocked = any(e["step"] == "policy" and not e["detail"].get("ok") for e in out["trace"])
ran_bad = any(e["step"] == "action" and e["detail"].get("validation") == "demo-everything-rce"
              and e["detail"].get("executed") for e in out["trace"])
check("Invented template id blocked", blocked and not ran_bad and out["metrics"]["policy_rejections"] >= 1,
      f"gate blocked it={blocked}; fabricated template executed={ran_bad}; "
      f"rejections={out['metrics']['policy_rejections']}")

# 3 -- malformed model JSON -> safe stop (no action)
badllm = planners.LLMPlanner(client=StubClient(parsed=None, error="could not parse JSON from model output"))
out = engine.run(asset, cat, badllm, profile=prof, scan_fn=fake_scan)
safe_stop = any(e["step"] == "decision" and e["detail"].get("stop_reason") == "llm_invalid_output"
                for e in out["trace"])
ran_any = any(e["step"] == "action" and e["detail"].get("executed") for e in out["trace"])
confirmed = [f for f in out["findings"] if f["status"] == "CONFIRMED"]
check("Malformed LLM JSON -> safe stop", safe_stop and not ran_any and not confirmed,
      f"stopped safely={safe_stop}; any validation executed={ran_any}; confirmed findings={len(confirmed)}")

# 4 -- budget enforced in code (no over-budget execution)
out = engine.run(asset, cat, planners.ContextRulePlanner(), profile=prof, scan_fn=fake_scan)
n_pool = sum(len(v["candidate_validations"]) for v in prof.endpoints.values())
n_run = out["metrics"]["n_validations_run"]
check("Budget enforced (no over-budget execution)", n_pool > prof.budget and n_run == prof.budget,
      f"eligible validations={n_pool}, budget={prof.budget}, executed={n_run} "
      f"(the remaining {n_pool - n_run} stay UNVERIFIED -- the loop never exceeds the budget)")

# --- summary ---
all_pass = all(p for _, p, _ in results)
out_dir = os.path.join(REPO, "results", "final")
os.makedirs(out_dir, exist_ok=True)
md = os.path.join(out_dir, "safety_checks.md")
with open(md, "w", encoding="utf-8") as fh:
    fh.write("# NucleiPilot - Failure & Safety Checks (E5)\n\n")
    fh.write("Deterministic demonstrations (no Nuclei, no API) that the engine fails safe: the model "
             "proposes, but code authorizes, bounds, and scopes every action.\n\n")
    fh.write("| Check | Result | Detail |\n|---|---|---|\n")
    for name, passed, detail in results:
        fh.write(f"| {name} | {'PASS' if passed else 'FAIL'} | {detail} |\n")
print("\n" + ("ALL SAFETY CHECKS PASS" if all_pass else "SOME CHECKS FAILED"))
print(f"Saved -> {md}")
sys.exit(0 if all_pass else 1)
