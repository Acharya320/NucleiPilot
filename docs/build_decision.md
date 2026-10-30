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
2. **The agentic layer earns its place — narrowly, and we are honest about where.** Our evaluation
   ([summary](../results/final/summary.md), [test results](../results/final/README.md)) is deliberately
   honest. Under a tight budget, a **naive severity-only** rule (B1) missed the business-critical
   `/payments` + `/account` and wasted a scan on a benign trap, while a **context-aware** rule (B2) and
   the LLM (C) both confirmed the two business-important issues. The first pick **flips when business
   context is swapped** (B2 and C both move) — reasoning, not a fixed favourite — and the loop **fails
   safe** on an out-of-scope target, an invented template, malformed model output, and an over-budget
   request. The honest headline: on this small, fully-labeled toy the LLM **ties** the well-tuned
   context-aware rule (B2); it does not beat it. The durable value is the governed, evidence-driven loop
   and its generalization — not the model out-picking a rule (see [toy_spec](toy_spec.md) §7).
3. **It generalizes without hand-written per-CVE logic.** Pointed at a **real app** (local Grafana
   8.3.0), the same engine fingerprinted the version and reasoned to the **applicable** CVE-2021-43798
   over an inapplicable distractor (CVE-2020-13379) with **zero CVE-specific decision code** — a new
   target is just one more registry + catalog entry. The arbitrary-file read was confirmed read-only via
   a harmless planted marker, and corroborated with ProjectDiscovery's **official** community template
   (`../results/final/vulhub_grafana_demo.json`) — so this isn't a toy-only effect.
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
