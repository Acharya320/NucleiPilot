# NucleiPilot - Evidence-Guided Follow-Up Testing with Nuclei

**Agentic AI for Offensive Security - take-home PoC (Part 2: implementation)**

NucleiPilot is a small, **governed AI agent** - an agentic decision layer - on top of the open-source [Nuclei scanner](https://github.com/projectdiscovery/nuclei). After collecting initial signals, the agent selects **which approved check to run next** based on business importance, available evidence, and a limited testing budget. Nuclei performs the scan; deterministic Python code checks permissions and interprets the result.

**Operating rule: the language model proposes; code authorizes.** This is a controlled testing prototype, not a fully autonomous penetration-testing product.

## Part 2 deliverables - where to find each

A reviewer with a single link lands here. The assignment's Part-2 deliverables and exactly where each lives:

| Assignment deliverable | Where to find it |
|---|---|
| **1. Tool teardown** | [`docs/tool_teardown.md`](docs/tool_teardown.md) |
| **2. Implementation (working code)** | this repo: [`nucleipilot/`](nucleipilot/) (library) · [`scripts/`](scripts/) (entry points) · [`config/`](config/) + [`templates/`](templates/) (data) · [`tests/`](tests/) |
| **3. Documentation (README)** | this file - §1-§5 cover design, agent behavior, architecture, dependencies, setup, how to run, and known limitations |
| **4. ~5-minute demo video** | Shared privately in the submission document (not published on this public repo) |
| **5. Test results** | [`results/final/`](results/final/) + its [`README`](results/final/README.md) - comparison, traces (decisions/actions), E3 Grafana run, safety |
| **6. Analysis (1 page)** | [`docs/analysis.md`](docs/analysis.md) |
| **7. Executive deck (≤5 slides)** | [`presentation/NucleiPilot_Executive_Deck.pdf`](presentation/NucleiPilot_Executive_Deck.pdf) |

**Supporting design docs:** [`docs/poc_plan.md`](docs/poc_plan.md) (design + build plan) · [`docs/toy_spec.md`](docs/toy_spec.md) (toy spec + experiment matrix E1-E4) · [`docs/figures/poc_flow.png`](docs/figures/poc_flow.png) (the POC's internal decision-flow diagram - not to be confused with the production-stack architecture diagram in Part 3 of the written brief).

**Suggested reading order:** this README → [`docs/analysis.md`](docs/analysis.md) (the verdict) → [`results/final/README.md`](results/final/README.md) (the evidence) → then, for depth, `poc_plan.md` and `toy_spec.md`.

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

**Two decision points, one engine.** The pipeline makes two kinds of decision: **curation** - which templates are even *relevant/applicable* to a target (the hard part when the corpus is large) - and **prioritization** - which relevant check to run next under a budget. The **toy demo (E1-E2)** stresses *prioritization* (a tiny pre-curated catalog, a tight budget → the planners A/B1/B2/C); the **Grafana demo (E3)** stresses *curation* (the real ~14k corpus, one applicable CVE → tag-rule vs version-parser vs LLM). Both run through the **same** `profile → decide → authorize → scan → verify` engine; only the rule baseline each is compared against differs, because the decision being tested differs.

**Testing boundary:** the project records tests on a self-hosted five-endpoint toy app and a local Grafana 8.3.0 container. Both are deliberately controlled lab targets. The code restricts submitted target hostnames to localhost, but does **not** provide enterprise-grade network isolation or a full redirect/egress policy. Do not use it against production or third-party systems.

## 3. Evidence and results

The toy app presents three real issues and one deliberately misleading debug signal. `/payments` and `/account` have higher *business importance* than `/docs`, even though `/docs` has higher *technical severity*.

| Method | Validation budget | Results | Interpretation |
|---|---:|---|---|
| **A - exhaustive reference** | 4 | Confirms `/payments`, `/account`, `/docs`; excludes `/health` | Coverage ceiling; **not** a same-budget comparator |
| **B1 - severity rule** | 2 | Confirms `/docs`; checks benign `/health`; misses two important issues | Technical severity alone can misallocate this budget |
| **B2 - context rule** | 2 | Confirms `/payments` and `/account` | Strong non-LLM baseline |
| **C - LLM planner** | 2 | Same two findings in all 3 recorded runs | **Matches B2; does not beat it** |

**False-positive discipline (part of E1):** a weak debug signal appears at both `/docs` and `/health`; a focused check validates both - `/docs` is CONFIRMED, the look-alike `/health` is **NOT_CONFIRMED**. A fired template is a hint, not a verdict (`results/final/e1_trap.json`). This is a **separate** check, not proof that the budget-2 LLM run tested `/health`.

Other focused checks:

- **E2 - context change:** when `/docs` becomes the most business-important target, B2 and C both select its validation first.
- **E3 - Grafana on the real 14k corpus (the LLM's clear win):** against a **live** Grafana 8.3.0 container, from the 12 grafana-tagged CVEs a `-tags grafana` rule gathers out of the real ~14k-template corpus, the LLM selects the one applicable to 8.3.0 - **F1 1.00** vs a tag rule **0.15** and a naive version parser **0.29** (stable over 3 runs) - then the **same engine runs that real community template live and the code verdict is CONFIRMED** (file read). Affected versions are inconsistent free-text, so this is the task where reading beats keyword/parse rules. A read-only safety gate refuses intrusive picks. The corpus is **referenced, not bundled** (ProjectDiscovery nuclei-templates **v10.5.1**, public, ~89 MB); the committed fixture (`config/grafana_corpus.json`) reproduces the selection with no external files. See [`results/final/e3_grafana_note.md`](results/final/e3_grafana_note.md).
- **E4 - four deterministic safety tests:** scope rejection, unknown-template rejection, malformed-output stop, and budget enforcement passed without requiring an LLM or live scanner.

**Takeaway:** the main implementation result is an inspectable, bounded follow-up workflow. On the small toy, the LLM only **ties** a well-designed context rule (it is not needed there); but on **Grafana + the large, messy real corpus (E3)** it **clearly wins**. The agent's value scales with the size and messiness of the template space.

Open [`results/final/README.md`](results/final/README.md) for the evidence index, [`results/final/summary.md`](results/final/summary.md) for recorded comparisons, and [`docs/analysis.md`](docs/analysis.md) for the short evaluation.

## 4. How to run it

> Commands below are **Windows PowerShell**. On **macOS/Linux**, replace `py` with `python3` and `.\.venv\Scripts\python.exe` with `./.venv/bin/python`.

### One-time setup (both demos)

Requirements: **Python 3.10+** and **Nuclei v3** (tested v3.11.1) on `PATH` (or set `NUCLEIPILOT_NUCLEI_BIN`). From the repo root:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The LLM steps need an API key: copy `.env.example` to `.env` and fill in your key (keep `.env` out of Git and ZIPs). Prefer no file? Export `NUCLEIPILOT_API_BASE`, `NUCLEIPILOT_API_KEY`, and `NUCLEIPILOT_MODEL` as environment variables instead - real env vars take precedence over `.env`. Any **OpenAI-compatible** endpoint works (OpenRouter, OpenAI, Anthropic, or local Ollama - ready-made blocks in `.env.example`). Without a key, the LLM method is skipped automatically and the run says so.

### 4A - Toy demo (E1-E2, plus safety E4)

**Needs:** Python + Nuclei. API key *optional* (only method C uses it). **No Docker.**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests    # 37 logic + safety tests (offline)
.\.venv\Scripts\python.exe scripts\smoke_toyapp.py          # confirm the toy target serves its signatures
.\.venv\Scripts\python.exe scripts\run_experiment.py        # E1-E2: A / B1 / B2 / C under a tight budget (+ E1 trap)
.\.venv\Scripts\python.exe scripts\safety_checks.py         # E4: four fail-safe demonstrations
.\.venv\Scripts\python.exe scripts\scope_demo.py            # E4: live scope-guard demo (real engine)
```
Outputs → `results/reproduced/`: `summary.md`, `comparison.csv`, `traces/`, `e1_trap.json`, `safety_checks.md`.

### 4B - Grafana demo (E3, real 14k corpus + live container)

**Needs (in addition to the setup above):** **Docker running**, an **API key** in `.env` (E3's selection uses the LLM), and the **nuclei-templates corpus**.

```powershell
nuclei -update-templates                                    # fetch the ~14k corpus to ~/nuclei-templates (once)
.\.venv\Scripts\python.exe scripts\run_grafana.py           # E3: fingerprint -> curate -> select -> live scan -> verdict
docker rm -f np-grafana                                     # stop the lab container when done
```
`run_grafana.py` starts `grafana/grafana:8.3.0` bound to **`127.0.0.1` only**. If your corpus is not at `~/nuclei-templates`, add `--corpus "<path>"`. Outputs → `results/reproduced/`: `e3_grafana_summary.md`, `e3_grafana_run.json`. *(Optional - prove the candidate pool isn't hand-picked:* `.\.venv\Scripts\python.exe scripts\build_grafana_fixture.py --corpus "<path>"`*.)*

### Notes

Reproduction runs write to `results/reproduced/` so the committed reference in `results/final/` is never overwritten (regenerate the reference deliberately with `--out results/final`). View one decision's full trace: `.\.venv\Scripts\python.exe scripts\show_trace.py results\final\traces\e1_C_run0.json`.

## 5. Known limitations

One LLM model; small, controlled test data; three repeated LLM runs per toy scenario; no proven real-world accuracy or scaling advantage; and lab-level rather than enterprise-grade network restrictions. E3 is **one product / version** - a demonstration, not a breadth guarantee. A larger pilot should compare the LLM with tuned rules on diverse, authorized systems before committing to an AI decision layer.

None of this changes what is already demonstrated here: a governed agent that ties a tuned rule where rules already suffice, and clearly beats them - live, on a real CVE - exactly where the problem gets hard. That result is the case for the pilot. *(All Part-2 deliverables and their locations are mapped at the top of this README.)*

## License

[MIT](LICENSE) - the same license Nuclei itself uses.
