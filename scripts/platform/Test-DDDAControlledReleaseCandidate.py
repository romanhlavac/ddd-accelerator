#!/usr/bin/env python3
"""Fail-closed selection contract for controlled release-candidate operations."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
OPERATIONS = frozenset({"technical_validation", "publish_hrdr_scaffold", "release_scope_dry_run"})


def validate_request(
    pr: dict[str, Any], *, repository: str, pr_number: int, source_sha: str, version: str, operation: str
) -> dict[str, Any]:
    failures: list[str] = []
    if operation not in OPERATIONS:
        failures.append("CONTROLLED_CANDIDATE_OPERATION_INVALID")
    if not VERSION_RE.fullmatch(version):
        failures.append("CONTROLLED_CANDIDATE_VERSION_INVALID")
    if not SHA_RE.fullmatch(source_sha):
        failures.append("CONTROLLED_CANDIDATE_SOURCE_SHA_INVALID")
    head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
    base = pr.get("base") if isinstance(pr.get("base"), dict) else {}
    head_repo = head.get("repo") if isinstance(head.get("repo"), dict) else {}
    expected_ref = f"release/{version}-controlled-recovery-source"
    if int(pr.get("number") or -1) != pr_number:
        failures.append("CONTROLLED_CANDIDATE_PR_IDENTITY_INVALID")
    if pr.get("state") != "open" or pr.get("draft") is not True:
        failures.append("CONTROLLED_CANDIDATE_MUST_REMAIN_OPEN_DRAFT")
    if str(head.get("sha") or "") != source_sha:
        failures.append("CONTROLLED_CANDIDATE_HEAD_SHA_MISMATCH")
    if str(head.get("ref") or "") != expected_ref:
        failures.append("CONTROLLED_CANDIDATE_BRANCH_INVALID")
    if str(head_repo.get("full_name") or "") != repository:
        failures.append("CONTROLLED_CANDIDATE_HEAD_REPOSITORY_INVALID")
    if str(base.get("ref") or "") != "main":
        failures.append("CONTROLLED_CANDIDATE_BASE_INVALID")
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
        "expected_branch": expected_ref,
        "failures": sorted(set(failures)),
    }


def validate_validation_evidence(
    report: dict[str, Any], *, repository: str, pr_number: int, source_sha: str, package_path: Path
) -> dict[str, Any]:
    """Bind a reusable candidate package to one exact controlled candidate."""
    failures: list[str] = []
    source = report.get("source") if isinstance(report.get("source"), dict) else {}
    package = report.get("package") if isinstance(report.get("package"), dict) else {}
    expected_hash = str(package.get("sha256") or "").lower()
    if report.get("status") != "PASS":
        failures.append("CONTROLLED_CANDIDATE_VALIDATION_NOT_PASS")
    if str(source.get("repository") or "") != repository:
        failures.append("CONTROLLED_CANDIDATE_VALIDATION_REPOSITORY_MISMATCH")
    if int(source.get("pr") or -1) != pr_number:
        failures.append("CONTROLLED_CANDIDATE_VALIDATION_PR_MISMATCH")
    if str(source.get("commit") or "") != source_sha:
        failures.append("CONTROLLED_CANDIDATE_VALIDATION_SHA_MISMATCH")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        failures.append("CONTROLLED_CANDIDATE_VALIDATION_PACKAGE_HASH_INVALID")
    if not package_path.is_file():
        failures.append("CONTROLLED_CANDIDATE_PACKAGE_MISSING")
    elif expected_hash:
        actual_hash = hashlib.sha256(package_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            failures.append("CONTROLLED_CANDIDATE_PACKAGE_HASH_MISMATCH")
    return {
        "status": "PASS" if not failures else "FAIL",
        "repository": repository,
        "pr": pr_number,
        "source_sha": source_sha,
        "candidate_package_sha256": expected_hash,
        "failures": sorted(set(failures)),
    }


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
