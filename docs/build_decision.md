# The Call: Should We Build This?

*AMEX / Atos take-home, Part 5. A decisive recommendation, grounded in the evidence from
Parts 1–4, plus the one fact that would flip it.*

---

## Recommendation: **YES — but as a scoped, time-boxed pilot, not a product build.**

Fund the **90-day, 2-person pilot** in [two_person_roadmap.md](two_person_roadmap.md) to build
**one thing**: a transparent, governed, agentic **triage/follow-up layer** on top of Nuclei —
**not** an autonomous exploitation platform. Decide "productionize vs stop" at day 90 on the
evidence the pilot produces.

## Why this is the right call (the evidence)

1. **There is a real, unclaimed niche** ([landscape](landscape_and_capability_map.md)). The market
   is crowded with *autonomy* (XBOW, RunSybil, NodeZero) and OSS *maximal-autonomy* tools
   (PentAGI, Strix). What's thin is a **transparent, governed, evidence-backed** agentic layer —
   exactly what a regulated buyer like AMEX values, and what the leaders under-serve.
2. **The agentic layer earns its place — narrowly.** Our evaluation ([summary](../results/final/summary.md))
   is deliberately honest: at full budget the LLM adds **no** detection value over simple rules.
   But under a budget it delivered **context-aware prioritization** (3/3 vs rules 0/1), the choice
   **flips with context (6/6)** so it's reasoning not bias, and it **fails safe** on bad input.
3. **It generalizes.** The same agent chose the applicable CVE on a **real app** (Grafana 8.3.0 /
   CVE-2021-43798) using Nuclei's official templates — so this isn't a toy-only effect.
4. **It's governable.** Scope allowlist, template allowlist, bounded budget, full audit trace, and
   fail-safe behavior are already demonstrated — the controls a bank's stakeholders ask for first
   ([architecture](enterprise_architecture.md)).

## What we are **not** recommending
- Not a full autonomous pentest/exploitation product (that's XBOW/RunSybil's game; we don't compete there).
- Not replacing human pentesters or existing scanners.
- Not a broad production rollout before the pilot proves real-world value.

## The one fact that would flip the answer to **NO**
> **If the 90-day pilot shows the LLM's prioritization does *not* beat a well-tuned rules baseline
> on real, messy targets — by a margin that justifies its latency, token cost, and governance
> burden — then do not build the AI decision layer.**

In that case the fallback is **rules for the decisions, LLM only for analyst-facing explanations** —
cheaper, simpler, and still useful. (A second, hard stop: if compliance cannot approve *any* model
data egress, even self-hosted, go fully rules-based.)

## Decision gate
- **Day 30:** reproducible rules-vs-LLM results on real targets → continue or stop.
- **Day 60:** AppSec + compliance sign-off on the pilot design → continue or stop.
- **Day 90:** measured lift vs rules on pilot data → **build / stop / keep-as-rules+explanations**.

**Bottom line:** the honest, evidence-based answer is *"yes, pilot it"* — because the unclaimed
ground is real and the governed-triage value is demonstrable — **with a crisp, pre-committed kill
criterion** so we don't build an AI layer that a rule could do for less.
