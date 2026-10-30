"""The four v2 planners (the decision layer of the A/B/C comparison).

All share one interface so the engine and the policy guard treat them identically:

    decide(pending, evidence, remaining_budget, context) -> Decision

where `pending` is the list of candidate validations not yet run (each a dict with
validation id, endpoint, business_importance, tech_severity, purpose, FP note).

  * FixedPlanner      (A)  exhaustive: run every validation; the reference ceiling.
  * SeverityRule      (B1) order by technical severity, stable tie-break.
  * ContextRule       (B2) order by business importance, then severity -- the STRONG
                           non-LLM baseline (a few lines of Python); the real bar for C.
  * LLMPlanner        (C)  an LLM proposes from the SAME candidates + evidence + budget;
                           the policy guard independently approves/blocks every choice.

A planner only ever *proposes*. config/catalog.json + policy.validate_choice decide,
in code, whether a proposal runs. The model cannot invent an id or reach a new host.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import registry

_SEV_RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}


def _sev(c) -> int:
    return _SEV_RANK.get(c.get("tech_severity"), 0)


def _imp(c) -> int:
    return registry.importance_rank(c.get("business_importance"))


@dataclass
class Decision:
    chosen: str | None             # a validation id, or None => stop
    reason: str
    confidence: float | None = None
    stop_reason: str | None = None
    raw: dict | None = None


class Planner:
    name = "base"
    exhaustive = False

    def decide(self, pending, evidence, remaining_budget, context=None) -> Decision:
        raise NotImplementedError


class FixedPlanner(Planner):
    """A -- run every validation regardless of business or evidence (the ceiling)."""
    name = "fixed"
    exhaustive = True

    def decide(self, pending, evidence, remaining_budget, context=None) -> Decision:
        if not pending:
            return Decision(None, "fixed/exhaustive: all validations have run", stop_reason="exhausted")
        nxt = sorted(pending, key=lambda c: (-_sev(c), c["validation"]))[0]
        return Decision(nxt["validation"], "fixed/exhaustive: run every validation")


class SeverityRulePlanner(Planner):
    """B1 -- highest technical severity first; no business context. Stable tie-break."""
    name = "rule-severity"

    def decide(self, pending, evidence, remaining_budget, context=None) -> Decision:
        if not pending:
            return Decision(None, "no candidate remains", stop_reason="exhausted")
        nxt = sorted(pending, key=lambda c: (-_sev(c), c["validation"]))[0]
        return Decision(nxt["validation"],
                        f"severity rule: validate the highest-severity signal first "
                        f"({nxt['tech_severity']} on {nxt['endpoint']})")


class ContextRulePlanner(Planner):
    """B2 -- business importance first, then severity. The strong non-LLM baseline."""
    name = "rule-context"

    def decide(self, pending, evidence, remaining_budget, context=None) -> Decision:
        if not pending:
            return Decision(None, "no candidate remains", stop_reason="exhausted")
        nxt = sorted(pending, key=lambda c: (-_imp(c), -_sev(c), c["validation"]))[0]
        return Decision(nxt["validation"],
                        f"context rule: validate the most business-critical signal first "
                        f"({nxt['business_importance']} business on {nxt['endpoint']})")


_LLM_SYSTEM = """You are a cautious security-assessment assistant inside a strict policy harness.
Pick the SINGLE most valuable next validation to run on an AUTHORIZED, LOCAL sandbox, or decide to STOP.

Hard rules:
- Choose a "chosen" ONLY from the CANDIDATES list, using its exact validation id. Never invent an id.
- A fired indicator is NOT a confirmed finding. Prefer the check that most reduces risk for the asset that matters MOST to the business, given the remaining budget and the evidence so far.
- If nothing is worth the remaining budget, STOP: set "chosen" to null and give a stop_reason.
- Respond with STRICT JSON only (no prose, no code fences), exactly this schema:
  {"chosen": <string id or null>, "reason": <string>, "confidence": <number 0..1>, "stop_reason": <string or null>}"""


class LLMPlanner(Planner):
    """C -- an LLM chooses among the SAME candidates; the policy guard approves/blocks."""
    name = "llm"

    def __init__(self, client=None, temperature: float = 0.0):
        if client is None:
            from .llm_client import LLMClient
            client = LLMClient(temperature=temperature)
        self.client = client

    def _build_user_prompt(self, pending, evidence, remaining_budget, context) -> str:
        import json as _json
        cands = "\n".join(
            f"- id={c['validation']}  endpoint={c['endpoint']}  "
            f"business_importance={c['business_importance']}  tech_severity={c['tech_severity']}\n"
            f"    purpose: {c.get('purpose')}\n"
            f"    possible_false_positive: {c.get('possible_false_positive')}"
            for c in pending
        ) or "- (none)"
        ev = "\n".join(
            f"- {e['validation']} on {e['endpoint']}: {e['status']}" for e in evidence
        ) or "- (no validations run yet)"
        ctx = _json.dumps(context, indent=2) if context else "(none)"
        return (
            f"ASSET CONTEXT:\n{ctx}\n\n"
            f"REMAINING VALIDATION BUDGET: {remaining_budget} "
            f"(you may run at most this many more validations)\n\n"
            f"EVIDENCE SO FAR (results of validations already run):\n{ev}\n\n"
            f"CANDIDATES (choose exactly one id, or STOP):\n{cands}\n\n"
            f"Return the JSON decision now."
        )

    def decide(self, pending, evidence, remaining_budget, context=None) -> Decision:
        if not pending:
            return Decision(None, "no candidate remains", stop_reason="exhausted")
        user = self._build_user_prompt(pending, evidence, remaining_budget, context)
        parsed, raw_text, usage, error = self.client.chat_json(_LLM_SYSTEM, user)
        if error or parsed is None:
            # Never guess on failure: stop safely and record what happened.
            return Decision(None, f"LLM unusable output: {error}", stop_reason="llm_invalid_output",
                            raw={"raw_text": raw_text, "error": error, "usage": usage})
        chosen = parsed.get("chosen")
        if isinstance(chosen, str) and chosen.strip().lower() in ("", "null", "none", "stop"):
            chosen = None
        return Decision(
            chosen=chosen,
            reason=str(parsed.get("reason", "")),
            confidence=parsed.get("confidence"),
            stop_reason=parsed.get("stop_reason"),
            raw={"parsed": parsed, "usage": usage, "model": getattr(self.client, "model", None)},
        )


# Convenience registry for the experiment harness.
def all_rule_planners() -> list[Planner]:
    return [FixedPlanner(), SeverityRulePlanner(), ContextRulePlanner()]
