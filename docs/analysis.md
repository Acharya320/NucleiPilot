# Part 2 — POC Evaluation (One Page)

**Goal.** Can an LLM help select useful follow-up checks around Nuclei, safely and under a limited scan budget? Nuclei remains the scanner; NucleiPilot adds planning, an independent permission check, and evidence-based finding status.

## What worked

- **Business-aware decisions:** With two validation slots, both the LLM planner (**C**) and a context-aware rule (**B2**) confirmed the important `/payments` and `/account` issues. The severity-only rule (**B1**) selected `/docs` and a benign `/health` signal instead.
- **The decision responds to context:** When business importance was switched, B2 and C both prioritized `/docs` first (E2). This shows sensitivity to the supplied context, not an advantage over rules.
- **Evidence matters:** In a separate test (E3), the `/docs` finding was confirmed by a content check; the similar-looking `/health` signal was **not confirmed**.
- **Reuse on another application:** On a local Grafana 8.3.0 container, the LLM chose a relevant CVE-2021-43798 template from two catalog options. The saved run reports a successful read-only file check (E4). This demonstrates feasibility on one additional target, not broad generalization.
- **Controlled execution:** Four deterministic tests passed for out-of-scope targets, unknown template IDs, malformed model output, and validation-budget enforcement (E5).
- **A case where the LLM clearly beats rules (E7):** On the real 14,104-template corpus, selecting the Grafana CVE that actually applies to version 8.3.0 — where affected versions are inconsistent free-text prose — the LLM scored **F1 1.00** (precision/recall 1.00, stable over three runs) versus a tag rule **0.15** and a naive version parser **0.29**. This is the one task, on messy real data, where reading the templates beats keyword/parse rules.

## What did not work or is unproven

On the toy's **prioritization** task, the LLM **did not outperform** the stronger non-LLM rule: both confirmed the same important findings across three LLM runs. The LLM varied its selection order. (The LLM's clear win is on a *different* task — **curation** over the messy real corpus, E7 above — not on small-toy prioritization.) We did not measure improvement in Nuclei's detection ability, real-world false-positive rates, or operational cost savings. The fixed exhaustive reference used **four** validation checks; B1/B2/C used **two**, so the fixed run is a coverage reference rather than a same-budget comparator. E7 is one product/version — a measured demonstration, not a breadth guarantee.

## Where people are still required

A human provides written authorization, approved targets and templates, per-asset business importance, and the permitted budget. A human also defines the toy application's expected results, reviews findings, and decides on any remediation or intrusive investigation. The POC does not autonomously exploit or repair systems.

## False positives, safety and limitations

The `/health` case demonstrates one intentionally designed false signal that a separate validation rejected. It does **not** establish a zero false-positive rate across applications. The recorded safety checks are deterministic unit-style demonstrations, not full enterprise penetration tests. This prototype uses a single model, two local environments, and a small curated template catalog. The API-based model also requires appropriate data-handling review before any enterprise use.

## Conclusion

**Proceed to a limited pilot, not a product rollout.** NucleiPilot demonstrates a controlled, explainable decision loop. The honest picture is two-sided: on a small, clean task the LLM only **ties** tuned rules (so it is not needed there), but on **curation over the large, messy real corpus** it **clearly wins** (E7) — selecting the version-applicable check is a reading problem rules cannot do. The agent's value therefore **scales with the size and messiness of the template space**. The pilot's job is to measure whether that holds across diverse, authorized systems **after accounting for time, cost, errors and security oversight**.

**Evidence:** [`../results/final/summary.md`](../results/final/summary.md) (E1–E3), [`../results/final/comparison.csv`](../results/final/comparison.csv), [`../results/final/grafana_demo.json`](../results/final/grafana_demo.json) (E4), [`../results/final/safety_checks.md`](../results/final/safety_checks.md) (E5), [`../results/final/curation_summary.md`](../results/final/curation_summary.md) + [`e7_curation_note.md`](../results/final/e7_curation_note.md) (E7).
