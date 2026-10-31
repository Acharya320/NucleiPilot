# Part 2 — Recorded Test Evidence

This folder contains **saved outputs** from the local toy app and Grafana 8.3.0. The results support a small proof of concept; they are not a real-world performance benchmark.

## Start with this comparison

The toy app has three known issues and a benign debug signal. All methods observe the same preliminary signals; they differ in which validations they choose.

| Method | Budget used | Validations selected | Verified findings |
|---|---:|---|---|
| A: exhaustive **reference** | **4** | docs, health, admin, PII | `/docs`, `/payments`, `/account` |
| B1: severity-first rule | **2** | docs, health | `/docs` |
| B2: context-aware rule | **2** | admin, PII | `/payments`, `/account` |
| C: LLM | **2** | admin + PII (order varied over 3 runs) | `/payments`, `/account` each time |

**Interpretation:** C ties B2. A has a bigger budget and is a coverage ceiling, **not** an equally budgeted comparator. The severity rule selected low-business-priority checks, but the separate code verifier still correctly rejected the benign `/health` signal.

## Other checks

- **E2 — Business-context switch:** B2 and C chose `/docs` first after it was designated business-critical; no HTTP response or vulnerability changed.
- **E3 — Designed false-positive example:** `/docs` passed validation; `/health` did not. It is only one controlled case.
- **E4 — Grafana:** the LLM chose an applicable CVE-2021-43798 check on local Grafana 8.3.0; the saved output reports successful file-read evidence. One additional target does not prove broad transfer.
- **E5 — Safety:** four deterministic checks passed. These did not involve a live LLM or scanner.
- **E6 — Maintenance illustration:** the same decision engine accepted a new asset and catalog, but lower maintenance cost versus a generic rules engine was **not measured**.
- **E7 — Corpus curation (the LLM's clear win):** choosing the Grafana CVE applicable to 8.3.0 from the real 14,104-template library, the LLM scored **F1 1.00** vs a tag rule **0.15** and a naive version parser **0.29** (stable over 3 runs). The affected-version prose is not machine-readable, so reading beats keyword/parse rules here. This is the complement to the toy's honest tie — one task, on messy real data, where the LLM is clearly needed.

## Where to look

| File | Purpose |
|---|---|
| `summary.md` | E1–E3 results, derived from the recorded runs |
| `comparison.csv` | Per-run choices, findings, budgets |
| `traces/e1_C_run0.json` | Example of LLM proposal, authorization, scan and verdict |
| `e3_trap.json` | The two separate debug validations |
| `grafana_demo.json` | Grafana candidate selection and confirmation summary |
| `vulhub_grafana_demo.json` | Additional Grafana run using an official Nuclei template, with trace |
| `safety_checks.md` | Four recorded safety checks |
| `e6_generalization_note.md` | Discussion of adding a new target without engine changes |
| `curation_summary.md` | E7 scores: tag rule vs version parser vs LLM on the real corpus |
| `curation_results.json` | E7 per-method selections and the LLM's per-CVE reasons |
| `e7_curation_note.md` | E7 analysis: the measured case where the LLM clearly beats rules |

**Limitations:** toy ground truth is deliberately simple; one model is tested; LLM output order varies; the Grafana `grafana_demo.json` stores a summary rather than the entire engine trace. See [`../../docs/analysis.md`](../../docs/analysis.md) for the one-page evaluation and [`../../README.md`](../../README.md) for reproducibility commands.
