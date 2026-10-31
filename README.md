# NucleiPilot — Evidence-Guided Follow-Up Testing with Nuclei

**Part 2 | ATOS / American Express take-home assignment**

NucleiPilot extends the open-source [Nuclei scanner](https://github.com/projectdiscovery/nuclei) with a small decision layer. After collecting initial signals, it selects **which approved check to run next** based on business importance, available evidence, and a limited testing budget. Nuclei performs the scan; deterministic Python code checks permissions and interprets the result.

**Operating rule: the model proposes; code authorizes.** This is a controlled testing prototype, not a fully autonomous penetration-testing product.

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
- **E4 — Grafana:** against a local 8.3.0 container, the LLM selected an applicable CVE-2021-43798 check from two catalog candidates; saved results report a successful, read-only file test. This is **one transfer example**, not measured performance across real deployments.
- **E5 — four deterministic safety tests:** scope rejection, unknown-template rejection, malformed-output stop, and budget enforcement passed without requiring an LLM or live scanner.

**Takeaway:** the main implementation result is an inspectable, bounded follow-up workflow. The evidence does **not** show an LLM advantage over a well-designed context rule on this small toy dataset.

Open [`results/final/README.md`](results/final/README.md) for the evidence index, [`results/final/summary.md`](results/final/summary.md) for recorded comparisons, and [`docs/analysis.md`](docs/analysis.md) for the short evaluation.

## 4. How to reproduce

**Requirements:** Python 3.10+, Nuclei v3 (tested with v3.11.1), an API key for the LLM planner only, and Docker for the Grafana demo. Install Nuclei separately and put it on `PATH` or set `NUCLEIPILOT_NUCLEI_BIN`. Keep any `.env` with real credentials **outside shared ZIP files and Git**.

From the repository root — **Windows (PowerShell):**

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe scripts\smoke_toyapp.py
.\.venv\Scripts\python.exe scripts\run_experiment.py
.\.venv\Scripts\python.exe scripts\safety_checks.py
```

**macOS / Linux (bash):**

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m unittest discover -s tests
./.venv/bin/python scripts/smoke_toyapp.py
./.venv/bin/python scripts/run_experiment.py
./.venv/bin/python scripts/safety_checks.py
```

For the LLM experiment, copy `.env.example` to `.env` locally and fill in the API settings. `scripts/run_grafana.py` additionally requires Docker; it binds the container to **`127.0.0.1` only**, so the lab Grafana is not exposed on the network. Shut down the lab container after the demonstration (`docker rm -f np-grafana`).

The deterministic tests can run without Nuclei or an LLM. The end-to-end experiments need the dependencies noted above; **without an API key, method C (the LLM planner) is skipped automatically** and the summary records that. Reproduction runs write to `results/reproduced/` by default, so the committed reference evidence in `results/final/` is never overwritten (regenerate the reference deliberately with `--out results/final`). Individual decisions can be displayed with `python scripts/show_trace.py results/final/traces/e1_C_run0.json`.

## 5. Deliverables and limits

- **Implementation:** `nucleipilot/`, `scripts/`, `config/`, `templates/`, `tests/`.
- **POC evidence:** `results/final/README.md`, `summary.md`, `comparison.csv`, `traces/`, `grafana_demo.json`, `safety_checks.md`.
- **One-page evaluation:** [`docs/analysis.md`](docs/analysis.md).
- **Tool overview:** [`docs/tool_teardown.md`](docs/tool_teardown.md).
- **Executive slides:** [`presentation/AXP_Executive_Deck.pptx`](presentation/AXP_Executive_Deck.pptx).
- **Demo video:** must be recorded and linked before submission.

**Limitations:** one LLM model, small controlled test data, three repeated LLM runs in E1, no proven real-world accuracy or scaling advantage, and lab-level rather than enterprise-grade network restrictions. A larger pilot should compare the LLM with tuned rules on real authorized systems before committing to an AI decision layer.
