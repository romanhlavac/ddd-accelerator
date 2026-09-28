"""Normalize authoritative HRDR comments for Governance Kernel consumers."""

from __future__ import annotations

import json
import re
from typing import Any

from runtime.platform.governance_kernel import evaluate_hrdr_binding


MARKER = "<!-- ddda:human-release-decision:v1 -->"
FENCED_JSON = re.compile(r"```json\s*(?P<json>.*?)\s*```", re.DOTALL)


def _result(
    status: str,
    *,
    failures: list[str] | None = None,
    record: Any = None,
    comment_id: Any = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": status,
        "failures": sorted(set(failures or [])),
        "record": record,
        "comment_id": comment_id,
    }


def collect_hrdr_evidence(
    comments: Any,
    *,
    allow_missing: bool = False,
    expected_repository: str | None = None,
    expected_pr: int | None = None,
    expected_source_sha: str | None = None,
    expected_package_sha256: str | None = None,
    expected_version: str | None = None,
) -> dict[str, Any]:
    if not isinstance(comments, list):
        return _result("FAIL", failures=["HRDR_COMMENTS_INVALID"])
    matches = [
        row
        for row in comments
        if isinstance(row, dict) and MARKER in str(row.get("body") or "")
    ]
    if not matches and allow_missing:
        return _result("MISSING")
    if len(matches) != 1:
        return _result("FAIL", failures=["HRDR_CARDINALITY"])

    comment = matches[0]
    match = FENCED_JSON.search(str(comment.get("body") or ""))
    if not match:
        return _result("FAIL", failures=["HRDR_JSON_INVALID"])
    try:
        record = json.loads(match.group("json"))
    except (json.JSONDecodeError, TypeError):
        return _result("FAIL", failures=["HRDR_JSON_INVALID"])
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        return _result("FAIL", failures=["HRDR_CONTRACT_INVALID"])

    decision = str(record.get("decision") or "").lower()
    user = comment.get("user")
    login = user.get("login") if isinstance(user, dict) else None
    user_type = user.get("type") if isinstance(user, dict) else None
    failures: list[str] = []
    if (
        not isinstance(login, str)
        or not login.strip()
        or not isinstance(user_type, str)
        or not user_type.strip()
    ):
        failures.append("HRDR_PROVENANCE_INVALID")
    if decision != "pending":
        human = (
            isinstance(login, str)
            and bool(login.strip())
            and user_type != "Bot"
            and not login.endswith("[bot]")
        )
        if not human or record.get("reviewer") != login or record.get("decision_owner") != login:
            failures.append("HRDR_PROVENANCE_INVALID")
    if failures:
        return _result("FAIL", failures=failures)

    expected = (
        expected_repository,
        expected_pr,
        expected_source_sha,
        expected_package_sha256,
        expected_version,
    )
    if any(value is not None for value in expected):
        if any(value is None for value in expected):
            return _result("FAIL", failures=["HRDR_EXPECTED_IDENTITY_INCOMPLETE"])
        reference = {
            "repository": record.get("repository"),
            "pr": record.get("pr"),
            "decision": decision.upper(),
            "source_sha": record.get("source_sha"),
            "candidate_package_sha256": record.get("candidate_package_sha256"),
            "version": record.get("version"),
            "decision_owner": record.get("decision_owner"),
            "decided_at": record.get("decided_at"),
            "provenance_verified": True,
        }
        context = {
            "operation": "promotion_dry_run",
            "repository": expected_repository,
            "pr": expected_pr,
            "source_sha": expected_source_sha,
            "version": expected_version,
            "validation_evidence": {"package_sha256": expected_package_sha256},
            "hrdr_reference": reference,
        }
        decision_result = evaluate_hrdr_binding(context)
        kernel_failures = list(decision_result.failure_codes)
        if kernel_failures:
            return _result("FAIL", failures=kernel_failures)

    return _result("PASS", record=record, comment_id=comment.get("id"))
