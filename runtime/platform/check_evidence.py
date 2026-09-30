"""Normalize GitHub check evidence for Governance Kernel consumers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from runtime.platform.governance_kernel import evaluate_authoritative_checks


DEFAULT_ACCEPTED_CONCLUSIONS = ("SUCCESS", "NEUTRAL", "SKIPPED")


def _timestamp(value: Any, *, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"CHECK_TIMESTAMP_MISSING:{name}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"CHECK_TIMESTAMP_INVALID:{name}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"CHECK_TIMESTAMP_INVALID:{name}")
    return parsed


def _latest_by_name(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, tuple[datetime, int, dict[str, Any]]] = {}
    for row in rows:
        name = str(row.get("name") or "")
        if not name:
            raise ValueError("CHECK_NAME_MISSING")
        try:
            run_id = int(row.get("id", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"CHECK_RUN_ID_INVALID:{name}") from exc
        if run_id <= 0:
            raise ValueError(f"CHECK_RUN_ID_INVALID:{name}")
        key = (_timestamp(row.get("started_at"), name=name), run_id)
        current = selected.get(name)
        if current is None or key > current[:2]:
            selected[name] = (key[0], key[1], row)
    return [selected[name][2] for name in sorted(selected)]


def _normalize_check_run(row: dict[str, Any]) -> dict[str, Any]:
    raw_status = str(row.get("status") or "").lower()
    status = (
        "COMPLETED"
        if raw_status == "completed"
        else "IN_PROGRESS" if raw_status == "in_progress" else "QUEUED"
    )
    return {
        "name": str(row.get("name")),
        "status": status,
        "conclusion": (
            str(row.get("conclusion")).upper()
            if row.get("conclusion") is not None
            else None
        ),
        "run_id": int(row.get("id")),
    }


def _normalize_commit_statuses(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    check_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        state = str(row.get("state") or "").lower()
        check_rows.append(
            {
                "name": f"commit-status:{str(row.get('context') or '')}",
                "id": row.get("id"),
                "started_at": row.get("updated_at") or row.get("created_at"),
                "status": "completed" if state != "pending" else "in_progress",
                "conclusion": "success" if state == "success" else (
                    None if state == "pending" else "failure"
                ),
            }
        )
    return check_rows


def evaluate_check_evidence(
    check_runs: Any,
    *,
    commit_statuses: Any = None,
    required_checks: Iterable[str] | None = None,
    ignored_checks: Iterable[str] = (),
    accepted_conclusions: Iterable[str] = DEFAULT_ACCEPTED_CONCLUSIONS,
) -> dict[str, Any]:
    """Select latest evidence by name and submit the required set to the kernel."""
    if not isinstance(check_runs, list):
        return {
            "schema_version": 1,
            "status": "FAIL",
            "failures": ["CHECK_RUNS_INVALID"],
            "summary": None,
            "observed_check_run_count": 0,
            "observed_commit_status_count": 0,
        }
    statuses = commit_statuses if isinstance(commit_statuses, list) else []
    combined = [row for row in check_runs if isinstance(row, dict)]
    combined.extend(_normalize_commit_statuses(statuses))
    ignored = {str(name) for name in ignored_checks}
    try:
        latest = [
            _normalize_check_run(row)
            for row in _latest_by_name(combined)
            if str(row.get("name")) not in ignored
        ]
    except ValueError as exc:
        return {
            "schema_version": 1,
            "status": "FAIL",
            "failures": [str(exc)],
            "summary": None,
            "observed_check_run_count": len(check_runs),
            "observed_commit_status_count": len(statuses),
        }

    required = (
        sorted({str(name) for name in required_checks if str(name) not in ignored})
        if required_checks is not None
        else [row["name"] for row in latest]
    )
    accepted = sorted({str(value).upper() for value in accepted_conclusions})
    summary = {
        "status": "PASS" if combined else "MISSING",
        "required_checks": required,
        "accepted_conclusions": accepted,
        "latest_results": latest,
    }
    decision = evaluate_authoritative_checks(
        {"operation": "merge_dry_run", "authoritative_check_summary": summary}
    )
    return {
        "schema_version": 1,
        "status": decision.status,
        "failures": list(decision.failure_codes),
        "summary": summary,
        "observed_check_run_count": len(check_runs),
        "observed_commit_status_count": len(statuses),
    }
