"""Emergency-only controlled-recovery compatibility evaluator.

The standard release evaluator deliberately does not import this module or
inspect recovery evidence. Callers must select this adapter explicitly.
"""

from __future__ import annotations

from typing import Any
import re

try:
    from .governance_kernel import evaluate_promotion_readiness
    from .recovery_transformation import apply_recovery_transformation_decision
    from .release_governance import GovernanceResult, evaluate_release_scope
except ImportError:  # direct script/runtime path import
    from governance_kernel import evaluate_promotion_readiness
    from recovery_transformation import apply_recovery_transformation_decision
    from release_governance import GovernanceResult, evaluate_release_scope


SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _sha_values(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values if SHA40.fullmatch(str(value))}


def evaluate_recovery_ledger(
    physical: dict[str, Any],
    *,
    expected_version: str,
    declared_scope: set[int],
) -> list[str]:
    """Validate historical v1 and current v2 controlled-recovery provenance."""
    ledger = physical.get("recovery_ledger")
    if ledger is None:
        return ["RECOVERY_LEDGER_REQUIRED"]
    if not isinstance(ledger, dict):
        return ["RECOVERY_LEDGER_EVIDENCE_INVALID"]

    failures: list[str] = []
    schema_version = ledger.get("schema_version")
    if schema_version not in {1, 2}:
        failures.append("RECOVERY_LEDGER_SCHEMA_VERSION")
    if ledger.get("version") != expected_version:
        failures.append("RECOVERY_LEDGER_VERSION_MISMATCH")
    if ledger.get("previous_release_tag") != physical.get("previous_release_tag"):
        failures.append("RECOVERY_LEDGER_PREVIOUS_TAG_MISMATCH")

    physical_commits = _sha_values(physical.get("commit_shas"))
    if not physical_commits:
        failures.append("RECOVERY_LEDGER_PHYSICAL_COMMIT_EVIDENCE_MISSING")

    if "metadata_commit_shas" in ledger:
        metadata = _sha_values(ledger.get("metadata_commit_shas"))
    else:
        metadata = _sha_values(physical.get("metadata_commit_shas"))
    expected_metadata_count = 2 if schema_version == 2 else 1
    if len(metadata) != expected_metadata_count or not metadata.issubset(physical_commits):
        failures.append("RECOVERY_LEDGER_METADATA_COMMIT_INVALID")

    if schema_version == 2:
        release_cut = ledger.get("release_cut")
        if not isinstance(release_cut, dict):
            failures.append("RECOVERY_LEDGER_RELEASE_CUT_EVIDENCE_MISSING")
        else:
            release_cut_sha = str(release_cut.get("commit_sha") or "")
            if not SHA40.fullmatch(release_cut_sha) or release_cut_sha not in metadata:
                failures.append("RECOVERY_LEDGER_RELEASE_CUT_COMMIT_INVALID")
            if release_cut.get("path") != "CHANGELOG.md":
                failures.append("RECOVERY_LEDGER_RELEASE_CUT_PATH_INVALID")
            if release_cut.get("version") != expected_version:
                failures.append("RECOVERY_LEDGER_RELEASE_CUT_VERSION_MISMATCH")
            if release_cut.get("changed_paths_match") is not True:
                failures.append("RECOVERY_LEDGER_RELEASE_CUT_PATHS_MISMATCH")
            if release_cut.get("source_blob_matches") is not True:
                failures.append("RECOVERY_LEDGER_RELEASE_CUT_SOURCE_BLOB_MISMATCH")
            if release_cut.get("release_blob_matches") is not True:
                failures.append("RECOVERY_LEDGER_RELEASE_CUT_RESULT_BLOB_MISMATCH")
            ordered_commits = [
                str(value)
                for value in physical.get("commit_shas", [])
                if SHA40.fullmatch(str(value))
            ]
            if (
                len(ordered_commits) < 2
                or ordered_commits[-2] != release_cut_sha
                or ordered_commits[-1] == release_cut_sha
                or ordered_commits[-1] not in metadata
            ):
                failures.append("RECOVERY_LEDGER_RELEASE_CUT_SEQUENCE_INVALID")

    entries = ledger.get("entries")
    if not isinstance(entries, list) or not entries:
        return sorted(set(failures + ["RECOVERY_LEDGER_ENTRIES_INVALID"]))

    recovered: set[str] = set()
    source_prs: set[int] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            failures.append("RECOVERY_LEDGER_ENTRY_SHAPE")
            continue
        recovered_sha = str(entry.get("recovered_commit_sha") or "")
        if not SHA40.fullmatch(recovered_sha) or recovered_sha in recovered:
            failures.append("RECOVERY_LEDGER_RECOVERED_COMMIT_INVALID")
            continue
        recovered.add(recovered_sha)
        try:
            source_pr = int(entry.get("source_pr", 0))
            primary_cr = int(entry.get("primary_cr", 0))
        except (TypeError, ValueError):
            source_pr = primary_cr = 0
        if source_pr <= 0 or source_pr in source_prs:
            failures.append("RECOVERY_LEDGER_SOURCE_PR_INVALID")
        source_prs.add(source_pr)
        if primary_cr <= 0:
            failures.append("RECOVERY_LEDGER_PRIMARY_CR_INVALID")
        if entry.get("source_pr_merged") is not True:
            failures.append(f"RECOVERY_LEDGER_SOURCE_PR_NOT_MERGED:PR#{source_pr}")
        if entry.get("source_primary_crs") != [primary_cr]:
            failures.append(f"RECOVERY_LEDGER_SOURCE_PRIMARY_CR_MISMATCH:PR#{source_pr}")
        if entry.get("source_merge_commit_sha") != entry.get("observed_source_merge_commit_sha"):
            failures.append(f"RECOVERY_LEDGER_SOURCE_MERGE_SHA_MISMATCH:PR#{source_pr}")
        if entry.get("changed_path_hashes_match") is not True:
            failures.append(f"RECOVERY_LEDGER_PATH_HASH_MISMATCH:PR#{source_pr}")
        if primary_cr not in declared_scope:
            failures.append(f"RECOVERY_LEDGER_OUT_OF_SCOPE_PRIMARY_CR:PR#{source_pr}:#{primary_cr}")

    if recovered & metadata:
        failures.append("RECOVERY_LEDGER_COMMIT_ROLE_OVERLAP")
    if recovered | metadata != physical_commits:
        failures.append("RECOVERY_LEDGER_COMMIT_COVERAGE_MISMATCH")
    return sorted(set(failures))


def evaluate_emergency_recovery_scope(
    record: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    expected_repository: str,
    expected_pr: int,
    expected_source_sha: str,
    expected_package_sha256: str,
    expected_version: str,
) -> GovernanceResult:
    """Evaluate controlled recovery only after explicit emergency routing."""
    standard = evaluate_release_scope(
        record,
        snapshot,
        expected_repository=expected_repository,
        expected_pr=expected_pr,
        expected_source_sha=expected_source_sha,
        expected_package_sha256=expected_package_sha256,
        expected_version=expected_version,
    )
    physical = snapshot.get("physical_scope")
    ledger_failures = evaluate_recovery_ledger(
        physical if isinstance(physical, dict) else {},
        expected_version=expected_version,
        declared_scope=set(standard.scope_issues),
    )
    combined = tuple(sorted(set(standard.failures) | set(ledger_failures)))
    recovery_input = GovernanceResult(
        status="PASS" if not combined else "FAIL",
        failures=combined,
        scope_issues=standard.scope_issues,
        accepted_risk_issues=standard.accepted_risk_issues,
        side_effects_allowed=not combined,
    )
    transformed = apply_recovery_transformation_decision(
        recovery_input,
        snapshot,
        expected_repository=expected_repository,
        expected_pr=expected_pr,
        expected_source_sha=expected_source_sha,
        expected_package_sha256=expected_package_sha256,
        expected_version=expected_version,
        expected_decision_owner=str(record.get("decision_owner") or ""),
    )
    readiness = evaluate_promotion_readiness(
        transformed.failures,
        operation="release_scope_validation",
    )
    return GovernanceResult(
        status=readiness.status,
        failures=readiness.failure_codes,
        scope_issues=transformed.scope_issues,
        accepted_risk_issues=transformed.accepted_risk_issues,
        side_effects_allowed=readiness.status == "PASS",
    )
