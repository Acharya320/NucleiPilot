# NucleiPilot — Work Log

A dated record of every meaningful build/experiment step, so the final analysis
and README are grounded in what actually happened. Newest entries at the bottom.

**Environment:** Windows 11 · Python 3.14.7 · Nuclei v3.11.1 (`go install`, at
`C:\Users\SUDIPTA\go\bin\nuclei.exe`) · OpenRouter (`openai/gpt-4o-mini`).

| Date/time | Target profile | Backend | Planner | What was run | Result | Next step |
|---|---|---|---|---|---|---|
| 27 Oct | — | — | — | Env setup: installed Nuclei v3.11.1, created py3.14 venv, `pip install -r requirements.txt` | All deps OK on 3.14 | Build sandbox |
| 27 Oct | admin/benign/clean | n/a (in-proc) | — | `scripts/smoke_sandbox.py` | Indicator vs validation behaviour correct; `benign` shows debug indicator but NOT exposure | Write templates |
| 27 Oct | — | — | — | `nuclei -validate -t templates` | "All templates validated successfully" (4 templates) | Real scan |
| 27 Oct | admin | **real Nuclei** | (scanner only) | `scripts/scan_once.py --profile admin` → `results/day1_admin_scan.json` | admin indicator+validation MATCHED; debug templates correctly did NOT match; authentic HTTP evidence captured | Build planners |
| 27 Oct | clean/benign/admin/both | real Nuclei | fixed, rule | `scripts/compare_rule_vs_fixed.py` | Rule uses fewer templates (clean 2 vs 4), **no false positive incl. the benign trap**, same verdicts | Add LLM planner |
| 27 Oct | both (budget 1) | real Nuclei | **llm** (gpt-4o-mini) vs rule | `scripts/llm_decision_demo.py` → `results/day2_llm_both_budget1.json` | With payments-context, LLM chose `demo-admin-validation` (business impact); severity rule chose `demo-debug-validation`. Policy guard approved the LLM choice. ~556 tokens. | Day 3: repeat 3×, metrics, failure/safety cases |
| 27 Oct | all (Block A) | real Nuclei | fixed/rule/llm×3 | `scripts/run_experiment.py` → `results/final/comparison.csv` | Full budget: all planners precision=recall=1.00, 0 FP; rule+llm avg 3.0 templates vs fixed 4.0; llm 0 invalid over 15 runs, ~6.5k tokens | Write summary.md |
| 27 Oct | both (Block B, budget 1) | real Nuclei | rule vs llm×3 | same harness | Prioritization: rule 0/1, **llm 3/3** chose the business-critical admin check (stable across repeats) | VulHub demo (Day 4-5) |
| 27 Oct | — (fakes) | none | safety | `scripts/safety_checks.py` → `results/final/safety_checks.md` | 4/4 pass: out-of-scope reject, invented-id block, malformed-JSON safe stop, STOP on clean. Test suite now 23 tests. | — |
| 27 Oct | 'both' flipped ctx (Block C) | real Nuclei | rule vs llm×3 | `scripts/run_experiment.py` | Context flip: LLM 3/3 picked debug when debug=critical (B→admin, C→debug); context-sensitivity verified (6/6), not biased | — |
| 27 Oct | **Grafana 8.3.0 (real app)** | real Nuclei (OFFICIAL templates) | llm | `scripts/vulhub_demo.py` → `results/final/vulhub_grafana_demo.json` | **Generalization:** agent read version 8.3.0, chose applicable CVE-2021-43798 over distractor CVE-2020-13379, confirmed real /etc/passwd read. Same framework, real app we didn't write. | Written brief + deck + video |
| 30 Oct | **scaled toy (5 endpoints)** | real Nuclei | A/B1/B2/C×3 | `scripts/run_experiment.py` → `results/final/` (E1/E2/E3) | Scaled to the severity-vs-business divergence + a benign trap. Budget 2: **B1** (severity) missed business-critical /payments+/account and hit the trap; **B2** (context rule) and **C** (LLM) both confirmed /payments+/account. **C ties B2 on outcome** (same findings all 3 runs; pick-order varies — LLM nondeterminism). | Grafana on same engine |
| 30 Oct | **Grafana 8.3.0 (real app)** | real Nuclei (our local CVE templates) | llm | `scripts/run_grafana.py` → `results/final/grafana_demo.json` | Same engine, new asset: fingerprinted 8.3.0, chose applicable CVE-2021-43798 over distractor (0 CVE-specific code); confirmed read-only via planted marker + /etc/passwd. Official-template run kept as corroboration. | Phase 7 cleanup |
| 30 Oct | — | — | — | **Phase 7:** committed the pre-cleanup tree to git, then retired the v1 2-issue demo (sandbox/planner/workflow/evaluate, demo-* templates, old scripts/tests); reconciled all evidence into `results/final/`; rewrote README to the scaled flow; dropped `_v2` suffixes. Suite now **37 tests** (v1 tests removed). | Demo video + GitHub push |

## Notes / decisions
- **v1 → scaled toy (30 Oct):** the 27 Oct entries above describe the original 2-issue demo
  (admin + debug). Phase 7 scaled the bench to 5 endpoints with the severity-vs-business divergence
  and retired the v1 code; `results/final/` now holds the scaled-toy evidence. The earlier v1 numbers
  (e.g. "llm 3/3", "6/6") belong to that superseded demo and remain in git history.
- **Target strategy:** toy sandbox = measurement bench (controllable ground truth);
  a VulHub real-CVE environment (lead: Apache CVE-2021-41773) = realism/generalization
  demo on Day 4–5. Juice Shop dropped — Nuclei (signature scanner) pairs poorly with its
  injection/business-logic flaws.
- **Caveat:** the LLM result so far is a single run; Day 3 adds repetition + failure modes.
