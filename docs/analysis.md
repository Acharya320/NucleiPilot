# Part 2 — POC Evaluation (One Page)

**Goal.** Can an LLM help select useful follow-up checks around Nuclei, safely and under a limited scan budget? Nuclei remains the scanner; NucleiPilot adds planning, an independent permission check, and evidence-based finding status.

## What worked

- **Business-aware decisions:** With two validation slots, both the LLM planner (**C**) and a context-aware rule (**B2**) confirmed the important `/payments` and `/account` issues. The severity-only rule (**B1**) selected `/docs` and a benign `/health` signal instead.
- **The decision responds to context:** When business importance was switched, B2 and C both prioritized `/docs` first (E2). This shows sensitivity to the supplied context, not an advantage over rules.
- **Evidence matters:** In a separate test (E3), the `/docs` finding was confirmed by a content check; the similar-looking `/health` signal was **not confirmed**.
- **Reuse on another application:** On a local Grafana 8.3.0 container, the LLM chose a relevant CVE-2021-43798 template from two catalog options. The saved run reports a successful read-only file check (E4). This demonstrates feasibility on one additional target, not broad generalization.
- **Controlled execution:** Four deterministic tests passed for out-of-scope targets, unknown template IDs, malformed model output, and validation-budget enforcement (E5).

## What did not work or is unproven

The LLM **did not outperform** the stronger non-LLM rule: both confirmed the same important findings across three LLM runs. The LLM varied its selection order. We did not measure improvement in Nuclei's detection ability, real-world false-positive rates, or operational cost savings. The fixed exhaustive reference used **four** validation checks; B1/B2/C used **two**, so the fixed run is a coverage reference rather than a same-budget comparator.

## Where people are still required

A human provides written authorization, approved targets and templates, per-asset business importance, and the permitted budget. A human also defines the toy application's expected results, reviews findings, and decides on any remediation or intrusive investigation. The POC does not autonomously exploit or repair systems.

## False positives, safety and limitations

The `/health` case demonstrates one intentionally designed false signal that a separate validation rejected. It does **not** establish a zero false-positive rate across applications. The recorded safety checks are deterministic unit-style demonstrations, not full enterprise penetration tests. This prototype uses a single model, two local environments, and a small curated template catalog. The API-based model also requires appropriate data-handling review before any enterprise use.

## Conclusion

**Proceed to a limited pilot, not a product rollout.** NucleiPilot demonstrates a controlled, explainable decision loop. The next question is whether the LLM makes better decisions than tuned rules on diverse, authorized systems **after accounting for time, cost, errors and security oversight**. If it does not, retain rules for selection and consider the LLM only for approved analyst-facing explanations.

**Evidence:** [`../results/final/summary.md`](../results/final/summary.md) (E1–E3), [`../results/final/comparison.csv`](../results/final/comparison.csv), [`../results/final/grafana_demo.json`](../results/final/grafana_demo.json) (E4), [`../results/final/safety_checks.md`](../results/final/safety_checks.md) (E5).
