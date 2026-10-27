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

## Notes / decisions
- **Target strategy:** toy sandbox = measurement bench (controllable ground truth);
  a VulHub real-CVE environment (lead: Apache CVE-2021-41773) = realism/generalization
  demo on Day 4–5. Juice Shop dropped — Nuclei (signature scanner) pairs poorly with its
  injection/business-logic flaws.
- **Caveat:** the LLM result so far is a single run; Day 3 adds repetition + failure modes.
