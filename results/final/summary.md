# NucleiPilot — Experimental Findings

*Authorized local sandbox only (127.0.0.1). Model: `openai/gpt-4o-mini` via OpenRouter.
Nuclei v3.11.1. See `environment.txt` and `comparison.csv` for the raw record, and
`traces/` for every run's full decision trace.*

## Objective
Test whether a policy-constrained LLM planner improves follow-up selection around Nuclei
compared with a **fixed/exhaustive** workflow and a **rule-based adaptive** workflow.

## Setup
Toy sandbox, 5 ground-truth profiles (`admin`, `debug`, `benign`, `clean`, `both`).
Two experiment blocks: **A** full budget (=2, enough to validate every signal), **B**
budget=1 on `both` with a target context (admin surface = business-critical payments;
debug = low-impact docs). LLM repeated **3×** per case. Ground truth is defined in the
sandbox, independent of the agent.

## Results

**Block A — accuracy (aggregated over 5 profiles):**

| Planner | Runs | Precision | Recall | FP | Avg templates | Avg latency | Tokens | Invalid/blocked |
|---|---|---|---|---|---|---|---|---|
| Fixed | 5 | 1.00 | 1.00 | 0 | 4.00 | 5.9s | 0 | 0 |
| Rule | 5 | 1.00 | 1.00 | 0 | 3.00 | 4.4s | 0 | 0 |
| LLM | 15 | 1.00 | 1.00 | 0 | 3.00 | 6.0s | ~6.5k | 0 |

**Block B — prioritization under a 1-follow-up budget (`both` + payments context):**

| Planner | Chose business-critical check | Picked first |
|---|---|---|
| Rule | 0 / 1 | `demo-debug-validation` (highest severity) |
| LLM | **3 / 3** | `demo-admin-validation` (highest business impact) |

**Block C — context sensitivity (same target, context FLIPPED: debug = business-critical):**

| Planner | Chose business-critical check | Picked first |
|---|---|---|
| Rule | 0 / 1 | `demo-debug-validation` (unchanged — rule ignores context) |
| LLM | **3 / 3** | `demo-debug-validation` (flipped to match the new context) |

Blocks B and C together show the LLM's choice **flips with the business context (6/6)**, while
the rule is context-blind. This rules out "the model just favours one issue."

## Observations
- **What worked:** (a) The LLM reliably prioritized the business-critical issue under a
  budget constraint (3/3), where the severity rule could not (0/1). (b) The divergence is
  *principled*: in Block A `both` (no context given) the LLM picked the same severity-first
  order as the rule — it only overrode it when context justified it, and when the context is
  *flipped* (Block C) the choice flips too (6/6) — proving the decision is context-driven,
  not biased. (c) No false positives on the `benign` trap by any planner.
- **What failed / added no value:** At full budget the LLM matched — did not beat — the
  rule's perfect accuracy, while adding ~1.6s latency and token cost per run.
- **Where human review belongs:** Under budget, the un-chosen real issue is surfaced as
  `UNVERIFIED` (not silently dropped, not falsely confirmed) — an explicit coverage gap for
  a human or the next budget.
- **Reliability:** 0 invalid/blocked actions across 15 live LLM runs; and when failure is
  injected (malformed JSON, invented template id, out-of-scope target) the harness fails
  safe — see `safety_checks.md`.

## Generalization (real CVE, outside the toy lab)
The same agent pattern was run against a real **Grafana 8.3.0** container using Nuclei's
**official** templates. Given the detected version and two candidate CVEs (budget 1), the LLM
chose the applicable `CVE-2021-43798` over the inapplicable `CVE-2020-13379` and confirmed a
real arbitrary-file-read (`/etc/passwd`). This shows the approach is not tied to our own toy
templates. Evidence: `results/final/vulhub_grafana_demo.json`.

## Limitations
Toy environment, 2 issue classes, small sample, a single model, localhost only. "Decision
correct" in Block B is defined as the business-impact-optimal choice given the stated
context. No claim of exploitation capability or production readiness. Perfect detection
accuracy is expected in a controlled lab and is **not** the headline result.

## Preliminary recommendation (full decision in docs/build_decision.md)
**Conditional.** Use rules for detection; use the LLM specifically as a **context-aware
triage/prioritization layer**, which is the only place it demonstrably beat the baseline.
We validated the *mechanism* on a real CVE (Grafana 8.3.0 / VulHub); before any pilot, extend
that to a broader real-world benchmark (multiple CVEs, messier targets, full metrics).

**Decision-flipping fact:** if, on a real-CVE target with messier input, the LLM shows no
prioritization advantage over rules *or* a materially higher invalid/blocked rate, the case
for the LLM layer collapses to "rules only (+ LLM for analyst-facing explanations)."
