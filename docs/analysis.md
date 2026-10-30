# Analysis — NucleiPilot (Part 2, one-pager)

*An honest evaluation of the PoC run against the localhost toy sandbox and the local Grafana 8.3.0
container. Every claim maps to a file in [`../results/final/`](../results/final/); see
[`findings.md`](../results/final/findings.md) for the claim-by-claim evidence and [`toy_spec.md`](toy_spec.md)
§7 for what the toy can and cannot prove. All testing was localhost-only and read-only.*

## What worked
- **Governance held under adversarial input.** Under "model proposes, code authorizes," all four
  failure modes failed safe — out-of-scope target, invented template id, malformed LLM JSON, and an
  over-budget request (E5, `safety_checks.md`). Every scan is authorized in code and fully traced.
- **Evidence-based triage rejected a false positive.** `/docs` and `/health` emit the *identical* weak
  debug indicator; only the validation's content signature separates them — `/docs` **CONFIRMED**,
  `/health` **NOT_CONFIRMED** (E3, `e3_trap.json`).
- **Business-aware prioritization under a tight budget.** At budget 2, the severity-only rule (B1)
  chose the high-severity `/docs` check, **missed** the business-critical `/payments` + `/account`, and
  wasted a slot on the trap; the context-aware rule (B2) and the LLM (C) both confirmed
  `/payments` + `/account` (E1, `summary.md`, `comparison.csv`).
- **Decisions followed context, not a fixed favourite.** Swapping the business importance moved B2's
  and C's first pick to `/docs` (E2).
- **It generalized to a real app with no new decision code.** On local Grafana 8.3.0 the agent
  fingerprinted the version and chose the applicable CVE-2021-43798 over an inapplicable distractor,
  then confirmed arbitrary file read **read-only** via a harmless planted marker (E4/E6,
  `grafana_demo.json`).

## What failed / did not add value (stated plainly)
- **No detection lift.** At full budget (planner A) every planner found every issue — detection is
  Nuclei's job, not the agent's.
- **On this toy the LLM only *ties* a well-tuned rule.** C matched B2's confirmed set; it did not beat
  it. The toy is small and fully labeled, so anything the LLM does well, a few lines of context rule
  (B2) can encode — the tie is a property of the toy's size, not proof the LLM wins (`toy_spec.md` §7).
- **LLM output is not perfectly repeatable.** Across 3 runs C confirmed the same *set* every time but
  validated it in a different *order* (gpt-4o-mini nondeterminism). Under the budget the outcome is
  unchanged, and the harness reports this rather than hiding it.

## Where human intervention was required
- A human defines the **scope** (asset registry + the localhost scope guard), the **approved catalog**
  of templates, the per-endpoint **business importance**, and the **budget**. The agent reasons
  *within* these; it does not invent them.
- A human authored the templates and the ground-truth **answer key** used to score the runs.
- The PoC stops at **triage.** Acting on a CONFIRMED finding (remediation, deeper exploitation) is left
  to a human — the agent decides *what to validate next*, not *what to do about it*.

## False positives / negatives & reliability
- **False positive:** the benign `/health` trap is the designed FP — correctly rejected on evidence
  (NOT_CONFIRMED). The severity-only baseline effectively "chased" it; the agent did not.
- **False-negative guard:** a scan error is labelled `TEST_ERROR` (checked *before* a match), so a
  failed scan is never silently counted as "clean."
- **Reliability caveats:** a single model was tested (`gpt-4o-mini`); the sample is small and fully
  labeled; and the pick-order nondeterminism above is real. These are why the recommendation is a
  *scoped pilot*, not a build.

## Did the agentic layer improve the workflow?
**Yes — narrowly, and honestly.** Under a realistic budget it prioritized the business-critical issues
a conventional severity-first pass missed, rejected a false positive on evidence, did so under hard
governance with a full audit trail, and extended to a new real target with zero new decision code. It
did **not** improve detection, and on this small toy it *tied* rather than beat a well-tuned rule. The
durable value is **governance + evidence discipline + generalization**. Whether the LLM's
prioritization beats a tuned rule on messy, unlabeled real targets is exactly the question the 90-day
pilot is built to answer — with a pre-committed kill-criterion (see [build_decision.md](build_decision.md)).
