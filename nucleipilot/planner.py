"""Planners: the decision-makers that choose the next follow-up (or stop).

All planners share one interface -- `decide(state, eligible_ids) -> Decision` --
so the workflow and the policy guard treat them identically. This file holds the
two NON-AI baselines; the LLM planner (added next) implements the same interface.

  * FixedPlanner  (baseline A): exhaustive -- run every template, ignore evidence.
  * RulePlanner   (baseline B): adaptive  -- validate a fired indicator, highest
                                severity first; stop when no signal needs follow-up.

`exhaustive` tells the workflow which candidate set to offer the planner:
all pending validations (Fixed) vs. only those whose indicator fired (Rule/LLM).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import policy

_SEV_RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}


def _severity_of(template_id: str) -> int:
    spec = policy.get(template_id)
    return _SEV_RANK.get(spec.severity, 0) if spec else 0


@dataclass
class Decision:
    next_template: str | None            # None => stop
    reason: str
    confidence: float | None = None
    evidence_referenced: list = field(default_factory=list)
    stop_reason: str | None = None
    raw: dict | None = None              # raw model output, for the LLM planner


class Planner:
    name = "base"
    exhaustive = False

    def decide(self, state, eligible_ids) -> Decision:  # noqa: D401
        raise NotImplementedError


class FixedPlanner(Planner):
    """Run every available template regardless of evidence (the conventional scan)."""
    name = "fixed"
    exhaustive = True

    def decide(self, state, eligible_ids) -> Decision:
        if not eligible_ids:
            return Decision(None, "fixed/exhaustive: all templates have been run",
                            stop_reason="exhausted")
        nxt = sorted(eligible_ids, key=lambda t: (-_severity_of(t), t))[0]
        return Decision(nxt, "fixed/exhaustive: run every template regardless of evidence")


class RulePlanner(Planner):
    """Adaptive if/then: validate a fired indicator, highest severity first."""
    name = "rule"
    exhaustive = False

    def decide(self, state, eligible_ids) -> Decision:
        if not eligible_ids:
            return Decision(None, "no fired indicator has a pending validation",
                            stop_reason="no eligible follow-up")
        nxt = sorted(eligible_ids, key=lambda t: (-_severity_of(t), t))[0]
        spec = policy.get(nxt)
        return Decision(
            nxt,
            f"rule: the {spec.issue!r} indicator fired; validate the highest-severity signal first",
            evidence_referenced=[spec.validates] if spec and spec.validates else [],
        )


_LLM_SYSTEM = """You are a cautious security-assessment assistant operating inside a strict policy harness.
Your job: pick the SINGLE most valuable next follow-up check to run against an AUTHORIZED, LOCAL sandbox target, or decide to STOP.

Hard rules:
- You may ONLY choose a next_template from the list of ELIGIBLE ACTIONS, using its exact id. Never invent an id.
- A weak indicator is NOT a confirmed finding. Prefer the check that most reduces uncertainty for the HIGHEST-IMPACT issue, given the target context and the remaining budget.
- If no eligible action is worth the remaining budget, STOP: set next_template to null and give a stop_reason.
- Respond with STRICT JSON only (no prose, no code fences), exactly this schema:
  {"next_template": <string id or null>, "reason": <string>, "confidence": <number 0..1>, "evidence_referenced": [<string ids>], "stop_reason": <string or null>}"""


class LLMPlanner(Planner):
    """Context-aware planner: an LLM chooses among the SAME eligible actions,
    then the policy guard independently approves/blocks the choice."""
    name = "llm"
    exhaustive = False

    def __init__(self, client=None, temperature: float = 0.0):
        if client is None:
            from .llm_client import LLMClient
            client = LLMClient(temperature=temperature)
        self.client = client

    def _build_user_prompt(self, state, eligible_ids) -> str:
        import json as _json
        ind_obs = [o for o in state.observations if o.kind == "indicator"]
        evidence = "\n".join(
            f"- {o.template_id}: {'MATCHED' if o.matched else 'no match'}"
            + (f" at {o.matched_at}" if o.matched else "")
            + f"  (issue={o.issue})"
            for o in ind_obs
        ) or "- (no indicators run yet)"
        actions = []
        for tid in eligible_ids:
            s = policy.get(tid)
            actions.append(
                f"- id={tid}  issue={s.issue}  severity={s.severity}\n"
                f"    purpose: {s.purpose}\n"
                f"    possible_false_positive: {s.possible_false_positive}"
            )
        actions_str = "\n".join(actions) if actions else "- (none)"
        ctx = _json.dumps(state.target_context, indent=2) if state.target_context else "(none provided)"
        return (
            f"TARGET CONTEXT:\n{ctx}\n\n"
            f"REMAINING FOLLOW-UP BUDGET: {state.budget_remaining} "
            f"(you may run at most this many more checks)\n\n"
            f"EVIDENCE SO FAR (indicator results):\n{evidence}\n\n"
            f"ELIGIBLE ACTIONS (choose exactly one id, or STOP):\n{actions_str}\n\n"
            f"Return the JSON decision now."
        )

    def decide(self, state, eligible_ids) -> Decision:
        if not eligible_ids:
            return Decision(None, "no eligible follow-up remains",
                            stop_reason="no eligible follow-up")
        user = self._build_user_prompt(state, eligible_ids)
        parsed, raw_text, usage, error = self.client.chat_json(_LLM_SYSTEM, user)
        if error or parsed is None:
            # Never guess on failure: stop safely and record what happened.
            return Decision(None, f"LLM unusable output: {error}",
                            stop_reason="llm_invalid_output",
                            raw={"raw_text": raw_text, "error": error, "usage": usage})
        nxt = parsed.get("next_template")
        if isinstance(nxt, str) and nxt.strip().lower() in ("", "null", "none", "stop"):
            nxt = None
        return Decision(
            next_template=nxt,
            reason=str(parsed.get("reason", "")),
            confidence=parsed.get("confidence"),
            evidence_referenced=parsed.get("evidence_referenced", []) or [],
            stop_reason=parsed.get("stop_reason"),
            raw={"parsed": parsed, "usage": usage, "model": getattr(self.client, "model", None)},
        )
