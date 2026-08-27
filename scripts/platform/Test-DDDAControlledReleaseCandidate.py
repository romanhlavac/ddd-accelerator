#!/usr/bin/env python3
"""Fail-closed selection contract for controlled release-candidate operations."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_RE = re.compile(r"^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$")
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--operation", required=True)
    parser.add_argument("--pr-json", required=True, type=Path)
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
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
