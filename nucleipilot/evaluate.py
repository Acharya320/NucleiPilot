"""Scoring a workflow run against the sandbox's INDEPENDENT ground truth.

Definitions (kept in one place so every number is defensible):
  * A "finding" = an issue the agent marks CONFIRMED.
  * TP = CONFIRMED issue that is truly present (in ground truth).
  * FP = CONFIRMED issue that is NOT truly present.
  * FN = truly-present issue that was NOT confirmed (incl. left UNVERIFIED under budget).
  * precision = TP/(TP+FP), recall = TP/(TP+FN); N/A when the denominator is 0.
Ground truth comes from the sandbox profile, never from the agent's own output.
"""
from __future__ import annotations

COND_TO_ISSUE = {"admin_auth_missing": "admin", "debug_exposed": "debug"}


def gt_issues(ground_truth_conditions) -> set:
    return {COND_TO_ISSUE[c] for c in ground_truth_conditions if c in COND_TO_ISSUE}


def score_run(run: dict, gt: set) -> dict:
    assessment = run.get("assessment", {})
    confirmed = {i for i, s in assessment.items() if s == "CONFIRMED"}
    return {
        "tp": len(confirmed & gt),
        "fp": len(confirmed - gt),
        "fn": len(gt - confirmed),
        "confirmed": sorted(confirmed),
        "assessment": assessment,
    }


def run_tokens(run: dict) -> dict:
    p = c = 0
    for e in run.get("trace", []):
        if e.get("step") == "decision":
            u = ((e.get("detail") or {}).get("raw") or {}).get("usage") or {}
            p += u.get("prompt_tokens") or 0
            c += u.get("completion_tokens") or 0
    return {"prompt_tokens": p, "completion_tokens": c}


def run_invalid_or_blocked(run: dict) -> bool:
    """True if any LLM decision produced invalid output OR the guard blocked a choice."""
    for e in run.get("trace", []):
        d = e.get("detail") or {}
        if e.get("step") == "decision" and (d.get("raw") or {}).get("error"):
            return True
        if e.get("step") == "policy" and d.get("ok") is False:
            return True
    return False


def first_decision(run: dict):
    for e in run.get("trace", []):
        if e.get("step") == "decision":
            return (e.get("detail") or {}).get("proposed")
    return None


def precision(tp, fp):
    return tp / (tp + fp) if (tp + fp) > 0 else None


def recall(tp, fn):
    return tp / (tp + fn) if (tp + fn) > 0 else None


def fmt(x):
    return "N/A" if x is None else f"{x:.2f}"
