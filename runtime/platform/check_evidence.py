"""Normalize GitHub evidence; the Governance Kernel owns check decisions."""

from __future__ import annotations

from typing import Any, Iterable

from runtime.platform.governance_kernel import evaluate_check_summary


DEFAULT_ACCEPTED_CONCLUSIONS = ("SUCCESS",)


def _normalize_check_run(row: dict[str, Any]) -> dict[str, Any]:
    app = row.get("app") if isinstance(row.get("app"), dict) else {}
    return {
        "name": row.get("name"),
        "source_sha": row.get("head_sha"),
        "status": str(row.get("status") or "UNKNOWN").upper(),
        "conclusion": str(row["conclusion"]).upper() if row.get("conclusion") is not None else None,
        "run_id": row.get("id"),
        "app_id": app.get("id"),
    }


def _normalize_commit_status(row: dict[str, Any]) -> dict[str, Any]:
    state = str(row.get("state") or "unknown").lower()
    return {
        "name": f"commit-status:{row.get('context') or ''}",
        "source_sha": row.get("sha"),
        "status": "IN_PROGRESS" if state == "pending" else "COMPLETED",
        "conclusion": None if state == "pending" else state.upper(),
        "run_id": row.get("id"),
        "app_id": None,
    }


def evaluate_check_evidence(
    check_runs: Any,
    *,
    source_sha: str,
    commit_statuses: Any = None,
    required_checks: Iterable[str] | None = None,
    ignored_checks: Iterable[str] = (),
    accepted_conclusions: Iterable[str] = DEFAULT_ACCEPTED_CONCLUSIONS,
) -> dict[str, Any]:
    """Keep all attempts until the singular kernel resolves their authority."""
    statuses = commit_statuses if isinstance(commit_statuses, list) else []
    valid_input = isinstance(check_runs, list) and all(isinstance(row, dict) for row in check_runs)
    rows = [_normalize_check_run(row) for row in check_runs] if valid_input else []
    rows.extend(_normalize_commit_status(row) for row in statuses if isinstance(row, dict))
    summary = {
        "status": "PASS" if valid_input else "FAIL",
        "source_sha": source_sha,
        "required_checks": list(required_checks) if required_checks is not None else [],
        "accepted_conclusions": [str(value).upper() for value in accepted_conclusions],
        "latest_results": rows,
    }
    ignored = set(ignored_checks)
    for row in rows:
        if row["name"] in ignored:
            row["classification"] = "NOT_APPLICABLE"
    report = evaluate_check_summary(summary, source_sha=source_sha)
    summary["status"] = report["status"]
    summary["latest_results"] = report["latest_results"]
    return {
        "schema_version": 1,
        "source_sha": source_sha,
        "required_check_set": summary["required_checks"],
        "status": report["status"],
        "gate_result": report["gate_result"],
        "failures": report["failures"],
        "summary": summary,
        "observed_check_run_count": len(check_runs) if isinstance(check_runs, list) else 0,
        "observed_commit_status_count": len(statuses),
    }
