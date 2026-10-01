"""Versioned primary classification for governance and projection mismatches."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_PATH = ROOT / "config/governance/mismatch-taxonomy-v1.json"


@lru_cache(maxsize=1)
def _taxonomy() -> dict[str, Any]:
    return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))


def classify_mismatch(code: str) -> dict[str, str]:
    """Return one primary category; unknown codes fail closed as safety blocking."""
    full_code = str(code or "UNKNOWN_MISMATCH")
    value = full_code.split(":", 1)[0]
    taxonomy = _taxonomy()
    matches = [(prefix, category) for prefix, category in taxonomy["prefix_categories"].items() if value.startswith(prefix)]
    category = max(matches, key=lambda pair: len(pair[0]))[1] if matches else taxonomy["default_category"]
    semantics = taxonomy["categories"][category]
    return {"code": full_code, "primary_category": category, "authority": semantics["authority"], "side_effect": semantics["side_effect"]}


def classify_result(result: str) -> list[dict[str, str]]:
    """Classify each code in the existing plus-delimited audit representation."""
    if not result or result == "PASS":
        return []
    return [classify_mismatch(code) for code in result.split("+") if code]
