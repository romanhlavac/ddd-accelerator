"""Candidate validation evidence collection for Governance Kernel adapters.

Filesystem access and hashing live here. Semantic repository, PR, SHA and
package binding decisions are delegated to the pure Governance Kernel.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from runtime.platform.governance_kernel import evaluate_candidate_package_binding


FAILURE_MAP = {
    "VALIDATION_NOT_PASS": "CONTROLLED_CANDIDATE_VALIDATION_NOT_PASS",
    "VALIDATION_REPOSITORY_MISMATCH": "CONTROLLED_CANDIDATE_VALIDATION_REPOSITORY_MISMATCH",
    "VALIDATION_PR_MISMATCH": "CONTROLLED_CANDIDATE_VALIDATION_PR_MISMATCH",
    "VALIDATION_SOURCE_SHA_MISMATCH": "CONTROLLED_CANDIDATE_VALIDATION_SHA_MISMATCH",
    "VALIDATION_PACKAGE_SHA256_INVALID": "CONTROLLED_CANDIDATE_VALIDATION_PACKAGE_HASH_INVALID",
    "CANDIDATE_PACKAGE_MISSING": "CONTROLLED_CANDIDATE_PACKAGE_MISSING",
    "CANDIDATE_PACKAGE_SHA256_INVALID": "CONTROLLED_CANDIDATE_PACKAGE_HASH_MISMATCH",
    "CANDIDATE_PACKAGE_SHA256_MISMATCH": "CONTROLLED_CANDIDATE_PACKAGE_HASH_MISMATCH",
}


def validate_candidate_evidence(
    report: dict[str, Any],
    *,
    repository: str,
    pr_number: int,
    source_sha: str,
    package_path: Path,
) -> dict[str, Any]:
    """Collect physical evidence and evaluate its normalized package binding."""
    source = report.get("source") if isinstance(report.get("source"), dict) else {}
    package = report.get("package") if isinstance(report.get("package"), dict) else {}
    expected_hash = str(package.get("sha256") or "").lower()
    package_present = package_path.is_file()
    observed_hash = hashlib.sha256(package_path.read_bytes()).hexdigest() if package_present else None
    try:
        workflow_run_id = int(package.get("workflow_run_id") or 1)
        if workflow_run_id <= 0:
            workflow_run_id = 1
    except (TypeError, ValueError):
        workflow_run_id = 1
    candidate_context = {
        "operation": "validate",
        "repository": repository,
        "pr": pr_number,
        "source_sha": source_sha,
        "validation_evidence": {
            "status": report.get("status"),
            "repository": str(source.get("repository") or ""),
            "pr": source.get("pr"),
            "source_sha": str(source.get("commit") or ""),
            "package_sha256": expected_hash,
            "package_present": package_present,
            "observed_package_sha256": observed_hash,
            "artifact_name": str(package.get("artifact_name") or "legacy-candidate-package"),
            "workflow_run_id": workflow_run_id,
        },
    }
    decision = evaluate_candidate_package_binding(candidate_context)
    failures = [FAILURE_MAP[code] for code in decision.failure_codes if code in FAILURE_MAP]
    return {
        "status": "PASS" if not failures else "FAIL",
        "repository": repository,
        "pr": pr_number,
        "source_sha": source_sha,
        "candidate_package_sha256": expected_hash,
        "observed_package_sha256": observed_hash,
        "failures": sorted(set(failures)),
    }


def restore_candidate_evidence(
    artifact_root: Path,
    *,
    repository: str,
    pr_number: int,
    source_sha: str,
) -> dict[str, Any]:
    """Restore exactly one report-bound package from an unpacked artifact."""
    reports = sorted(path for path in artifact_root.rglob("result.json") if path.is_file())
    if len(reports) != 1:
        return {
            "status": "FAIL",
            "repository": repository,
            "pr": pr_number,
            "source_sha": source_sha,
            "failures": ["CANDIDATE_EVIDENCE_REPORT_CARDINALITY"],
        }
    report_path = reports[0]
    try:
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {
            "status": "FAIL",
            "repository": repository,
            "pr": pr_number,
            "source_sha": source_sha,
            "failures": ["CANDIDATE_EVIDENCE_REPORT_INVALID"],
        }
    package = report.get("package") if isinstance(report.get("package"), dict) else {}
    package_name = Path(str(package.get("path") or "")).name
    expected_prefix = f"ddda-candidate-pr-{pr_number}-{source_sha[:12]}-"
    if (
        not package_name.startswith(expected_prefix)
        or not package_name.lower().endswith(".zip")
    ):
        return {
            "status": "FAIL",
            "repository": repository,
            "pr": pr_number,
            "source_sha": source_sha,
            "failures": ["CANDIDATE_EVIDENCE_PACKAGE_IDENTITY_INVALID"],
        }
    packages = sorted(path for path in artifact_root.rglob(package_name) if path.is_file())
    if len(packages) != 1:
        return {
            "status": "FAIL",
            "repository": repository,
            "pr": pr_number,
            "source_sha": source_sha,
            "failures": ["CANDIDATE_EVIDENCE_PACKAGE_CARDINALITY"],
        }
    result = validate_candidate_evidence(
        report,
        repository=repository,
        pr_number=pr_number,
        source_sha=source_sha,
        package_path=packages[0],
    )
    result["validation_report_path"] = str(report_path.resolve())
    result["candidate_package_path"] = str(packages[0].resolve())
    return result
