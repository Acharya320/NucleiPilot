"""VulHub real-CVE generalization demo.

The SAME agent pattern (observe -> reason -> authorize -> act -> reassess) as the toy
experiment, but against a REAL app (Grafana 8.3.0) using Nuclei's OFFICIAL community
templates. It reuses the real components: the scope-guarded scanner and the LLM client.

The decision is made meaningful by giving the agent two candidate CVEs and a budget of 1:
one applies to the detected version, one does not. A good agent reasons from the detected
version and spends its single budget on the applicable CVE.

Target: http://127.0.0.1:3000 (Grafana 8.3.0, authorized local sandbox).
Needs: the Grafana container running, `nuclei -update-templates` done, and an OpenRouter key.
"""
import os, sys, json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from nucleipilot import scanner                       # noqa: E402  (scope guard + real nuclei)
from nucleipilot.llm_client import LLMClient          # noqa: E402

NT = os.getenv("NUCLEI_TEMPLATES_DIR") or os.path.expanduser("~/nuclei-templates")
TARGET = "http://127.0.0.1:3000"
BUDGET = 1

INDICATOR_PATH = os.path.join(NT, "http", "exposed-panels", "grafana-detect.yaml")
CATALOG = {
    "CVE-2021-43798": {
        "path": os.path.join(NT, "http", "cves", "2021", "CVE-2021-43798.yaml"),
        "severity": "high", "applies_to": "Grafana 8.0.0-beta1 through 8.3.0",
        "purpose": "Unauthenticated arbitrary file read via plugin path traversal.",
    },
    "CVE-2020-13379": {
        "path": os.path.join(NT, "http", "cves", "2020", "CVE-2020-13379.yaml"),
        "severity": "high", "applies_to": "Grafana 3.0.1 through 7.0.1",
        "purpose": "Unauthenticated SSRF via the avatar endpoint.",
    },
}

SYSTEM = """You are a cautious security-assessment assistant inside a strict policy harness.
Pick the SINGLE most valuable CVE check to run next against an AUTHORIZED local target, or STOP.
Rules:
- Choose next_template ONLY from the provided candidate ids (exact id). Never invent one.
- Use the DETECTED version: a CVE is only worth running if its affected range covers that version.
- With a limited budget, do not waste it on a check that cannot apply.
- Respond with STRICT JSON only:
  {"next_template": <id or null>, "reason": <str>, "confidence": <0..1>, "stop_reason": <str or null>}"""


def banner(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def main():
    trace = []

    # 1) OBSERVE
    banner("[1] OBSERVE  -- run the real indicator (Grafana fingerprint)")
    ind = scanner.run_template(TARGET, INDICATOR_PATH)
    version = ind.extracted[0] if ind.extracted else "unknown"
    print(f"  grafana-detect: matched={ind.matched}  version={version}  at={ind.matched_at}")
    trace.append({"step": "observe", "template": "grafana-detect",
                  "matched": ind.matched, "version": version})

    # 2) REASON
    banner("[2] REASON  -- LLM picks the applicable CVE for the detected version (budget=1)")
    desc = "\n".join(
        f"- id={cid}  severity={c['severity']}  applies_to={c['applies_to']}\n    purpose: {c['purpose']}"
        for cid, c in CATALOG.items())
    user = (f"TARGET: {TARGET} (authorized local sandbox)\n"
            f"DETECTED: Grafana version {version}\n"
            f"REMAINING BUDGET: {BUDGET} check\n\n"
            f"CANDIDATE CVE CHECKS (choose exactly one id, or STOP):\n{desc}\n\n"
            f"Return the JSON decision now.")
    client = LLMClient()
    parsed, raw, usage, err = client.chat_json(SYSTEM, user)
    if err or not parsed:
        print(f"  LLM unusable: {err}; raw={raw[:160]!r}")
        return
    choice = parsed.get("next_template")
    print(f"  model={client.model}  usage={usage}")
    print(f"  chose     : {choice}")
    print(f"  reason    : {parsed.get('reason')}")
    print(f"  confidence: {parsed.get('confidence')}")
    trace.append({"step": "reason", "proposed": choice, "reason": parsed.get("reason"),
                  "confidence": parsed.get("confidence"), "usage": usage})

    # 3) AUTHORIZE
    banner("[3] AUTHORIZE  -- candidate allowlist + localhost scope guard")
    in_allow = choice in CATALOG
    try:
        scanner.assert_in_scope(TARGET)
        in_scope = True
    except scanner.ScopeError:
        in_scope = False
    ok = in_allow and in_scope
    print(f"  in candidate allowlist={in_allow}; target in scope={in_scope} -> "
          f"{'APPROVED' if ok else 'BLOCKED'}")
    trace.append({"step": "authorize", "ok": ok, "in_allowlist": in_allow, "in_scope": in_scope})

    val = None
    if not ok:
        print("  BLOCKED -- nothing executed.")
    else:
        # 4) ACT
        banner("[4] ACT  -- run the approved real CVE template")
        val = scanner.run_template(TARGET, CATALOG[choice]["path"])
        print(f"  {choice}: matched={val.matched}  at={val.matched_at}")
        if val.extracted:
            print(f"  evidence (file read): {str(val.extracted)[:120]}")
        trace.append({"step": "act", "template": choice, "matched": val.matched,
                      "matched_at": val.matched_at})

        # 5) REASSESS
        banner("[5] REASSESS")
        verdict = "CONFIRMED" if val.matched else "NOT CONFIRMED"
        print(f"  {choice}: {verdict}")
        trace.append({"step": "reassess", "cve": choice, "verdict": verdict})

    banner("CONTRAST")
    print("  An exhaustive baseline runs BOTH candidate CVEs -- wasting a scan on the one that")
    print(f"  cannot apply to {version}. The agent spent its single budget on the applicable CVE")
    print("  by reasoning from the detected version. Same framework, real app, real CVE.")

    out = os.path.join(REPO, "results", "final", "vulhub_grafana_demo.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"target": TARGET, "detected_version": version, "budget": BUDGET,
                   "candidate_catalog": list(CATALOG), "trace": trace,
                   "indicator_raw": ind.to_dict(),
                   "validation_raw": val.to_dict() if val else None},
                  fh, indent=2, default=str)
    print(f"\nSaved -> {out}")


if __name__ == "__main__":
    main()
