#!/usr/bin/env python3
"""Validate explicit human authorization for controlled DDDA release promotion."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

MARKER = "<!-- ddda:promotion-release-authorization:v1 -->"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
COMMAND_RE = re.compile(
    r"^/ddda promote-controlled\s+"
    r"--source-sha\s+(?P<source_sha>[0-9a-f]{40})\s+"
    r"--version\s+(?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))\s+"
    r"--package-sha256\s+(?P<package_sha256>[0-9a-f]{64})$"
)


def _flatten_comments(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    result: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, list):
            result.extend(entry for entry in item if isinstance(entry, dict))
        elif isinstance(item, dict):
            result.append(item)
    return result


def _extract_json(body: str) -> dict[str, Any] | None:
    match = re.search(r"```json\s*(\{.*?\})\s*```", body, flags=re.DOTALL)
    if match is None:
        return None
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def validate_authorization(
    comments_payload: Any,
    *,
    repository: str,
    pr_number: int,
    actor: str,
    command_text: str,
) -> dict[str, Any]:
    failures: list[str] = []
    command_match = COMMAND_RE.fullmatch(command_text.strip())
    if command_match is None:
        return {
            "status": "FAIL",
            "repository": repository,
            "pr": pr_number,
            "actor": actor,
            "failures": ["CONTROLLED_PROMOTION_COMMAND_INVALID"],
        }

    source_sha = command_match.group("source_sha")
    version = command_match.group("version")
    package_sha256 = command_match.group("package_sha256")
    if not SHA_RE.fullmatch(source_sha):
        failures.append("CONTROLLED_PROMOTION_SOURCE_SHA_INVALID")
    if not VERSION_RE.fullmatch(version):
        failures.append("CONTROLLED_PROMOTION_VERSION_INVALID")
    if not HASH_RE.fullmatch(package_sha256):
        failures.append("CONTROLLED_PROMOTION_PACKAGE_HASH_INVALID")

    comments = _flatten_comments(comments_payload)
    marked = [comment for comment in comments if MARKER in str(comment.get("body") or "")]
    if len(marked) != 1:
        failures.append("CONTROLLED_PROMOTION_AUTHORIZATION_MARKER_COUNT_INVALID")
        authorization_comment = None
        authorization = None
    else:
        authorization_comment = marked[0]
        authorization = _extract_json(str(authorization_comment.get("body") or ""))
        if authorization is None:
            failures.append("CONTROLLED_PROMOTION_AUTHORIZATION_JSON_INVALID")

    if authorization_comment is not None:
        user = authorization_comment.get("user") if isinstance(authorization_comment.get("user"), dict) else {}
        login = str(user.get("login") or "")
        user_type = str(user.get("type") or "")
        issue_url = str(authorization_comment.get("issue_url") or "")
        if not login or login != actor or user_type == "Bot" or login.endswith("[bot]"):
            failures.append("CONTROLLED_PROMOTION_AUTHORIZATION_PROVENANCE_INVALID")
        if not issue_url.endswith(f"/issues/{pr_number}"):
            failures.append("CONTROLLED_PROMOTION_AUTHORIZATION_PR_MISMATCH")

    if authorization is not None:
        expected_side_effects = {
            "release_package",
            "release_validation",
            f"tag:v{version}",
            f"github_release:v{version}",
        }
        observed_side_effects = authorization.get("authorized_side_effects_after_canonical_pass")
        observed_side_effects = set(observed_side_effects) if isinstance(observed_side_effects, list) else set()
        expected_command = f"promote-pr -Pr {pr_number} -Version {version} -ConfirmPromotion"
        checks = {
            "CONTROLLED_PROMOTION_AUTHORIZATION_SCHEMA_INVALID": authorization.get("schema_version") == 1,
            "CONTROLLED_PROMOTION_AUTHORIZATION_REPOSITORY_MISMATCH": str(authorization.get("repository") or "") == repository,
            "CONTROLLED_PROMOTION_AUTHORIZATION_PR_MISMATCH": int(authorization.get("pr") or -1) == pr_number,
            "CONTROLLED_PROMOTION_AUTHORIZATION_SHA_MISMATCH": str(authorization.get("source_sha") or "") == source_sha,
            "CONTROLLED_PROMOTION_AUTHORIZATION_PACKAGE_MISMATCH": str(authorization.get("candidate_package_sha256") or "") == package_sha256,
            "CONTROLLED_PROMOTION_AUTHORIZATION_VERSION_MISMATCH": str(authorization.get("version") or "") == version,
            "CONTROLLED_PROMOTION_AUTHORIZATION_ACTOR_MISMATCH": str(authorization.get("authorizer") or "") == actor,
            "CONTROLLED_PROMOTION_AUTHORIZATION_DECISION_INVALID": str(authorization.get("decision") or "").lower() == "approve",
            "CONTROLLED_PROMOTION_AUTHORIZATION_COMMAND_MISMATCH": str(authorization.get("authorized_command") or "") == expected_command,
            "CONTROLLED_PROMOTION_AUTHORIZATION_MODE_INVALID": str(authorization.get("release_source_mode") or "") == "CONTROLLED_EXACT_PR_SHA",
            "CONTROLLED_PROMOTION_AUTHORIZATION_MERGE_BOUNDARY_INVALID": authorization.get("candidate_merge_allowed") is False,
            "CONTROLLED_PROMOTION_AUTHORIZATION_SIDE_EFFECTS_INVALID": observed_side_effects == expected_side_effects,
        }
        for failure, passed in checks.items():
            if not passed:
                failures.append(failure)

    return {
        "status": "PASS" if not failures else "FAIL",
        "repository": repository,
        "pr": pr_number,
        "actor": actor,
        "source_sha": source_sha,
        "version": version,
        "candidate_package_sha256": package_sha256,
        "authorization_comment_id": None if authorization_comment is None else int(authorization_comment.get("id") or 0),
        "failures": sorted(set(failures)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--command-text", required=True)
    parser.add_argument("--comments-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = json.loads(args.comments_json.read_text(encoding="utf-8-sig"))
    result = validate_authorization(
        payload,
        repository=args.repository,
        pr_number=args.pr,
        actor=args.actor,
        command_text=args.command_text,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
