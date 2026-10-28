# From PoC to Production — a 2-Person, 90-Day Plan

*AMEX / Atos take-home, Part 4. A lightweight plan to take NucleiPilot from today's proof of
concept to a governed internal pilot with a **two-engineer** team. What ships first, the
riskiest unknown, and what would make us change course.*

---

## The team
- **Engineer A — Security / scanning.** Owns the Nuclei runner, template catalog, scope and
  safety controls, identity/logging integration. (Builds out the *data plane* + *gateway* from Part 3.)
- **Engineer B — Agent / evaluation.** Owns the planner, policy guard, trace store, and the
  evaluation harness. (Builds out the *control plane* + evidence from Parts 2–3.)

## What ships first (the MVP)
**Not** a broad autonomous platform. The first ship is the **narrowest thing that attacks the
riskiest unknown**: the context-aware **triage/follow-up layer running against *real* Nuclei
findings on one approved non-production asset class**, with the full decision trace *and* a
rules-only baseline running alongside for comparison. It extends the pattern already proven in
the Grafana/VulHub demo — just on sanctioned internal assets, with the governance wrapper.

## The plan

| Phase | Engineer A (security/scanning) | Engineer B (agent/eval) | Exit gate |
|---|---|---|---|
| **Days 0–30 — De-risk** | Isolated Nuclei runner; curated real-template catalog (beyond the toy set); approved-asset allowlist + scope guard hardened | Productionize planner + policy guard + trace store; expand eval harness to real targets + **add a 2nd model**; design the riskiest-unknown experiment | Reproducible results on **real (non-toy) targets**, rules-vs-LLM, with traces |
| **Days 31–60 — Pilot-ready** | SSO/RBAC + secrets vault; SIEM/log feed; rate-limits + change-window controls | **Analyst review UI** (the human-in-the-loop that is only design-intent today); precision/recall + cost + reliability on real CVEs | **AppSec-approved pilot design** + compliance sign-off package |
| **Days 61–90 — Pilot & decide** | Run the pilot on a few approved **non-production** assets; harden ops | ROI vs a tuned rules baseline on real data; analyst-feedback loop | **Build / stop / continue** decision, evidence-backed |

## The riskiest unknown
> **Does the LLM's context-aware prioritization hold up on real, messy targets with many
> findings — and beat a *well-tuned rules baseline* by a margin that justifies its latency,
> token cost, and governance burden?**

Our toy + single-CVE evidence is promising (3/3 vs 0/1, context-driven 6/6, fails safe), but a
controlled lab makes the LLM look better than messy reality will. Everything else (scope guards,
isolation, auditability) is ordinary engineering; **this** is the question the pilot exists to answer.

## What would make us change course
- **Pivot to "rules + LLM-for-explanations":** if, on real data, the LLM shows **no prioritization
  lift** over rules, **or** its invalid/blocked rate rises materially, **or** analysts don't trust/use
  it — drop the LLM as a *decision-maker* and keep it only for analyst-facing narrative.
- **Stop / go rules-only:** if compliance cannot approve *any* model data egress, even self-hosted.
- **Accelerate:** if the lift is large and analysts adopt it, widen the template catalog and asset scope.

## Resourcing notes
- **Model hosting:** budget for a **self-hosted** model option early (the pilot's compliance story
  likely depends on it); keep the OpenAI-compatible interface so the model is swappable.
- **No new headcount beyond the two engineers** for the 90 days; analyst time is borrowed from
  the existing AppSec team for the review loop.
