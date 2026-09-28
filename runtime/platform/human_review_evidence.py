"""Normalize one human-authored implementation review for Governance Kernel use.

GitHub/network acquisition stays in the calling adapter.  This collector owns
authoritative marker cardinality, JSON parsing and human provenance
normalization; exact candidate binding is delegated to the pure kernel.
"""

from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Any

from runtime.platform.governance_kernel import evaluate_human_review_binding


MARKER = "<!-- ddda:human-pr-review:v1 -->"
FENCED_JSON = re.compile(r"```json\s*(?P<json>\{.*?\})\s*```", re.DOTALL)


def _failure(*codes: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "FAIL",
        "failures": sorted(set(codes)),
        "review": None,
        "comment_id": None,
    }


def _parse_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def collect_human_review_evidence(
    comments: Any,
    *,
    repository: str,
    pr_number: int,
    source_sha: str,
    candidate_package_sha256: str,
) -> dict[str, Any]:
    if not isinstance(comments, list):
        return _failure("HUMAN_REVIEW_COMMENTS_INVALID")
    matches = [
        row
        for row in comments
        if isinstance(row, dict) and MARKER in str(row.get("body") or "")
    ]
    if len(matches) != 1:
        return _failure("HUMAN_REVIEW_CARDINALITY")

    comment = matches[0]
    match = FENCED_JSON.search(str(comment.get("body") or ""))
    if not match:
        return _failure("HUMAN_REVIEW_JSON_INVALID")
    try:
        record = json.loads(match.group("json"))
    except (json.JSONDecodeError, TypeError):
        return _failure("HUMAN_REVIEW_JSON_INVALID")
    if not isinstance(record, dict):
        return _failure("HUMAN_REVIEW_JSON_INVALID")

    failures: list[str] = []
    if record.get("schema_version") != 1 or record.get("kind") != "implementation_pr_review":
        failures.append("HUMAN_REVIEW_CONTRACT_INVALID")

    user = comment.get("user")
    login = user.get("login") if isinstance(user, dict) else None
    user_type = user.get("type") if isinstance(user, dict) else None
    reviewer = record.get("reviewer")
    provenance_verified = (
        isinstance(login, str)
        and bool(login.strip())
        and isinstance(user_type, str)
        and bool(user_type.strip())
        and user_type != "Bot"
        and not login.endswith("[bot]")
        and reviewer == login
    )
    if not provenance_verified:
        failures.append("HUMAN_REVIEW_PROVENANCE_INVALID")
    if not _parse_timestamp(record.get("reviewed_at")):
        failures.append("HUMAN_REVIEW_IDENTITY_INVALID")
    if failures:
        return _failure(*failures)

    review = {
        "repository": record.get("repository"),
        "pr": record.get("pr"),
        "verdict": str(record.get("verdict") or "").upper(),
        "reviewed_sha": record.get("reviewed_sha"),
        "candidate_package_sha256": record.get("candidate_package_sha256"),
        "reviewer": reviewer,
        "reviewed_at": record.get("reviewed_at"),
        "provenance_verified": True,
    }
    context = {
        "operation": "merge_dry_run",
        "repository": repository,
        "pr": pr_number,
        "source_sha": source_sha,
        "validation_evidence": {"package_sha256": candidate_package_sha256},
        "human_review_reference": review,
    }
    decision = evaluate_human_review_binding(context)
    return {
        "schema_version": 1,
        "status": decision.status,
        "failures": list(decision.failure_codes),
        "review": review,
        "comment_id": comment.get("id"),
    }
