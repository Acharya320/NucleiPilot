"""The agent loop: observe -> reason -> act -> reassess.

Phases:
  1. DISCOVERY  -- run every indicator template once (the cheap signal pass).
  2. DECISION   -- while budget remains: the planner proposes a follow-up,
                   the POLICY GUARD independently approves/blocks it, and only
                   approved validations run. Every step is recorded in the trace.
  3. REASSESS   -- turn the evidence into a per-issue verdict:
                   CONFIRMED / DISMISSED / UNVERIFIED / CLEAN.

The workflow never consults ground truth; decisions use evidence only. Scoring
against ground truth happens separately in the experiment harness.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

from . import policy, scanner

ISSUES = ("admin", "debug")


@dataclass
class Observation:
    template_id: str
    kind: str
    issue: str
    matched: bool
    matched_at: str | None
    severity: str | None
    duration_s: float | None
    error: str | None = None


@dataclass
class TraceEvent:
    step: str          # discovery | decision | policy | action | reassess
    detail: dict


@dataclass
class WorkflowState:
    target: str
    target_context: dict = field(default_factory=dict)
    observations: list = field(default_factory=list)
    fired_indicators: set = field(default_factory=set)
    confirmed_issues: set = field(default_factory=set)
    dismissed_issues: set = field(default_factory=set)
    run_templates: set = field(default_factory=set)
    budget_remaining: int = 0


def _all_pending_validations(state: WorkflowState) -> list[str]:
    return [v.id for v in policy.validations() if v.id not in state.run_templates]


def _signal_pending_validations(state: WorkflowState) -> list[str]:
    out = []
    for ind_id in state.fired_indicators:
        v = policy.validation_for(ind_id)
        if v and v.id not in state.run_templates:
            out.append(v.id)
    return out


def _finalize(state: WorkflowState) -> dict:
    """Per-issue verdict from the evidence gathered."""
    result = {}
    for issue in ISSUES:
        ind = next((s for s in policy.indicators() if s.issue == issue), None)
        fired = bool(ind) and ind.id in state.fired_indicators
        if issue in state.confirmed_issues:
            status = "CONFIRMED"      # validation ran and matched
        elif issue in state.dismissed_issues:
            status = "DISMISSED"      # validation ran, no match -> signal rejected (good)
        elif fired:
            status = "UNVERIFIED"     # signal present but not followed up (budget/decision)
        else:
            status = "CLEAN"          # no signal at all
        result[issue] = status
    return result


def run_workflow(target, planner, *, budget=2, target_context=None, nuclei_bin=None, scan_fn=None):
    # scan_fn lets tests inject a deterministic fake scanner; the default is the
    # real, scope-guarded Nuclei wrapper.
    scan = scan_fn or (lambda t, p: scanner.run_template(t, p, nuclei_bin=nuclei_bin))
    state = WorkflowState(target=target, target_context=target_context or {},
                          budget_remaining=budget)
    trace: list[TraceEvent] = []
    t0 = time.monotonic()

    # --- Phase 1: discovery ------------------------------------------------
    for spec in sorted(policy.indicators(), key=lambda s: s.id):
        res = scan(target, policy.template_path(spec.id))
        state.observations.append(Observation(
            spec.id, spec.kind, spec.issue, res.matched, res.matched_at,
            res.severity, res.duration_s, res.error))
        state.run_templates.add(spec.id)
        if res.matched:
            state.fired_indicators.add(spec.id)
        trace.append(TraceEvent("discovery", {
            "template": spec.id, "matched": res.matched,
            "evidence_at": res.matched_at, "error": res.error}))

    # --- Phase 2: decision loop -------------------------------------------
    while state.budget_remaining > 0:
        eligible = (_all_pending_validations(state) if planner.exhaustive
                    else _signal_pending_validations(state))
        decision = planner.decide(state, eligible)
        trace.append(TraceEvent("decision", {
            "planner": planner.name, "proposed": decision.next_template,
            "reason": decision.reason, "confidence": decision.confidence,
            "stop_reason": decision.stop_reason,
            "evidence_referenced": decision.evidence_referenced, "raw": decision.raw}))

        verdict = policy.validate_choice(decision.next_template, eligible)
        trace.append(TraceEvent("policy", {
            "proposed": decision.next_template, "ok": verdict.ok, "reason": verdict.reason}))

        if decision.next_template is None:          # planner chose to stop
            break
        if not verdict.ok:                          # blocked -> run nothing, stop
            trace.append(TraceEvent("action", {
                "template": decision.next_template, "executed": False,
                "blocked_reason": verdict.reason}))
            break

        spec = policy.get(decision.next_template)
        res = scan(target, policy.template_path(spec.id))
        state.run_templates.add(spec.id)
        state.budget_remaining -= 1
        state.observations.append(Observation(
            spec.id, spec.kind, spec.issue, res.matched, res.matched_at,
            res.severity, res.duration_s, res.error))
        if res.matched:
            state.confirmed_issues.add(spec.issue)
        else:
            state.dismissed_issues.add(spec.issue)
        trace.append(TraceEvent("action", {
            "template": spec.id, "executed": True, "matched": res.matched,
            "evidence_at": res.matched_at}))

    # --- Phase 3: reassess -------------------------------------------------
    assessment = _finalize(state)
    trace.append(TraceEvent("reassess", {"assessment": assessment}))
    elapsed = time.monotonic() - t0

    return {
        "target": target,
        "planner": planner.name,
        "budget": budget,
        "target_context": state.target_context,
        "fired_indicators": sorted(state.fired_indicators),
        "assessment": assessment,
        "templates_run": sorted(state.run_templates),
        "n_templates_run": len(state.run_templates),
        "observations": [asdict(o) for o in state.observations],
        "trace": [asdict(e) for e in trace],
        "elapsed_s": round(elapsed, 3),
    }
