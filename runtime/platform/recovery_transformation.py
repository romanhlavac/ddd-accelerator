"""Fail-closed authorization for intentionally transformed release-source recovery.

Exact source-merge changed-path -> result-blob equality remains the default
recovery invariant. A mismatch can be accepted only when a single live GitHub
comment contains a machine-readable human decision bound to the exact candidate
identity and to the complete set of differing paths and hashes.
"""

from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Any, Callable

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
MARKER = "<!-- ddda:recovery-transformation-decision:v1 -->"
MISMATCH_PREFIX = "RECOVERY_LEDGER_PATH_HASH_MISMATCH:PR#"

_RECORD_KEYS = {
    "schema_version",
    "kind",
    "repository",
    "pr",
    "source_sha",
    "candidate_package_sha256",
    "version",
    "reviewer",
    "decision",
    "decided_at",
    "rationale",
    "transformations",
}
_TRANSFORMATION_KEYS = {
    "source_pr",
    "primary_cr",
    "source_merge_commit_sha",
    "recovered_commit_sha",
    "path_decisions",
}
_PATH_KEYS = {
    "path",
    "source_present",
    "source_blob_sha",
    "recovered_present",
    "recovered_blob_sha",
}


def _parse_json_fence(body: str) -> dict[str, Any] | None:
    match = re.search(r"```json\s*(\{.*?\})\s*```", body, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def parse_recovery_transformation_decision_comments(
    comments: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return one exact human decision envelope or explicit invalid evidence."""
    matches = [
        row
        for row in comments
        if isinstance(row, dict) and MARKER in str(row.get("body") or "")
    ]
    if not matches:
        return None
    if len(matches) != 1:
        return {
            "status": "INVALID",
            "reason": "MULTIPLE_MARKERS",
            "marker_count": len(matches),
        }

    row = matches[0]
    record = _parse_json_fence(str(row.get("body") or ""))
    if record is None:
        return {
            "status": "INVALID",
            "reason": "MALFORMED_JSON",
            "comment_id": row.get("id"),
        }
    user = row.get("user") if isinstance(row.get("user"), dict) else {}
    return {
        "status": "PRESENT",
        "comment_id": row.get("id"),
        "comment_author": str((user or {}).get("login") or ""),
        "record": record,
    }


def augment_recovery_transformation_evidence(
    physical: dict[str, Any],
    *,
    repository: str,
    pr: int,
    token: str,
    fetch_comments: Callable[[str, str], list[Any]],
    fetch_commit_path_hashes: Callable[
        [str, str, str], dict[str, str | None] | None
    ],
) -> dict[str, Any]:
    """Attach live decision and exact hash maps without changing base invariants."""
    ledger = physical.get("recovery_ledger")
    if not isinstance(ledger, dict):
        return physical

    comments = fetch_comments(f"repos/{repository}/issues/{pr}/comments", token)
    physical["recovery_transformation_decision"] = (
        parse_recovery_transformation_decision_comments(
            [row for row in comments if isinstance(row, dict)]
        )
    )

    entries = ledger.get("entries")
    if not isinstance(entries, list):
        return physical
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("changed_path_hashes_match") is True:
            continue
        source_sha = str(entry.get("source_merge_commit_sha") or "")
        recovered_sha = str(entry.get("recovered_commit_sha") or "")
        entry["source_path_hashes"] = (
            fetch_commit_path_hashes(repository, source_sha, token)
            if SHA40.fullmatch(source_sha)
            else None
        )
        entry["recovered_path_hashes"] = (
            fetch_commit_path_hashes(repository, recovered_sha, token)
            if SHA40.fullmatch(recovered_sha)
            else None
        )
    return physical


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _valid_path_map(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    for path, blob in value.items():
        if not isinstance(path, str) or not path:
            return False
        if blob is not None and not SHA40.fullmatch(str(blob)):
            return False
    return True


def path_hash_differences(
    source: dict[str, str | None], recovered: dict[str, str | None]
) -> list[dict[str, Any]]:
    """Return the complete canonical difference set for two changed-path maps."""
    rows: list[dict[str, Any]] = []
    for path in sorted(set(source) | set(recovered)):
        source_present = path in source
        recovered_present = path in recovered
        source_blob = source.get(path) if source_present else None
        recovered_blob = recovered.get(path) if recovered_present else None
        if source_present == recovered_present and source_blob == recovered_blob:
            continue
        rows.append(
            {
                "path": path,
                "source_present": source_present,
                "source_blob_sha": source_blob,
                "recovered_present": recovered_present,
                "recovered_blob_sha": recovered_blob,
            }
        )
    return rows


def _record_shape_failures(record: Any) -> list[str]:
    failures: list[str] = []
    if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
        return ["RECOVERY_TRANSFORMATION_DECISION_RECORD_SHAPE"]
    if record.get("schema_version") != 1:
        failures.append("RECOVERY_TRANSFORMATION_DECISION_SCHEMA_VERSION")
    if record.get("kind") != "recovery_transformation_decision":
        failures.append("RECOVERY_TRANSFORMATION_DECISION_KIND")
    if not isinstance(record.get("repository"), str) or "/" not in str(
        record.get("repository")
    ):
        failures.append("RECOVERY_TRANSFORMATION_DECISION_REPOSITORY")
    try:
        if int(record.get("pr", 0)) <= 0:
            failures.append("RECOVERY_TRANSFORMATION_DECISION_PR")
    except (TypeError, ValueError):
        failures.append("RECOVERY_TRANSFORMATION_DECISION_PR")
    if not SHA40.fullmatch(str(record.get("source_sha") or "")):
        failures.append("RECOVERY_TRANSFORMATION_DECISION_SOURCE_SHA")
    if not SHA256.fullmatch(str(record.get("candidate_package_sha256") or "")):
        failures.append("RECOVERY_TRANSFORMATION_DECISION_PACKAGE_SHA256")
    if not SEMVER.fullmatch(str(record.get("version") or "")):
        failures.append("RECOVERY_TRANSFORMATION_DECISION_VERSION")
    if not str(record.get("reviewer") or "").strip():
        failures.append("RECOVERY_TRANSFORMATION_DECISION_REVIEWER")
    if record.get("decision") != "approve":
        failures.append("RECOVERY_TRANSFORMATION_DECISION_NOT_APPROVED")
    if not _valid_timestamp(record.get("decided_at")):
        failures.append("RECOVERY_TRANSFORMATION_DECISION_DECIDED_AT")
    if not str(record.get("rationale") or "").strip():
        failures.append("RECOVERY_TRANSFORMATION_DECISION_RATIONALE")

    transformations = record.get("transformations")
    if not isinstance(transformations, list) or not transformations:
        failures.append("RECOVERY_TRANSFORMATION_DECISION_TRANSFORMATIONS")
        return sorted(set(failures))

    seen_prs: set[int] = set()
    for row in transformations:
        if not isinstance(row, dict) or set(row) != _TRANSFORMATION_KEYS:
            failures.append("RECOVERY_TRANSFORMATION_DECISION_TRANSFORMATION_SHAPE")
            continue
        try:
            source_pr = int(row.get("source_pr", 0))
            primary_cr = int(row.get("primary_cr", 0))
        except (TypeError, ValueError):
            source_pr = primary_cr = 0
        if source_pr <= 0 or source_pr in seen_prs:
            failures.append("RECOVERY_TRANSFORMATION_DECISION_SOURCE_PR")
        seen_prs.add(source_pr)
        if primary_cr <= 0:
            failures.append("RECOVERY_TRANSFORMATION_DECISION_PRIMARY_CR")
        if not SHA40.fullmatch(str(row.get("source_merge_commit_sha") or "")):
            failures.append("RECOVERY_TRANSFORMATION_DECISION_SOURCE_MERGE_SHA")
        if not SHA40.fullmatch(str(row.get("recovered_commit_sha") or "")):
            failures.append("RECOVERY_TRANSFORMATION_DECISION_RECOVERED_SHA")
        paths = row.get("path_decisions")
        if not isinstance(paths, list) or not paths:
            failures.append("RECOVERY_TRANSFORMATION_DECISION_PATHS")
            continue
        seen_paths: set[str] = set()
        for decision in paths:
            if not isinstance(decision, dict) or set(decision) != _PATH_KEYS:
                failures.append("RECOVERY_TRANSFORMATION_DECISION_PATH_SHAPE")
                continue
            path = str(decision.get("path") or "")
            if not path or path in seen_paths:
                failures.append("RECOVERY_TRANSFORMATION_DECISION_PATH")
            seen_paths.add(path)
            for prefix in ("source", "recovered"):
                present = decision.get(f"{prefix}_present")
                blob = decision.get(f"{prefix}_blob_sha")
                if not isinstance(present, bool):
                    failures.append("RECOVERY_TRANSFORMATION_DECISION_PATH_PRESENCE")
                if blob is not None and not SHA40.fullmatch(str(blob)):
                    failures.append("RECOVERY_TRANSFORMATION_DECISION_PATH_HASH")
                if present is False and blob is not None:
                    failures.append("RECOVERY_TRANSFORMATION_DECISION_ABSENT_PATH_HASH")
    return sorted(set(failures))


def _mismatch_prs(failures: tuple[str, ...]) -> set[int]:
    result: set[int] = set()
    for failure in failures:
        if failure.startswith(MISMATCH_PREFIX):
            suffix = failure[len(MISMATCH_PREFIX) :]
            if suffix.isdigit():
                result.add(int(suffix))
    return result


def _decision_failures(
    physical: dict[str, Any],
    mismatch_prs: set[int],
    *,
    expected_repository: str,
    expected_pr: int,
    expected_source_sha: str,
    expected_package_sha256: str,
    expected_version: str,
    expected_decision_owner: str,
) -> list[str]:
    evidence = physical.get("recovery_transformation_decision")
    if evidence is None:
        return []
    if not isinstance(evidence, dict) or evidence.get("status") != "PRESENT":
        reason = (
            str((evidence or {}).get("reason") or "EVIDENCE_INVALID")
            if isinstance(evidence, dict)
            else "EVIDENCE_INVALID"
        )
        return [f"RECOVERY_TRANSFORMATION_DECISION_INVALID:{reason}"]

    record = evidence.get("record")
    failures = _record_shape_failures(record)
    if failures or not isinstance(record, dict):
        return failures or ["RECOVERY_TRANSFORMATION_DECISION_INVALID"]

    if record.get("repository") != expected_repository:
        failures.append("RECOVERY_TRANSFORMATION_DECISION_REPOSITORY_MISMATCH")
    if int(record.get("pr", 0)) != int(expected_pr):
        failures.append("RECOVERY_TRANSFORMATION_DECISION_PR_MISMATCH")
    if record.get("source_sha") != expected_source_sha:
        failures.append("RECOVERY_TRANSFORMATION_DECISION_SOURCE_SHA_MISMATCH")
    if record.get("candidate_package_sha256") != expected_package_sha256:
        failures.append("RECOVERY_TRANSFORMATION_DECISION_PACKAGE_SHA256_MISMATCH")
    if record.get("version") != expected_version:
        failures.append("RECOVERY_TRANSFORMATION_DECISION_VERSION_MISMATCH")

    author = str(evidence.get("comment_author") or "")
    reviewer = str(record.get("reviewer") or "")
    if not author or author != reviewer:
        failures.append("RECOVERY_TRANSFORMATION_DECISION_AUTHOR_MISMATCH")
    if author.casefold().endswith("[bot]"):
        failures.append("RECOVERY_TRANSFORMATION_DECISION_BOT_AUTHOR")
    if not expected_decision_owner or reviewer != expected_decision_owner:
        failures.append("RECOVERY_TRANSFORMATION_DECISION_AUTHORITY_MISMATCH")

    ledger = physical.get("recovery_ledger")
    entries = ledger.get("entries") if isinstance(ledger, dict) else None
    if not isinstance(entries, list):
        failures.append("RECOVERY_TRANSFORMATION_DECISION_LEDGER_EVIDENCE")
        return sorted(set(failures))

    mismatch_entries: dict[int, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("changed_path_hashes_match") is True:
            continue
        try:
            source_pr = int(entry.get("source_pr", 0))
        except (TypeError, ValueError):
            source_pr = 0
        if source_pr <= 0 or source_pr in mismatch_entries:
            failures.append("RECOVERY_TRANSFORMATION_DECISION_LEDGER_IDENTITY")
            continue
        mismatch_entries[source_pr] = entry

    if set(mismatch_entries) != mismatch_prs:
        failures.append("RECOVERY_TRANSFORMATION_DECISION_MISMATCH_SET")

    transformations = record.get("transformations")
    by_pr: dict[int, dict[str, Any]] = {}
    if isinstance(transformations, list):
        for row in transformations:
            if not isinstance(row, dict):
                continue
            try:
                number = int(row.get("source_pr", 0))
            except (TypeError, ValueError):
                continue
            if number > 0:
                by_pr[number] = row
    if set(by_pr) != mismatch_prs:
        failures.append("RECOVERY_TRANSFORMATION_DECISION_UNUSED_OR_MISSING_TRANSFORMATION")

    for source_pr in sorted(mismatch_prs):
        entry = mismatch_entries.get(source_pr)
        transform = by_pr.get(source_pr)
        if not isinstance(entry, dict) or not isinstance(transform, dict):
            continue
        if transform.get("primary_cr") != entry.get("primary_cr"):
            failures.append(
                f"RECOVERY_TRANSFORMATION_DECISION_PRIMARY_CR_MISMATCH:PR#{source_pr}"
            )
        if transform.get("source_merge_commit_sha") != entry.get(
            "source_merge_commit_sha"
        ):
            failures.append(
                f"RECOVERY_TRANSFORMATION_DECISION_SOURCE_MERGE_MISMATCH:PR#{source_pr}"
            )
        if transform.get("recovered_commit_sha") != entry.get(
            "recovered_commit_sha"
        ):
            failures.append(
                f"RECOVERY_TRANSFORMATION_DECISION_RECOVERED_COMMIT_MISMATCH:PR#{source_pr}"
            )

        source_map = entry.get("source_path_hashes")
        recovered_map = entry.get("recovered_path_hashes")
        if not _valid_path_map(source_map) or not _valid_path_map(recovered_map):
            failures.append(
                f"RECOVERY_TRANSFORMATION_DECISION_PATH_EVIDENCE_INVALID:PR#{source_pr}"
            )
            continue
        actual = path_hash_differences(source_map, recovered_map)
        declared = transform.get("path_decisions")
        if not isinstance(declared, list):
            failures.append(
                f"RECOVERY_TRANSFORMATION_DECISION_PATHS_INVALID:PR#{source_pr}"
            )
            continue
        declared_sorted = sorted(
            declared,
            key=lambda row: str(row.get("path") or "")
            if isinstance(row, dict)
            else "",
        )
        if declared_sorted != actual:
            failures.append(
                f"RECOVERY_TRANSFORMATION_DECISION_PATH_HASH_MISMATCH:PR#{source_pr}"
            )
    return sorted(set(failures))


def apply_recovery_transformation_decision(
    result: Any,
    snapshot: dict[str, Any],
    *,
    expected_repository: str,
    expected_pr: int,
    expected_source_sha: str,
    expected_package_sha256: str,
    expected_version: str,
    expected_decision_owner: str,
) -> Any:
    """Authorize only exact mismatches covered by one exact human record."""
    physical = snapshot.get("physical_scope")
    if not isinstance(physical, dict):
        return result
    mismatch_prs = _mismatch_prs(result.failures)
    evidence_present = physical.get("recovery_transformation_decision") is not None
    if not mismatch_prs and not evidence_present:
        return result

    decision_failures = _decision_failures(
        physical,
        mismatch_prs,
        expected_repository=expected_repository,
        expected_pr=expected_pr,
        expected_source_sha=expected_source_sha,
        expected_package_sha256=expected_package_sha256,
        expected_version=expected_version,
        expected_decision_owner=expected_decision_owner,
    )
    if not mismatch_prs and evidence_present:
        decision_failures.append("RECOVERY_TRANSFORMATION_DECISION_UNUSED")

    failures = list(result.failures)
    if mismatch_prs and evidence_present and not decision_failures:
        failures = [
            failure
            for failure in failures
            if not (
                failure.startswith(MISMATCH_PREFIX)
                and failure[len(MISMATCH_PREFIX) :].isdigit()
                and int(failure[len(MISMATCH_PREFIX) :]) in mismatch_prs
            )
        ]
    else:
        failures.extend(decision_failures)

    normalized = tuple(sorted(set(failures)))
    return type(result)(
        status="PASS" if not normalized else "FAIL",
        failures=normalized,
        scope_issues=result.scope_issues,
        accepted_risk_issues=result.accepted_risk_issues,
        side_effects_allowed=not normalized,
    )
