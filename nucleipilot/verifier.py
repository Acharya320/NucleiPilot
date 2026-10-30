"""Evidence verifier: assigns each finding exactly ONE status, in code, from the
Nuclei evidence -- never from the model, and never from the sandbox answer key.

The five statuses (see docs/toy_spec.md §9):
  CONFIRMED      validation ran and its finding-specific signature matched
  NOT_CONFIRMED  validation ran, required evidence absent (e.g. the benign trap)
  UNVERIFIED     indicator fired, but no validation ran (budget exhausted)
  NO_INDICATOR   no indicator fired (NOT a claim the endpoint is secure)
  TEST_ERROR     the scan/HTTP validation failed -- never counted as a negative

CONFIRMED relies on validations being signature-specific: a validation template
matches ONLY when its content signature is present. config/catalog.json and the
tests enforce that, so a validation's matched==True means the signature was found.
"""
from __future__ import annotations

from dataclasses import dataclass, field

CONFIRMED = "CONFIRMED"
NOT_CONFIRMED = "NOT_CONFIRMED"
UNVERIFIED = "UNVERIFIED"
NO_INDICATOR = "NO_INDICATOR"
TEST_ERROR = "TEST_ERROR"
VERDICTS = {CONFIRMED, NOT_CONFIRMED, UNVERIFIED, NO_INDICATOR, TEST_ERROR}


def verdict(indicator_fired: bool, validation_result=None) -> str:
    """The deterministic status rule. `validation_result` is a scanner.ScanResult
    (or None if no validation ran). Error is checked before match, so a failed
    scan is a TEST_ERROR, never a (false) negative."""
    if not indicator_fired:
        return NO_INDICATOR
    if validation_result is None:
        return UNVERIFIED
    if getattr(validation_result, "error", None):
        return TEST_ERROR
    if getattr(validation_result, "matched", False):
        return CONFIRMED
    return NOT_CONFIRMED


@dataclass
class Finding:
    endpoint: str
    issue: str
    indicator: str
    indicator_fired: bool
    validation: str | None
    status: str
    tech_severity: str | None = None
    business_importance: str | None = None
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "endpoint": self.endpoint, "issue": self.issue,
            "indicator": self.indicator, "indicator_fired": self.indicator_fired,
            "validation": self.validation, "status": self.status,
            "tech_severity": self.tech_severity,
            "business_importance": self.business_importance,
            "evidence": self.evidence,
        }


def make_finding(*, endpoint, issue, indicator, indicator_fired,
                 validation=None, validation_result=None,
                 tech_severity=None, business_importance=None) -> Finding:
    """Build a Finding with its code-assigned status and a small evidence summary."""
    status = verdict(indicator_fired, validation_result)
    evidence = {}
    if validation_result is not None:
        evidence = {
            "matched": getattr(validation_result, "matched", None),
            "matched_at": getattr(validation_result, "matched_at", None),
            "matcher": getattr(validation_result, "matcher_name", None),
            "error": getattr(validation_result, "error", None),
        }
    return Finding(
        endpoint=endpoint, issue=issue, indicator=indicator,
        indicator_fired=indicator_fired, validation=validation, status=status,
        tech_severity=tech_severity, business_importance=business_importance,
        evidence=evidence,
    )
