"""Policy guard: the approved-template allowlist and the independent check that
every planner's proposal must pass BEFORE the scanner runs anything.

This is the safety core. The LLM (or any planner) only ever *proposes* a
template id. `validate_choice` decides, in code, whether that proposal is:
  1. a real, approved template (in the allowlist), and
  2. actually eligible at this step (the workflow decides what's eligible).
Anything else is blocked and logged. The model cannot invent a template,
reach a new target, or run a raw command -- those paths simply do not exist.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(_REPO, "templates")


@dataclass(frozen=True)
class TemplateSpec:
    id: str
    filename: str
    issue: str                 # "admin" | "debug"
    kind: str                  # "indicator" | "validation"
    purpose: str               # plain-language description for the planner
    severity: str              # info | low | medium | high | critical
    validates: str | None = None          # for a validation: the indicator it confirms
    cost: int = 1                          # budget units this check consumes
    possible_false_positive: str | None = None


# The ONLY templates any planner is allowed to run. Add here deliberately.
ALLOWLIST: dict[str, TemplateSpec] = {
    t.id: t
    for t in [
        TemplateSpec(
            "demo-admin-indicator", "demo-admin-indicator.yaml", "admin", "indicator",
            "Signals that a management/admin surface may exist (weak signal only).",
            "info",
        ),
        TemplateSpec(
            "demo-admin-validation", "demo-admin-validation.yaml", "admin", "validation",
            "Confirms the management endpoint does not require authentication.",
            "medium", validates="demo-admin-indicator",
            possible_false_positive="A management surface can exist yet still require auth.",
        ),
        TemplateSpec(
            "demo-debug-indicator", "demo-debug-indicator.yaml", "debug", "indicator",
            "Signals that debug mode may be enabled (weak signal only).",
            "info",
        ),
        TemplateSpec(
            "demo-debug-validation", "demo-debug-validation.yaml", "debug", "validation",
            "Confirms a debug interface is actually exposed (returns a synthetic token).",
            "high", validates="demo-debug-indicator",
            possible_false_positive="A debug flag can be set WITHOUT exposing an interface (the benign trap).",
        ),
    ]
}


@dataclass
class PolicyResult:
    ok: bool
    reason: str


def get(template_id: str) -> TemplateSpec | None:
    return ALLOWLIST.get(template_id)


def template_path(template_id: str) -> str:
    spec = ALLOWLIST.get(template_id)
    if spec is None:
        raise KeyError(f"{template_id!r} is not an approved template")
    return os.path.join(TEMPLATES_DIR, spec.filename)


def indicators() -> list[TemplateSpec]:
    return [t for t in ALLOWLIST.values() if t.kind == "indicator"]


def validations() -> list[TemplateSpec]:
    return [t for t in ALLOWLIST.values() if t.kind == "validation"]


def validation_for(indicator_id: str) -> TemplateSpec | None:
    """The validation template that confirms a given indicator, if any."""
    return next((t for t in validations() if t.validates == indicator_id), None)


def validate_choice(chosen_id: str | None, eligible_ids) -> PolicyResult:
    """The independent guard. `chosen_id=None` means 'stop', always permitted."""
    if chosen_id is None:
        return PolicyResult(True, "stop is always permitted")
    if chosen_id not in ALLOWLIST:
        return PolicyResult(False, f"BLOCKED: {chosen_id!r} is not in the approved allowlist")
    if chosen_id not in set(eligible_ids):
        return PolicyResult(
            False,
            f"BLOCKED: {chosen_id!r} is approved but not eligible at this step "
            f"(eligible: {sorted(eligible_ids)})",
        )
    return PolicyResult(True, f"approved: {chosen_id!r} is in the allowlist and eligible")
