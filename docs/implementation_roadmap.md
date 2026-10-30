# Implementation Roadmap — NucleiPilot POC

*A stepwise checklist for building the scaled-up POC. We tick each box only when the step is actually
done and checked. Read with `poc_plan.md` (the plan) and `toy_spec.md` (the toy design).*

**Two standing rules for this build:**
1. **Evolve in place, don't fork.** The POC extends the existing `nucleipilot/` code; the old shape
   lives in git history. We do **not** keep parallel "v1" copies.
2. **The examiner must be able to run everything themselves.** Every step that produces a result must
   be reproducible by a single documented command. The README (Phase 7) is a first-class deliverable,
   not an afterthought.

Legend: `[x]` done · `[~]` in progress · `[ ]` not started. *(reuse)* = adapt existing v1 code.

---

## Phase 0 — Plan & specs (design, no code)
- [x] Lock the 2-day POC plan → `docs/poc_plan.md`
- [x] Clean up docs so there is no "v1 vs v2" confusion (renamed to `poc_plan.md`; nothing deleted)
- [x] Design the scaled-up toy with the severity-vs-business divergence → `docs/toy_spec.md`
- [x] **You review `toy_spec.md` and approve** (approved 2026-10-30 — "Ok lets go")

## Phase 1 — Scaled toy sandbox + templates  ✅ (2026-10-30)
- [x] New module `nucleipilot/toyapp.py` serves the 5 endpoints (`/payments`, `/account`, `/docs`, `/health`, `/home`) with their exact headers/bodies/signatures — all present at once (v1 `sandbox.py` left intact, retired in Phase 7)
- [x] Confirmed the **trap** (`/health`) sends the *same* `X-Debug-Mode: enabled` signal as `/docs` — the debug indicator fires on both (verified with real Nuclei)
- [x] Wrote 7 templates: `toy-admin-{indicator,validation}`, `toy-debug-indicator` (shared), `toy-docs-debug-validation`, `toy-health-debug-validation` (trap), `toy-pii-{indicator,validation}`
- [x] Each **validation** matches on its **content signature** (body words), not a bare status code; severities give the divergence (admin=medium, docs-debug=high, pii=medium)
- [x] Answer key recorded machine-readable: `config/toy_answer_key.json` (mirrors `toyapp.ANSWER_KEY`)
- [x] Smoke test `scripts/smoke_toyapp.py` PASSED (server signatures); real-Nuclei check PASSED (all 6 match, trap correctly does NOT match)

## Phase 2 — Core engine (the "code authorizes" back-end) *(mostly reuse)*
- [x] New **asset registry** config: `config/asset_registry.json` + `nucleipilot/registry.py` (5 endpoints, per-endpoint business importance, budget=2)
- [x] New **catalog**: `config/catalog.json` + `policy.load_catalog()`/`toy_catalog()` (7 `toy-*` templates tagged indicator/validation, severity, cost 0/1, endpoint; shared debug indicator resolves per-endpoint)
- [x] `policy.py` made **catalog-aware** without breaking v1 (`validate_choice(..., catalog=None)` defaults to the v1 ALLOWLIST); 9 consistency tests green, all 23 v1 tests still pass
- [x] **Context profiler** (`nucleipilot/profiler.py`) — Python-only, no LLM, no raw HTML; `discover()` runs indicators, `build_profile()` assembles per-endpoint context (business importance + budget + fired indicators + candidate validations). Shared debug indicator fans out to /docs + /health. Unit-tested + live-verified with real Nuclei.
- [x] *(reuse)* **Policy gate** (`policy.py`) — allowlist + eligibility now catalog-driven (scope guard = `scanner.assert_in_scope`, localhost-only)
- [x] *(reuse)* **Scanner runner** (`scanner.py`) — confirmed working against the toy in Phase 1 (fixed command line, `-ni`, localhost-only, JSON out)
- [x] **Evidence verifier** (`nucleipilot/verifier.py`) — `verdict()` sets CONFIRMED / NOT_CONFIRMED / UNVERIFIED / NO_INDICATOR / TEST_ERROR in code (error checked before match, so a failed scan is never a false negative); `make_finding()` builds a Finding. LLM never assigns labels. Live-verified: /payments→CONFIRMED, /health trap→NOT_CONFIRMED.
- [x] **Trace log + stop switch** — in `nucleipilot/engine.py` (full per-step trace: decision/policy/action/reassess; `should_stop` kill switch)

## Phase 3 — Planners (the decision front-end)  ✅ (2026-10-30)
All four planners in `nucleipilot/planners.py`; the v2 workflow in `nucleipilot/engine.py`.
52 unit tests pass; live A/B1/B2/C run against the toy with real Nuclei + real LLM.
- [x] **Fixed** planner (A) — runs the full validation set (reference ceiling); live A found all 3 real issues + rejected the trap
- [x] **B1 · Severity-only rule** — severity-ordered; live B1 confirmed /docs and wasted a slot on the /health trap, missing both business-critical issues
- [x] **B2 · Context-aware rule** — business importance → severity → stable tie-break; a few lines of Python; live B2 confirmed /payments + /account
- [x] **C · LLM** planner — picks from the catalog using per-endpoint business context + budget; **live C tied B2** (chose /payments + /account) — the honest headline, not an "LLM wins" claim
- [x] **Two-stage / evidence-aware:** `engine.run` decides one validation per round and passes the structured evidence-so-far (validation, endpoint, status) to later LLM decisions — not raw HTML
- [x] Budget behaviour: one validation per round for ≤ `budget` rounds, so the first commit is ≤ `budget − 1` and later rounds are reactive (reserve rule); live budget_used=2
- [x] All planners return only catalog template IDs; a hallucinated id is rejected by the gate (tested: `test_hallucinated_id_is_blocked_by_the_gate`)

## Phase 4 — Experiment harness + metrics  ✅ (2026-10-30)
One reproducible script: `scripts/run_experiment_v2.py` (starts the toy, profiles once for a fair shared
discovery, runs everything, writes a **data-driven** summary). Outputs in `results/experiment/`
(traces/, comparison.csv, summary.md, e3_trap.json) — kept separate from the v1 `results/final/` until
Phase 7 reconciles them. *(E4 Grafana = Phase 5; E5 safety = Phase 6.)*
- [x] **E1** — A / B1 / B2 / C on the same target, catalog, shared discovery, budget 2. Live result: B1 misses both business-critical issues + hits the trap; B2 and C both confirm /payments + /account
- [x] Metrics logged per run: validation-budget units, validations run, policy rejections, decision-loop elapsed, chosen order, LLM tokens (in each trace's `raw.usage`); HTTP request counts deliberately NOT fabricated (honest — toy_spec §5)
- [x] **E2 · Context-flip** (swap `/docs`↔`/payments` importance, responses unchanged) → B2 and C both shift their first pick to `/docs`
- [x] **E3 · Trap verification** — validated BOTH `/docs` (CONFIRMED) and `/health` (NOT_CONFIRMED)
- [x] Repeated the LLM decision 3× — C stable (identical choices all 3 runs)
- [x] Saved all traces + comparison table; `summary.md` is generated from the actual runs and states the honest headline: **C ties B2** (no "LLM wins" claim)

## Phase 5 — Grafana generalization (real app, non-destructive) · E4  ✅ (2026-10-30)
Run through the **same `engine.py`** as the toy: Grafana is just another asset + catalog (`scripts/run_grafana.py`). Evidence: `results/experiment/grafana_demo.json`. 55 tests still pass.
- [x] *(reuse)* Local **Grafana 8.3.0** container, version pinned, isolated (script starts it if down; fingerprint via `/api/health`)
- [x] Planted a **harmless marker file** (`/tmp/np-marker.txt`); the agent retrieved that exact marker → CONFIRMED (primary, read-only proof)
- [x] `/etc/passwd` read as the secondary proof via a **local template implementing the real CVE-2021-43798 traversal** (`grafana-cve-2021-43798-passwd.yaml`) → CONFIRMED. *(Note: this is our own template, not ProjectDiscovery's official one; the v1 run in `results/final/vulhub_grafana_demo.json` used the official community template — kept as corroboration.)*
- [x] Saved evidence JSON; reported only what we observed (no answer key assumed for Grafana)
- [x] **E6** — `results/experiment/e6_generalization_note.md`: the LLM reasoned version→CVE from catalog descriptions with **0 CVE-specific decision code** (picked CVE-2021-43798 over the 2020-13379 distractor); a rule needs explicit per-CVE version-range logic. Honest taste of maintenance cost, not a scale claim.

## Phase 6 — Safety checks (show them failing safe) · E5  ✅ (2026-10-30)
`scripts/safety_checks_v2.py` (deterministic, no Nuclei/API) → `results/experiment/safety_checks.md`; 3 matching unit tests in `tests/test_engine.py`. All PASS (55 tests total).
- [x] Out-of-scope target → rejected before any scan (scope guard + engine refuses the asset)
- [x] Template not on the allowlist → blocked by the gate (rejection logged, nothing executed)
- [x] Malformed JSON from the LLM → safe stop (0 validations run, 0 confirmed)
- [x] Over-budget → prevented in code (4 eligible, budget 2, exactly 2 run; rest stay UNVERIFIED)

## Phase 7 — Results, docs & the examiner-runnable README
- [ ] Regenerate `results/final/` from the scaled toy (replaces the old 2-issue numbers, **in place**)
- [ ] Write a short results note (what we found, honestly)
- [ ] Final architecture figure matching the built code
- [ ] **README the examiner can follow start-to-finish:**
  - [ ] Prerequisites (Python version, venv, Nuclei v3 path, OpenRouter key for the LLM planner only)
  - [ ] One-command setup (create venv, install requirements)
  - [ ] Exact commands to: run unit tests · start the toy · run A/B/C · run safety checks · run Grafana demo
  - [ ] What output each command produces and **where** it lands (`results/final/…`)
  - [ ] A note that all testing is localhost-only and read-only
  - [ ] Index linking every deliverable (plan, toy spec, landscape, architecture, roadmap, decision, deck)
- [ ] Update `README.md`'s "How it works" + reproduce sections to the built flow (**in place**)

## Phase 8 — Submission
- [ ] ~5-minute demo video (you record; I write the script)
- [ ] Final check: `.env` gitignored, no secrets, PDFs stay outside the repo
- [ ] GitHub push (visibility, repo name, reviewer handles confirmed with you first)

---

## Deliverables the examiner receives (the "many artifacts")
Runnable repo · toy sandbox + templates · asset registry + catalog configs · agent/policy/scanner code ·
tests · `results/final/` (raw JSON + comparison table + traces) · `docs/` (plan, toy spec, landscape &
capability map, enterprise architecture, roadmap, build decision) · README index · exec deck · demo video.
