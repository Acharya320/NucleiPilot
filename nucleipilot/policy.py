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

import json
import os
from dataclasses import dataclass

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(_REPO, "templates")
CONFIG_DIR = os.path.join(_REPO, "config")
TOY_CATALOG_PATH = os.path.join(CONFIG_DIR, "catalog.json")


@dataclass(frozen=True)
class TemplateSpec:
    id: str
    filename: str
    issue: str                 # "admin" | "debug"
    kind: str                  # "indicator" | "validation"
    purpose: str               # plain-language description for the planner
    severity: str              # info | low | medium | high | critical
    validates: str | None = None          # for a validation: the indicator it confirms
    cost: int = 1                          # budget units this check consumes (v2: indicator=0, validation=1)
    possible_false_positive: str | None = None
    endpoint: str | None = None            # app component this maps to (None = shared, e.g. the debug indicator)


# The approved template catalog lives in config/catalog.json and is loaded on
# demand (see toy_catalog / load_catalog below). The allowlist rule still holds:
# a planner may only run a template that appears in the active catalog.


@dataclass
class PolicyResult:
    ok: bool
    reason: str


_DEFAULT_CATALOG: dict[str, TemplateSpec] | None = None


def _default_catalog() -> dict[str, TemplateSpec]:
    """The built-in default catalog (the scaled toy's config/catalog.json), loaded once."""
    global _DEFAULT_CATALOG
    if _DEFAULT_CATALOG is None:
        _DEFAULT_CATALOG = toy_catalog()
    return _DEFAULT_CATALOG


def _cat(catalog):
    """The catalog to use: the caller's, else the built-in default (config/catalog.json)."""
    return catalog if catalog is not None else _default_catalog()


def load_catalog(path: str) -> dict[str, TemplateSpec]:
    """Load an approved catalog from a JSON file into TemplateSpec objects.

    The catalog is the generalization seam: growing coverage means adding an
    entry here (and the YAML), not changing code. See config/catalog.json.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    cat: dict[str, TemplateSpec] = {}
    for e in data["templates"]:
        spec = TemplateSpec(
            id=e["id"], filename=e["file"], issue=e["issue"], kind=e["kind"],
            purpose=e.get("purpose", ""), severity=e["severity"],
            validates=e.get("validates"), cost=int(e.get("cost", 1)),
            possible_false_positive=e.get("possible_false_positive"),
            endpoint=e.get("endpoint"),
        )
        cat[spec.id] = spec
    return cat


def toy_catalog() -> dict[str, TemplateSpec]:
    """The approved catalog for the scaled toy app (config/catalog.json)."""
    return load_catalog(TOY_CATALOG_PATH)


def get(template_id: str, catalog=None) -> TemplateSpec | None:
    return _cat(catalog).get(template_id)


def template_path(template_id: str, catalog=None) -> str:
    spec = _cat(catalog).get(template_id)
    if spec is None:
        raise KeyError(f"{template_id!r} is not an approved template")
    return os.path.join(TEMPLATES_DIR, spec.filename)


def indicators(catalog=None) -> list[TemplateSpec]:
    return [t for t in _cat(catalog).values() if t.kind == "indicator"]


def validations(catalog=None) -> list[TemplateSpec]:
    return [t for t in _cat(catalog).values() if t.kind == "validation"]


def validation_for(indicator_id: str, catalog=None) -> TemplateSpec | None:
    """The validation that confirms a given indicator (first match).

    When an indicator is shared across endpoints (the debug indicator fires on
    both /docs and /health), prefer validation_for_endpoint to disambiguate.
    """
    return next((t for t in validations(catalog) if t.validates == indicator_id), None)


def validation_for_endpoint(indicator_id: str, endpoint: str | None, catalog=None) -> TemplateSpec | None:
    """The validation that confirms (indicator, endpoint).

    Needed for the shared debug indicator, whose real validation (/docs) and
    benign trap (/health) differ only by endpoint.
    """
    return next(
        (t for t in validations(catalog)
         if t.validates == indicator_id and t.endpoint == endpoint),
        None,
    )


def validate_choice(chosen_id: str | None, eligible_ids, catalog=None) -> PolicyResult:
    """The independent guard. `chosen_id=None` means 'stop', always permitted.

    `catalog` defaults to the built-in catalog (config/catalog.json); the engine passes its own.
    """
    cat = _cat(catalog)
    if chosen_id is None:
        return PolicyResult(True, "stop is always permitted")
    if chosen_id not in cat:
        return PolicyResult(False, f"BLOCKED: {chosen_id!r} is not in the approved allowlist")
    if chosen_id not in set(eligible_ids):
        return PolicyResult(
            False,
            f"BLOCKED: {chosen_id!r} is approved but not eligible at this step "
            f"(eligible: {sorted(eligible_ids)})",
        )
    return PolicyResult(True, f"approved: {chosen_id!r} is in the allowlist and eligible")
