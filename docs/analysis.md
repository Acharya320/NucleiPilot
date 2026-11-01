# Part 2 — POC Evaluation (One Page)

**Goal.** Can an LLM help select useful follow-up checks around Nuclei, safely and under a limited scan budget? Nuclei remains the scanner; NucleiPilot adds planning, an independent permission check, and evidence-based finding status.

## What worked

- **Business-aware decisions:** With two validation slots, both the LLM planner (**C**) and a context-aware rule (**B2**) confirmed the important `/payments` and `/account` issues. The severity-only rule (**B1**) selected `/docs` and a benign `/health` signal instead.
- **The decision responds to context:** When business importance was switched, B2 and C both prioritized `/docs` first (E2). This shows sensitivity to the supplied context, not an advantage over rules.
- **Evidence matters:** In the toy's false-positive check (part of E1), the `/docs` finding was confirmed by a content check; the similar-looking `/health` signal was **not confirmed**.
- **A real-app case where the LLM clearly beats rules (E3):** On a **live Grafana 8.3.0** container, from the grafana-tagged CVEs a `-tags grafana` rule gathers out of the real **14,104-template corpus**, the LLM selected the one applicable to 8.3.0 — **F1 1.00** (precision/recall 1.00, stable over three runs) vs a tag rule **0.15** and a naive version parser **0.29** — then the **same engine ran that real community template live and the verdict was CONFIRMED** (read-only file read). Affected versions are inconsistent free-text, so this is the task where reading beats keyword/parse rules. One product/version — a demonstration, not broad generalization.
- **Controlled execution:** Four deterministic tests passed for out-of-scope targets, unknown template IDs, malformed model output, and validation-budget enforcement (E4).

## What did not work or is unproven

On the toy's **prioritization** task, the LLM **did not outperform** the stronger non-LLM rule: both confirmed the same important findings across three LLM runs. The LLM varied its selection order. (The LLM's clear win is on a *different* task — **curation over the messy real corpus, E3 above** — not on small-toy prioritization.) We did not measure improvement in Nuclei's detection ability, real-world false-positive rates, or operational cost savings. The fixed exhaustive reference used **four** validation checks; B1/B2/C used **two**, so the fixed run is a coverage reference rather than a same-budget comparator. E3 is one product/version — a measured demonstration, not a breadth guarantee.

## Where people are still required

A human provides written authorization, approved targets and templates, per-asset business importance, and the permitted budget. A human also defines the toy application's expected results, reviews findings, and decides on any remediation or intrusive investigation. The POC does not autonomously exploit or repair systems.

## False positives, safety and limitations

The `/health` case demonstrates one intentionally designed false signal that a separate validation rejected. It does **not** establish a zero false-positive rate across applications. The recorded safety checks are deterministic unit-style demonstrations, not full enterprise penetration tests. This prototype uses a single model, two local environments, and a small curated template catalog. The API-based model also requires appropriate data-handling review before any enterprise use.

## Conclusion

**Proceed to a limited pilot, not a product rollout.** NucleiPilot demonstrates a controlled, explainable decision loop. The honest picture is two-sided: on a small, clean task the LLM only **ties** tuned rules (so it is not needed there), but on **Grafana + the large, messy real corpus** it **clearly wins** (E3) — selecting the version-applicable check is a reading problem rules cannot do. The agent's value therefore **scales with the size and messiness of the template space**. The pilot's job is to measure whether that holds across diverse, authorized systems **after accounting for time, cost, errors and security oversight**.

**Evidence:** [`../results/final/summary.md`](../results/final/summary.md) (E1–E2), [`../results/final/comparison.csv`](../results/final/comparison.csv), [`../results/final/safety_checks.md`](../results/final/safety_checks.md) (E4), [`../results/final/e3_grafana_summary.md`](../results/final/e3_grafana_summary.md) + [`e3_grafana_note.md`](../results/final/e3_grafana_note.md) (E3).
