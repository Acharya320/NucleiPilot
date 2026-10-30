# NucleiPilot - Findings: what we claim, and the evidence

*One page. Every claim points to a file you can open and a command you can re-run. The framing is
deliberately honest - read `docs/toy_spec.md` §7 for what this PoC can and cannot prove.*

**In one line:** NucleiPilot is a *governed, evidence-driven* agent around Nuclei - the model proposes,
code authorizes, bounds, and verifies every action. On a small toy its per-decision quality ties a
well-tuned rule; its durable value is governance and generalization, not out-picking a rule.

---

## What we CAN claim (with evidence)

| # | Claim | Result | Evidence |
|---|---|---|---|
| 1 | **A bounded, auditable loop** - model proposes, *code* authorizes every scan (scope + allowlist + budget), with a full trace. | Out-of-scope target, invented template id, malformed LLM JSON, and over-budget proposals all **fail safe** (nothing unsafe runs). | `safety_checks.md` (E5); `traces/*.json` |
| 2 | **Evidence-based verdicts** - a fired template is a hint, not a finding; false positives are rejected *on evidence*. | `/docs` and `/health` send the **identical** debug indicator; only the validation's content signature separates them → `/docs` **CONFIRMED**, `/health` **NOT_CONFIRMED**. | `e3_trap.json`; `summary.md` (E3) |
| 3 | **Business-aware prioritization under a tight budget.** | At budget 2: severity-only **B1** missed the business-critical `/payments` + `/account` and wasted a slot on the trap; context-aware **B2** and the LLM **C** both confirmed `/payments` + `/account`. | `summary.md` (E1); `comparison.csv` |
| 4 | **Decisions follow business context**, not a fixed favorite. | Flip `/payments`↔`/docs` importance (responses unchanged): **B2 and C both shift** their first pick to `/docs`. | `summary.md` (E2) |
| 5 | **The LLM is stable and matches the strong rule** (the honest headline). | **C** made identical choices across **3 runs**; C's confirmed set **equals B2's**. This is *not* "the LLM beats rules." | `summary.md` (E1) |
| 6 | **The same engine generalizes to a real app** - a new target is just another registry + catalog entry. | Local Grafana 8.3.0: the LLM reasoned version → **applicable CVE-2021-43798** over the 2020-13379 distractor with **0 CVE-specific code**; harmless planted-marker read **CONFIRMED** (+ `/etc/passwd` secondary **CONFIRMED**). | `grafana_demo.json` (E4); `e6_generalization_note.md` (E6) |

## What we do NOT claim (equally important)

- **Not** that the LLM beats a well-tuned rule here. On a small, fully-labeled toy a few lines of
  context-aware rule (B2) tie it - a property of the toy's size, not a weakness of the agent (§7).
- **Not** real-world reliability. Whether LLM reasoning beats rules on messy, unlabeled, real targets is
  exactly what the 90-day pilot in `docs/build_decision.md` is designed to measure.
- **Not** improved *detection*. Nuclei already detects; the agent helps *choose and triage*, under control.
- All testing was **localhost-only and read-only**, against systems we control or a throwaway container.

---

## Reproduce (each is one command from the repo root)

```
python -m unittest discover -s tests            # 55 deterministic tests (no Nuclei/API)
python scripts/smoke_toyapp.py                  # the toy app serves the exact signatures
python scripts/run_experiment_v2.py             # E1/E2/E3 -> this folder (needs Nuclei; LLM key for C)
python scripts/safety_checks_v2.py              # E5 fail-safe demonstrations (no deps)
python scripts/run_grafana.py                   # E4 real-app demo (needs Docker + Nuclei + LLM key)
```

Outputs land in `results/experiment/`: `comparison.csv`, `summary.md` (E1-E3, generated from the runs),
`e3_trap.json`, `safety_checks.md` (E5), `grafana_demo.json` (E4), `e6_generalization_note.md` (E6),
and per-run `traces/`.
