"""Asset registry: the authorized-targets + per-endpoint business-context seam.

This is a thin, data-driven loader over config/asset_registry.json. It answers
three questions the engine needs:
  * what are we allowed to scan (scope), and
  * how important is each endpoint to the business (per endpoint, set by a human),
  * what is the validation budget for a target.

Business importance lives HERE, never in the scanner -- the scanner never guesses
how much an endpoint matters. Adding a future authorized target is one more entry
in the JSON, not a code change (the generalization seam).
"""
from __future__ import annotations

import json
import os

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(_REPO, "config")
ASSET_REGISTRY_PATH = os.path.join(CONFIG_DIR, "asset_registry.json")

# Ordered so "more important" compares greater; used by the context-aware rule (B2).
IMPORTANCE_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def load_registry(path: str = ASSET_REGISTRY_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def get_asset(registry: dict, asset_id: str) -> dict:
    for a in registry.get("assets", []):
        if a.get("id") == asset_id:
            return a
    raise KeyError(f"asset {asset_id!r} is not in the registry")


def endpoints(asset: dict) -> dict:
    return asset.get("endpoints", {})


def budget(asset: dict) -> int:
    return int(asset.get("budget", 0))


def business_importance(asset: dict, endpoint: str) -> str | None:
    ep = asset.get("endpoints", {}).get(endpoint)
    return ep.get("business_importance") if ep else None


def importance_rank(importance: str | None) -> int:
    """Numeric rank for ordering; unknown/None sorts lowest."""
    return IMPORTANCE_RANK.get((importance or "").lower(), 0)


def catalog_path(asset: dict) -> str:
    """The approved catalog file for an asset (each asset names its own catalog)."""
    return os.path.join(CONFIG_DIR, asset.get("catalog", "catalog.json"))
