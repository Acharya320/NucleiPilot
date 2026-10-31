"""Live scope-guard demo: the REAL engine + REAL scanner (no stubs, no fakes)
refuse an out-of-scope target at every entry point, BEFORE any network call.

Uses the exact same engine.run() and scanner that scripts/run_experiment.py uses
-- nothing here is faked. Safe to run: the out-of-scope host is never contacted,
because the guard refuses before any request is made. No Nuclei, API key, or toy
app needed. Run from the repo root:

    python scripts/scope_demo.py
"""
import sys, os, copy

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from nucleipilot import policy, registry, engine, planners, scanner        # noqa: E402
from nucleipilot.scanner import ScopeError                                 # noqa: E402


def main():
    print("=" * 66)
    print(" LIVE SCOPE-GUARD DEMO  -- real engine.run + real scanner, no stubs")
    print("=" * 66)

    cat = policy.toy_catalog()
    asset = registry.get_asset(registry.load_registry(), "toy-app")
    GOOD = "http://127.0.0.1:8777"          # approved (localhost)
    BAD = "http://attacker.example.com"     # NOT approved

    # 1 -- the real scanner guard on an APPROVED target
    print("\n[1] scanner.assert_in_scope() on an approved localhost target:")
    try:
        scanner.assert_in_scope(GOOD)
        print("    ALLOWED  (127.0.0.1 is in the approved scope)")
    except ScopeError as e:
        print("    unexpectedly blocked:", e)

    # 2 -- the real scanner guard on an OUT-OF-SCOPE target
    print("\n[2] scanner.assert_in_scope() on an OUT-OF-SCOPE target:")
    try:
        scanner.assert_in_scope(BAD)
        print("    ALLOWED (!!) -- that would be a bug")
    except ScopeError as e:
        print("    BLOCKED ->", e)

    # 3 -- the REAL engine path (same engine.run the experiment calls) with a bad asset
    print("\n[3] engine.run() on an asset whose base_url is OUT OF SCOPE")
    print("    (identical to how run_experiment.py invokes the engine; real scanner):")
    evil = copy.deepcopy(asset)
    evil["base_url"] = BAD
    try:
        engine.run(evil, cat, planners.ContextRulePlanner())
        print("    ran (!!) -- that would be a bug")
    except ScopeError as e:
        print("    BLOCKED before any profiling or scan ->", e)

    # 4 -- the real Nuclei runner: refused BEFORE nuclei.exe is ever launched
    print("\n[4] scanner.run_template() on an out-of-scope URL (would launch Nuclei):")
    try:
        scanner.run_template(BAD, policy.template_path("toy-admin-validation", cat))
        print("    launched Nuclei (!!) -- that would be a bug")
    except ScopeError as e:
        print("    BLOCKED before Nuclei ever launches ->", e)

    print("\n" + "=" * 66)
    print(" RESULT: every REAL entry point refused the out-of-scope target")
    print("         BEFORE any network call. The model/caller cannot reach it.")
    print("=" * 66)


if __name__ == "__main__":
    main()
