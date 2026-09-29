#!/usr/bin/env python3
"""Fail-closed selection contract for controlled release-candidate operations."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.platform.candidate_evidence import validate_candidate_evidence
from runtime.platform.governance_kernel import evaluate_candidate_identity

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
OPERATIONS = frozenset(
    {"technical_validation", "publish_hrdr_scaffold", "release_scope_dry_run", "promotion_dry_run"}
)


def validate_request(
    pr: dict[str, Any], *, repository: str, pr_number: int, source_sha: str, version: str, operation: str
) -> dict[str, Any]:
    failures: list[str] = []
    head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
    base = pr.get("base") if isinstance(pr.get("base"), dict) else {}
    head_repo = head.get("repo") if isinstance(head.get("repo"), dict) else {}
    expected_ref = f"release/{version}-controlled-recovery-source"
    actual_ref = str(head.get("ref") or "")
    generation_match = re.search(r"-v(?P<generation>[1-9]\d*)$", actual_ref)
    generation = int(generation_match.group("generation")) if generation_match else 1
    if pr.get("state") != "open":
        pr_state = "MERGED_CLOSED"
    elif pr.get("draft") is True:
        pr_state = "DRAFT"
    elif pr.get("draft") is False:
        pr_state = "READY"
    else:
        pr_state = "UNKNOWN"

    kernel_operation = {
        "technical_validation": "validate",
        "publish_hrdr_scaffold": "publish_hrdr_scaffold",
        "release_scope_dry_run": "release_scope_validation",
        "promotion_dry_run": "promotion_dry_run",
    }.get(operation, operation)
    normalized_sha = source_sha if SHA_RE.fullmatch(source_sha) else "0" * 40
    candidate_context = {
        "schema_version": 1,
        "context_kind": "ddda_candidate_context",
        "candidate_kind": "RECOVERY",
        "release_mode": "CONTROLLED_RECOVERY",
        "operation": kernel_operation,
        "repository": repository,
        "pr": pr_number,
        "base_branch": str(base.get("ref") or ""),
        "source_branch": actual_ref,
        "source_sha": source_sha,
        "version": version,
        "generation": generation,
        "pr_state": pr_state,
        "validation_evidence": {
            "status": "MISSING",
            "repository": repository,
            "pr": pr_number,
            "source_sha": normalized_sha,
            "package_sha256": "0" * 64,
            "package_present": False,
            "observed_package_sha256": None,
            "artifact_name": "not-restored",
            "workflow_run_id": 1,
        },
        "authoritative_check_summary": {
            "status": "MISSING",
            "required_checks": [],
            "latest_results": [],
        },
        "human_review_reference": None,
        "hrdr_reference": None,
        "physical_scope_reference": None,
        "project_evidence_reference": None,
    }
    decision = evaluate_candidate_identity(candidate_context)
    failure_map = {
        "OPERATION_INVALID": "CONTROLLED_CANDIDATE_OPERATION_INVALID",
        "VERSION_INVALID": "CONTROLLED_CANDIDATE_VERSION_INVALID",
        "RECOVERY_VERSION_INVALID": "CONTROLLED_CANDIDATE_VERSION_INVALID",
        "SOURCE_SHA_INVALID": "CONTROLLED_CANDIDATE_SOURCE_SHA_INVALID",
        "BASE_BRANCH_INVALID": "CONTROLLED_CANDIDATE_BASE_INVALID",
        "SOURCE_BRANCH_INVALID": "CONTROLLED_CANDIDATE_BRANCH_INVALID",
        "RECOVERY_BRANCH_INVALID": "CONTROLLED_CANDIDATE_BRANCH_INVALID",
        "CANDIDATE_MUST_BE_OPEN": "CONTROLLED_CANDIDATE_MUST_REMAIN_OPEN",
        "RECOVERY_PREPARATION_REQUIRES_DRAFT": "CONTROLLED_CANDIDATE_MUST_REMAIN_OPEN_DRAFT",
        "RECOVERY_DRY_RUN_REQUIRES_READY": "CONTROLLED_CANDIDATE_SCOPE_DRY_RUN_REQUIRES_READY",
    }
    for code in decision.failure_codes:
        mapped = failure_map.get(code)
        if mapped:
            failures.append(mapped)
        elif code == "PR_STATE_INVALID":
            failures.append(
                "CONTROLLED_CANDIDATE_SCOPE_DRY_RUN_REQUIRES_READY"
                if operation in {"release_scope_dry_run", "promotion_dry_run"}
                else "CONTROLLED_CANDIDATE_MUST_REMAIN_OPEN_DRAFT"
            )
    if int(pr.get("number") or -1) != pr_number:
        failures.append("CONTROLLED_CANDIDATE_PR_IDENTITY_INVALID")
    if str(head.get("sha") or "") != source_sha:
        failures.append("CONTROLLED_CANDIDATE_HEAD_SHA_MISMATCH")
    if str(head_repo.get("full_name") or "") != repository:
        failures.append("CONTROLLED_CANDIDATE_HEAD_REPOSITORY_INVALID")
    body = str(pr.get("body") or "")
    if f"Controlled release-source candidate — DDDA {version}" not in body:
        failures.append("CONTROLLED_CANDIDATE_MARKER_INVALID")
    return {
        "status": "PASS" if not failures else "FAIL",
        "operation": operation,
        "repository": repository,
        "pr": pr_number,
        "source_sha": source_sha,
        "version": version,
        "expected_branch": f"{expected_ref} or {expected_ref}-vN (N >= 2)",
        "failures": sorted(set(failures)),
    }


def validate_validation_evidence(
    report: dict[str, Any], *, repository: str, pr_number: int, source_sha: str, package_path: Path
) -> dict[str, Any]:
    """Compatibility wrapper for the shared candidate-evidence collector."""
    return validate_candidate_evidence(
        report,
        repository=repository,
        pr_number=pr_number,
        source_sha=source_sha,
        package_path=package_path,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--operation", required=True)
    parser.add_argument("--pr-json", required=True, type=Path)
    parser.add_argument("--validation-report", type=Path)
    parser.add_argument("--candidate-package", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    pr = json.loads(args.pr_json.read_text(encoding="utf-8"))
    result = validate_request(
        pr,
        repository=args.repository,
        pr_number=args.pr,
        source_sha=args.source_sha,
        version=args.version,
        operation=args.operation,
    )
    if (args.validation_report is None) != (args.candidate_package is None):
        parser.error("--validation-report and --candidate-package must be supplied together")
    if args.validation_report and args.candidate_package:
        evidence = validate_validation_evidence(
            json.loads(args.validation_report.read_text(encoding="utf-8-sig")),
            repository=args.repository,
            pr_number=args.pr,
            source_sha=args.source_sha,
            package_path=args.candidate_package,
        )
        result["validation_evidence"] = evidence
        if evidence["status"] != "PASS":
            result["status"] = "FAIL"
            result["failures"] = sorted(set(result["failures"] + evidence["failures"]))
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
