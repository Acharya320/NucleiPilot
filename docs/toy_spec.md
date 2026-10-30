# Toy Target Spec — the scaled-up sandbox

*The measurement bench for NucleiPilot. One small web app on `127.0.0.1` with several endpoints, a
known answer key, and — on purpose — a case where the **most business-critical** endpoint does **not**
carry the **highest technical severity**. Everything here is read-only and localhost-only.*

> Read `poc_plan.md` first. This document fills in Section 7 of that plan: it is the single design
> choice the whole experiment depends on.

---

## 1. The idea in one line

One app, several components. Each component has its **own business importance** (set per endpoint, not
for the whole app). Each planted issue has a **weak signal (indicator)** and a **specific confirmation
(validation)**. A match on an indicator is *not* a finding — only the validation's **content signature**
confirms it. A tight budget forces the agent to choose *which* issue is worth confirming.

---

## 2. The app and its components

A toy "payments company" app. Five endpoints, each with a business-importance label:

| Endpoint | Business importance | Why it matters to the business |
|---|---|---|
| `/payments` | **Critical** | Handles cardholder / transaction data. |
| `/account`  | **High**     | Holds customer personal data (PII). |
| `/docs`     | **Low**      | Public product documentation. |
| `/health`   | **Low**      | Ops/monitoring probe. |
| `/home`     | **Low**      | Public landing page. |

Business importance comes from configuration (the asset registry), **not** from the scan. The scanner
never guesses how much an endpoint matters — a human sets that once.

---

## 3. The planted issues (sandbox ground truth / answer key)

Three real issues, one benign trap, one clean endpoint. Every signature below is plain text in a
response **header** or **body**, or a **status code** — all matchable by a normal Nuclei template, all
GET-only and non-destructive.

| ID | Endpoint | Issue | Indicator (weak signal) | Validation **content signature** (what confirms it) | Tech severity | Business | Real? |
|---|---|---|---|---|---|---|---|
| **ISSUE-ADMIN** | `/payments` | Unauthenticated admin/config exposure | `GET /payments/` body shows an `Admin Console` banner | `GET /payments/admin/config.json` → `200` **and** body contains `authentication` and `disabled` | **Medium** | **Critical** | ✅ yes |
| **ISSUE-DEBUG** | `/docs` | Debug interface leaks internals | response header `X-Debug-Mode: enabled` | `GET /docs/debug/vars` → `200` **and** body contains `"stacktrace"` and the path `/srv/app/internal` | **High** | **Low** | ✅ yes |
| **ISSUE-PII** | `/account` | Verbose-error info disclosure | error page body names the framework (`Jinja2`) | `GET /account/export?id=../` → body contains `Traceback (most recent call last)` and `TOY_SECRET_KEY=planted-marker` | **Medium** | **High** | ✅ yes |
| **TRAP-DEBUG** | `/health` | Debug flag set, but **no** interface (benign) | response header `X-Debug-Mode: enabled` — **the same signal as ISSUE-DEBUG** | `GET /health/debug/vars` → `404`, body has **no** `stacktrace` signature | — | Low | ❌ no (false-positive trap) |
| **(clean)** | `/home` | Nothing wrong | no indicator fires | — | — | Low | ❌ no (no planted issue) |

**The key trick — the trap shares its signal with a real issue.** `/health` and `/docs` both send
`X-Debug-Mode: enabled`. From the *indicator alone*, no method — rule or LLM — can tell the real debug
leak from the harmless flag. Only the **validation content signature** (`stacktrace` + internal path)
separates them. This is the whole point of "model proposes, code authorizes": a fired template is a
hint, not a verdict.

---

## 4. The divergence (why this toy can test prioritization)

Look at the two highlighted rows:

- `/payments` — **Critical** business, but only **Medium** severity.
- `/docs` — **Low** business, but **High** severity.

So the business-critical issue is **not** the highest-severity issue. This is deliberate. If the most
important issue were always also the highest severity, every method would pick the same thing and we
would learn nothing. The divergence is what separates a **severity-only** strategy from a
**business-aware** one.

---

## 5. The budget model (precise)

All methods first run the **same** approved indicator-discovery stage. Then:

- **Indicator checks cost zero *validation-budget units* — but not zero HTTP requests or time.** They
  still hit the network and take wall-clock seconds, and we **measure** that. "Cost 0" is only about the
  validation budget.
- **Each validation template costs one budget unit.** Validations are the expensive, careful
  confirmations.
- **Budget = 2 validation units per target.** At most **1** validation is chosen in the first round
  (`budget − 1`); the second slot is **reserved** for a possible evidence-informed follow-up. This stops
  the agent from spending everything blindly up front.

**What we log for every run:** templates executed, validation-budget consumed, elapsed seconds, HTTP
requests (only when actually measured — otherwise omitted, never guessed), per-finding status, chosen
template IDs, policy rejections, and LLM input/output token counts where available.

---

## 6. The comparison — four methods, a fair fight

We run four methods on the **same** target, catalog, discovery matches, and budget. Beating a weak
baseline proves nothing, so we include a **strong non-LLM baseline (B2)**.

| Method | Selection rule | Budget | Role |
|---|---|---|---|
| **A · Fixed (reference)** | Run **all** reviewed validations | no cap | Full-set ceiling: the answer key and the "most work" number. Not a same-budget competitor. |
| **B1 · Severity-only rules** | Order candidates by technical severity, with a documented tie-break | 2 | Conventional priority baseline. |
| **B2 · Context-aware rules** | Order by configured business importance, then severity, with a documented tie-break | 2 | **The strong non-LLM baseline — the real bar to clear.** A few lines of Python. |
| **C · NucleiPilot (LLM)** | Propose validations from structured context + evidence + budget; Python enforces every choice | 2 | Tests whether the LLM adds judgment **beyond the rules**. |

All of B1/B2/C get the same fired indicators and the same 2-unit budget, with the same reserve rule. Use
a **stable tie-break** (e.g. issue ID alphabetical) so the rule results are not secretly engineered to
hit — or avoid — the trap.

> **The actual recorded outcome** (`results/experiment/summary.md`, generated by the harness): under
> budget 2, **B1** chose the High-severity debug validations and could not tell `/docs` from the
> `/health` trap — so it **missed** the business-critical `/payments` and `/account`. **B2** and **C**
> both chose `/payments` + `/account`. **C tied B2** — identical choice, stable across 3 runs. As
> promised, we say it plainly: on this small toy the LLM shows **no prioritization advantage over the
> context-aware rule**; the win is the governed, evidence-driven loop, not the model itself (see §7).

---

## 7. What this toy proves — and where the agent's value really sits

Be honest, but do **not** undervalue the agent. Its worth is a **stack of four things**, and only one of
them is the "the LLM out-picks a rule" claim that this toy cannot settle:

1. **Governance — "model proposes, code authorizes."** A flexible proposer (today an LLM) drives a real
   scanner while code enforces scope, allowlist, and budget and logs every step. For a regulated buyer
   this *is* the product. Fully demonstrable here (E5, traces).
2. **Evidence discipline.** Indicator→validation with content-signature verdicts turns raw matches into
   trustworthy findings and rejects false positives *on evidence*. Demonstrable here (E3).
3. **Budget-aware prioritization.** A real capability. On this small, fully-labeled toy a context-aware
   rule (B2) matches it — **as expected**. That tie is a property of the toy's size, not a weakness of
   the agent (see below).
4. **Generalization without hand-written rules.** The LLM extends 1–3 to targets, technologies, and
   evidence patterns nobody pre-coded. This is where rules get expensive and the agent earns its cost.
   Demonstrable as a *taste* here (the Grafana version→CVE reasoning used **zero CVE-specific decision
   code** — E4/E6); its *reliability at scale* is the 90-day pilot's job (`build_decision.md`).

**The point that keeps us honest without underselling:** *a rule like B2 is the LLM's decision policy,
frozen into code.* You can only write that rule once you already know the right policy. On a 5-endpoint
labeled board the policy is trivial to know and freeze, so B2 ties C — of course it does. The agent's
value is producing a good policy on the inputs you *haven't* enumerated and *can't* cheaply pre-write:
new assets, new CVEs, messy unlabeled context. AMEX's real world is thousands of assets and a constant
stream of new templates — exactly the regime where maintaining rules by hand breaks down and a governed,
generalizing agent pays off.

So the honest headline is **not** "the LLM wins" and **not** "the agent adds nothing." It is: *a bounded,
auditable agent that makes evidence-driven, context-aware decisions and generalizes to new targets
without new rule code; on a toy this small its per-decision quality ties a hand-tuned rule, and proving a
reliability edge on messy real targets is the pilot's job.*

---

## 8. The checks that make the result trustworthy

1. **Repeat each LLM decision ≥ 3 times** (settings fixed) and confirm it is stable.
2. **Context-flip (E2):** swap the importance labels of `/payments` and `/docs`, change **nothing** in
   the HTTP responses, and show B2 and C both shift to the debug issue. This proves the choice tracks
   business context, not a fixed favourite.
3. **Trap verification (E3):** a small separate run that **actually validates both** `/docs` and
   `/health`. `/docs/debug/vars` matches its signature → `CONFIRMED`; `/health/debug/vars` returns 404
   with no signature → `NOT_CONFIRMED`. This is what proves the FP is *rejected on evidence* — skipping
   `/health` in the budget run does **not** prove that.
4. **Evidence-aware second decision (E1 follow-up):** the LLM's second call receives a **small
   structured summary of the first validation's actual result** (see below), not raw HTML — so the
   follow-up is informed by evidence. We log the first result, the second proposal + reason, the policy
   verdict, and the final scan. We do **not** claim "adaptive improvement" just because the LLM was
   called twice, and we do **not** invent a changed choice when the same next check is still rational.

The second-call input is a tiny JSON object, e.g.:

```json
{
  "first_check": "toy-admin-validation",
  "first_result": "CONFIRMED",
  "evidence_summary": "configured auth-disabled marker matched",
  "remaining_candidates": ["toy-pii-validation", "toy-docs-debug-validation", "toy-health-debug-validation"],
  "remaining_validation_budget": 1,
  "business_context": {"/account": "High", "/docs": "Low", "/health": "Low"}
}
```

Sending this summary instead of raw page content is also a **security** choice: the model never ingests
raw target output, which shrinks the prompt-injection and data-egress surface.

---

## 9. How the verdict is decided (in code, not by the model)

Code assigns each finding exactly one status from the saved Nuclei evidence and the per-finding rules.
Two things are kept separate: the **sandbox ground truth** (what the author planted) and the
**scanner-observed status** (what the executed checks actually support).

| Status | Code-controlled definition | Example |
|---|---|---|
| `CONFIRMED` | A completed, finding-specific validation satisfies **all** required content/status predicates | `/docs/debug/vars`: 200 **and** `stacktrace` **and** internal-path marker |
| `NOT_CONFIRMED` | The validation completed, but the required evidence was **absent** (does not prove the issue is impossible) | `/health/debug/vars`: 404, no `stacktrace` marker → the benign trap |
| `UNVERIFIED` | An indicator matched, but no validation ran (budget exhausted) | `/account` indicator skipped under budget |
| `NO_INDICATOR` | No indicator matched **among the checks actually performed** (not a claim the endpoint is secure) | `/home` in this limited test |
| `TEST_ERROR` | The scan/HTTP validation failed or produced unusable evidence — **never** counted as a negative | timeout, malformed output, tool error |

The LLM **may not assign or overwrite** these labels. It only explains relevance and business priority.

---

## 10. Minimal experiment matrix (no new endpoints or agents)

| # | Setup | What it shows | Success criterion |
|---|---|---|---|
| **E1** | Five-endpoint toy, budget 2 | A vs B1 vs B2 vs C, with the actual chosen templates + confirmed issues | Reproducible, fair; **no assumed LLM win** |
| **E2** | Swap `/payments` ↔ `/docs` importance; responses unchanged | Repeat B2 and C | Choices/reasons track context; report both |
| **E3** | `/docs` vs `/health`, both validated | Identical indicator → different validation results | Evidence-based `CONFIRMED` vs `NOT_CONFIRMED` |
| **E4** | Isolated local Grafana 8.3.0, non-destructive templates | Nuclei JSON → guard → status → report | Real end-to-end trace; no unsupported Grafana claims |
| **E5** | Local config only | Invalid template, off-scope target, over-budget proposal, malformed LLM JSON | Each blocked/rejected; **zero** off-scope executions |
| **E6** | The already-built Grafana case | Decision-code each path needs: LLM reasons version→CVE from the catalog (**0 CVE-specific lines**) vs an equal rule (explicit version-range logic per CVE pair) | An honest *taste* of generalization / rule-maintenance cost — **not** a scale claim |

Run the LLM cases ≥ 3× with fixed settings. Keep the full Nuclei output, the model's proposed IDs +
reasons, and the deterministic verifier's final decision for every run.

---

## 11. What we build for this (reusing v1)

The v1 sandbox already serves ground-truth profiles and the indicator/validation + benign-trap pattern,
so we **extend** it rather than start over:

- **Sandbox** — serve the five endpoints with their exact headers, bodies, and signatures (one small
  localhost-only Python handler — the scope guard already covers it).
- **Templates** — grow from 4 to the indicator+validation pairs for ADMIN, DEBUG, PII, plus the shared
  debug indicator used by the trap. Each **validation** matches on its **content signature**, never on a
  bare status code alone.
- **Asset registry** — new small config: the five endpoints, each with its business-importance label and
  the budget. A future authorized target = one more entry.
- **Catalog** — the templates above, tagged indicator/validation, with severity and cost (0 or 1).
- **Baseline B2** — a few lines of Python (importance → severity → stable tie-break), kept outside the
  LLM so it is a genuine independent baseline.
- **Two-stage LLM** — first proposal, then a second proposal that receives the structured evidence
  summary from §8; both pass through the same policy guard.

Everything else (policy gate, scanner runner, evidence verifier, trace log) is reused from v1 and only
adapted to read the per-endpoint business context and to emit the §9 status labels.
