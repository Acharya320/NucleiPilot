# NucleiPilot — Evidence-Guided Follow-Up Testing with Nuclei

**Part 2 | ATOS / American Express take-home assignment**

NucleiPilot extends the open-source [Nuclei scanner](https://github.com/projectdiscovery/nuclei) with a small decision layer. After collecting initial signals, it selects **which approved check to run next** based on business importance, available evidence, and a limited testing budget. Nuclei performs the scan; deterministic Python code checks permissions and interprets the result.

**Operating rule: the model proposes; code authorizes.** This is a controlled testing prototype, not a fully autonomous penetration-testing product.

## Repository map

| Path | What it is |
|---|---|
| `README.md` | this file — overview, architecture, how to run, results |
| `docs/analysis.md` | **1-page evaluation** — what worked, what didn't, limits |
| `docs/tool_teardown.md` | teardown of Nuclei (what we extend, and why the agentic layer earns its place) |
| `docs/poc_plan.md` | design rationale + 2-day build plan (embeds the decision-flow diagram) |
| `docs/toy_spec.md` | toy-app specification + the experiment matrix (E1–E5) |
| `docs/figures/poc_flow.png` | the decision-flow diagram |
| `nucleipilot/` | the library — `engine`, `planners`, `policy`, `scanner`, `verifier`, `profiler`, … |
| `scripts/` | runnable entry points — `run_experiment` (toy), `run_grafana` (E4), `safety_checks`, `scope_demo`, `show_trace`, `build_grafana_fixture` |
| `config/` + `templates/` | approved targets, the catalog/fixtures, and the Nuclei checks |
| `tests/` | automated tests (37) |
| `results/final/` | recorded evidence, with its own [`README.md`](results/final/README.md) index |
| `presentation/AXP_Executive_Deck.pptx` | the 5-slide executive deck |

**Suggested reading order for a reviewer:** this README → [`docs/analysis.md`](docs/analysis.md) (the verdict) → [`results/final/README.md`](results/final/README.md) (the evidence) → then, for depth, [`docs/poc_plan.md`](docs/poc_plan.md) and [`docs/toy_spec.md`](docs/toy_spec.md).

## 1. Why build it?

Nuclei already supports thousands of security checks and template filtering. The question is what to do **after an initial scan reveals several potential issues** but there is only enough time or budget to investigate some of them. Should we investigate the technically severe issue first, or one affecting a business-critical service?

NucleiPilot tests two capabilities:

1. **Evidence-based follow-up:** treat a preliminary signal as unverified until a separate check provides stronger evidence.
2. **Context-aware selection:** choose the next permitted validation using business importance and technical information, subject to a fixed budget.

## 2. What runs in the POC?

```text
Approved local target -> Nuclei indicator checks -> target profile
                                                 |
                                                 v
                                  Rule-based OR LLM planner
                                        proposes a template
                                                 |
                                                 v
                          Python guard: scope + catalog + budget
                                                 |
                                                 v
                               Nuclei validation -> code verdict
                                                 |
                                                 v
                                   Next decision or final trace
```

The components are in `nucleipilot/`: `profiler.py` (initial observations), `planners.py` (four planning methods), `policy.py` (allowed choices), `scanner.py` (Nuclei command execution), `verifier.py` (evidence status), and `engine.py` (the loop). The input assets and approved templates are in `config/` and `templates/`.

**Two decision points, one engine.** The pipeline makes two kinds of decision: **curation** — which templates are even *relevant/applicable* to a target (the hard part when the corpus is large) — and **prioritization** — which relevant check to run next under a budget. The **toy demo (E1–E3)** stresses *prioritization* (a tiny pre-curated catalog, a tight budget → the planners A/B1/B2/C); the **Grafana demo (E4)** stresses *curation* (the real ~14k corpus, one applicable CVE → tag-rule vs version-parser vs LLM). Both run through the **same** `profile → decide → authorize → scan → verify` engine; only the rule baseline each is compared against differs, because the decision being tested differs.

**Testing boundary:** the project records tests on a self-hosted five-endpoint toy app and a local Grafana 8.3.0 container. Both are deliberately controlled lab targets. The code restricts submitted target hostnames to localhost, but does **not** provide enterprise-grade network isolation or a full redirect/egress policy. Do not use it against production or third-party systems.

## 3. Evidence and results

The toy app presents three real issues and one deliberately misleading debug signal. `/payments` and `/account` have higher *business importance* than `/docs`, even though `/docs` has higher *technical severity*.

| Method | Validation budget | Results | Interpretation |
|---|---:|---|---|
| **A — exhaustive reference** | 4 | Confirms `/payments`, `/account`, `/docs`; excludes `/health` | Coverage ceiling; **not** a same-budget comparator |
| **B1 — severity rule** | 2 | Confirms `/docs`; checks benign `/health`; misses two important issues | Technical severity alone can misallocate this budget |
| **B2 — context rule** | 2 | Confirms `/payments` and `/account` | Strong non-LLM baseline |
| **C — LLM planner** | 2 | Same two findings in all 3 recorded runs | **Matches B2; does not beat it** |

Other focused checks:

- **E2 — context change:** when `/docs` becomes the most business-important target, B2 and C both select its validation first.
- **E3 — independent false-positive test:** a weak debug signal appears at `/docs` and `/health`. A targeted check confirms the `/docs` issue and does **not confirm** `/health`. This is a **separate** check, not proof that the budget-2 LLM run tested `/health`.
- **E4 — Grafana on the real 14k corpus (the LLM's clear win):** against a **live** Grafana 8.3.0 container, from the 12 grafana-tagged CVEs a `-tags grafana` rule gathers out of the real ~14k-template corpus, the LLM selects the one applicable to 8.3.0 — **F1 1.00** vs a tag rule **0.15** and a naive version parser **0.29** (stable over 3 runs) — then the **same engine runs that real community template live and the code verdict is CONFIRMED** (file read). Affected versions are inconsistent free-text, so this is the task where reading beats keyword/parse rules. A read-only safety gate refuses intrusive picks. The corpus is **referenced, not bundled** (ProjectDiscovery nuclei-templates **v10.5.1**, public, ~89 MB); the committed fixture (`config/grafana_corpus.json`) reproduces the selection with no external files. See [`results/final/e4_grafana_note.md`](results/final/e4_grafana_note.md).
- **E5 — four deterministic safety tests:** scope rejection, unknown-template rejection, malformed-output stop, and budget enforcement passed without requiring an LLM or live scanner.

**Takeaway:** the main implementation result is an inspectable, bounded follow-up workflow. On the small toy, the LLM only **ties** a well-designed context rule (it is not needed there); but on **Grafana + the large, messy real corpus (E4)** it **clearly wins**. The agent's value scales with the size and messiness of the template space.

Open [`results/final/README.md`](results/final/README.md) for the evidence index, [`results/final/summary.md`](results/final/summary.md) for recorded comparisons, and [`docs/analysis.md`](docs/analysis.md) for the short evaluation.

## 4. How to run it

> Commands below are **Windows PowerShell**. On **macOS/Linux**, replace `py` with `python3` and `.\.venv\Scripts\python.exe` with `./.venv/bin/python`.

### One-time setup (both demos)

Requirements: **Python 3.10+** and **Nuclei v3** (tested v3.11.1) on `PATH` (or set `NUCLEIPILOT_NUCLEI_BIN`). From the repo root:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The LLM steps need an API key: copy `.env.example` to `.env` and fill in your key (keep `.env` out of Git and ZIPs). Without a key, the LLM method is skipped automatically and the run says so.

### 4A — Toy demo (E1–E3, plus safety E5)

**Needs:** Python + Nuclei. API key *optional* (only method C uses it). **No Docker.**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests    # 37 logic + safety tests (offline)
.\.venv\Scripts\python.exe scripts\smoke_toyapp.py          # confirm the toy target serves its signatures
.\.venv\Scripts\python.exe scripts\run_experiment.py        # E1-E3: A / B1 / B2 / C under a tight budget
.\.venv\Scripts\python.exe scripts\safety_checks.py         # E5: four fail-safe demonstrations
.\.venv\Scripts\python.exe scripts\scope_demo.py            # E5: live scope-guard demo (real engine)
```
Outputs → `results/reproduced/`: `summary.md`, `comparison.csv`, `traces/`, `e3_trap.json`, `safety_checks.md`.

### 4B — Grafana demo (E4, real 14k corpus + live container)

**Needs (in addition to the setup above):** **Docker running**, an **API key** in `.env` (E4's selection uses the LLM), and the **nuclei-templates corpus**.

```powershell
nuclei -update-templates                                    # fetch the ~14k corpus to ~/nuclei-templates (once)
.\.venv\Scripts\python.exe scripts\run_grafana.py           # E4: fingerprint -> curate -> select -> live scan -> verdict
docker rm -f np-grafana                                     # stop the lab container when done
```
`run_grafana.py` starts `grafana/grafana:8.3.0` bound to **`127.0.0.1` only**. If your corpus is not at `~/nuclei-templates`, add `--corpus "<path>"`. Outputs → `results/reproduced/`: `e4_grafana_summary.md`, `e4_grafana_run.json`. *(Optional — prove the candidate pool isn't hand-picked:* `.\.venv\Scripts\python.exe scripts\build_grafana_fixture.py --corpus "<path>"`*.)*

### Notes

Reproduction runs write to `results/reproduced/` so the committed reference in `results/final/` is never overwritten (regenerate the reference deliberately with `--out results/final`). View one decision's full trace: `.\.venv\Scripts\python.exe scripts\show_trace.py results\final\traces\e1_C_run0.json`.

## 5. Deliverables and limits

- **Implementation:** `nucleipilot/`, `scripts/`, `config/`, `templates/`, `tests/`.
- **POC evidence:** `results/final/README.md`, `summary.md`, `comparison.csv`, `traces/` (E1–E3), `safety_checks.md` (E5), `e4_grafana_summary.md` + `e4_grafana_run.json` + `e4_grafana_note.md` (E4).
- **One-page evaluation:** [`docs/analysis.md`](docs/analysis.md).
- **Tool overview:** [`docs/tool_teardown.md`](docs/tool_teardown.md).
- **Executive slides:** [`presentation/AXP_Executive_Deck.pptx`](presentation/AXP_Executive_Deck.pptx).
- **Demo video:** must be recorded and linked before submission.

**Limitations:** one LLM model, small controlled test data, three repeated LLM runs in E1, no proven real-world accuracy or scaling advantage, and lab-level rather than enterprise-grade network restrictions. A larger pilot should compare the LLM with tuned rules on real authorized systems before committing to an AI decision layer.
