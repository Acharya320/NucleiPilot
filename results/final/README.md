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

**Interpretation:** C ties B2. A has a bigger budget and is a coverage ceiling, **not** an equally budgeted comparator. The severity rule selected low-business-priority checks, but the separate code verifier still correctly rejected the benign `/health` signal. A focused false-positive check (part of E1) validates **both** `/docs` and `/health` explicitly — `/docs` CONFIRMED, `/health` NOT_CONFIRMED (see `e1_trap.json`): a fired template is a hint, not a verdict. It is only one controlled case.

## Other checks

- **E2 — Business-context switch:** B2 and C chose `/docs` first after it was designated business-critical; no HTTP response or vulnerability changed.
- **E3 — Grafana on the real 14k corpus (the LLM's clear win):** from the 12 grafana-tagged CVEs a `-tags grafana` rule gathers out of the real ~14,104-template corpus, the LLM selects the one applicable to **live Grafana 8.3.0** — **F1 1.00** vs a tag rule **0.15** and a naive version parser **0.29** (stable over 3 runs) — then the **same engine runs that real community template live and the verdict is CONFIRMED** (file read). Affected versions are inconsistent free-text, so reading beats keyword/parse rules. A read-only gate refuses intrusive picks. Generalization here is **data, not code**. One product/version — a demonstration, not breadth.
- **E4 — Safety:** four deterministic checks passed. These did not involve a live LLM or scanner.

## Where to look

| File | Purpose |
|---|---|
| `summary.md` | E1–E2 results, derived from the recorded runs |
| `comparison.csv` | Per-run choices, findings, budgets |
| `traces/e1_C_run0.json` | Example of LLM proposal, authorization, scan and verdict |
| `e1_trap.json` | The two separate debug validations (E1 false-positive trap) |
| `safety_checks.md` | Four recorded safety checks (E4) |
| `e3_grafana_summary.md` | E3 scores (tag vs version vs LLM) + the live verdict |
| `e3_grafana_run.json` | E3 full record: selection + the live engine trace |
| `e3_grafana_note.md` | E3 analysis: the measured LLM win, generalization, and reproducing from the full corpus |

**Limitations:** toy ground truth is deliberately simple; one model is tested; LLM output order varies; E3 is one product/version (a demonstration, not breadth). See [`../../docs/analysis.md`](../../docs/analysis.md) for the one-page evaluation and [`../../README.md`](../../README.md) for reproducibility commands.
