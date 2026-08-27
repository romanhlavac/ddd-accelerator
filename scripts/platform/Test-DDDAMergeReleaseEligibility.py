#!/usr/bin/env python3
"""Read-only releasable-main guard for governed implementation merges.

The active train is the single open ``DDDA X.Y.Z`` Milestone.  While it
exists, a PR may merge to main only when its one primary Change Request is in
that Milestone.  The script never changes a Milestone, Project field or PR.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "runtime" / "platform"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from release_governance import evaluate_merge_release_eligibility  # noqa: E402


API_ROOT = "https://api.github.com"
MILESTONE_RE = re.compile(r"^DDDA (?P<version>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))$")
PRIMARY_RE = re.compile(r"(?im)^\s*(?:[-*]\s*)?(?:Implements|Closes)\s+#(\d+)\s*$")
TARGET_RE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?Target\s+Release(?:\*\*)?\s*:\s*`?([^`\r\n]+)"
)
TRANSITION_RE = re.compile(
    r"(?is)<!--\s*ddda:merge-eligibility-transition:v1\s*-->\s*```json\s*(\{.*?\})\s*```"
)
GOVERNANCE_REPAIR_RE = re.compile(
    r"(?is)<!--\s*ddda:merge-eligibility-governance-repair:v1\s*-->\s*```json\s*(\{.*?\})\s*```"
)

FUTURE_RELEASE_METADATA_PATHS = frozenset(
    {
        "config/governance/github-bootstrap.json",
        "config/governance/backlog-policy.yaml",
        "docs/roadmap/backlog-index.md",
        "runtime/platform/tests/test_project_backlog_delivery_governance.py",
    }
)
TRANSITION_PATHS = frozenset(
    {
        "runtime/platform/release_governance.py",
        "runtime/platform/tests/test_release_governance.py",
        "runtime/platform/tests/test_merge_release_eligibility_collector.py",
        "scripts/platform/Test-DDDAMergeReleaseEligibility.py",
        "docs/adr/0012-future-release-metadata-merge-eligibility.md",
        "docs/developer-guide/platform-development-lifecycle.md",
    }
)
TRANSITION_FILE_STATUSES = {
    "docs/adr/0012-future-release-metadata-merge-eligibility.md": "added",
    "runtime/platform/tests/test_merge_release_eligibility_collector.py": "added",
    "docs/developer-guide/platform-development-lifecycle.md": "modified",
    "runtime/platform/release_governance.py": "modified",
    "runtime/platform/tests/test_release_governance.py": "modified",
    "scripts/platform/Test-DDDAMergeReleaseEligibility.py": "modified",
}

# The value is deliberately the exact main SHA before this remediation.  The
# transition is therefore impossible once any other main change is integrated.
TRANSITION_BASE_SHA = "b61392ace66a95c808f321f3bd4b046cc5f564e5"
TRANSITION_PRIMARY_CR = 16

# This is a second, one-time bootstrap transition.  It permits the narrowly
# scoped repair that makes a previously integrated guard able to assess its
# own follow-up repair.  It is intentionally exact-base-bound and expires as
# soon as main advances.
GOVERNANCE_REPAIR_TRANSITION_BASE_SHA = "fdcc2b323eff4bcc9cef71207e280f3ffa950dd8"
GOVERNANCE_REPAIR_PATHS = frozenset(
    {
        "docs/adr/0012-future-release-metadata-merge-eligibility.md",
        "runtime/platform/tests/test_merge_release_eligibility_collector.py",
        "scripts/platform/Test-DDDAMergeReleaseEligibility.py",
    }
)
GOVERNANCE_REPAIR_TRANSITION_PATHS = GOVERNANCE_REPAIR_PATHS | {
    "runtime/platform/release_governance.py",
}
GOVERNANCE_REPAIR_TRANSITION_FILE_STATUSES = {
    path: "modified" for path in GOVERNANCE_REPAIR_TRANSITION_PATHS
}


class GitHubReadError(RuntimeError):
    pass


def request_json(path: str, token: str) -> Any:
    request = Request(
        f"{API_ROOT}/{path.lstrip('/')}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "DDDA-Merge-Release-Eligibility",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")[:500]
        raise GitHubReadError(f"GitHub GET {path} failed: HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise GitHubReadError(f"GitHub GET {path} failed: {exc}") from exc


def pages(path: str, token: str) -> list[Any]:
    result: list[Any] = []
    for page in range(1, 101):
        separator = "&" if "?" in path else "?"
        rows = request_json(f"{path}{separator}per_page=100&page={page}", token)
        if not isinstance(rows, list):
            raise GitHubReadError(f"Expected a list from {path}")
        result.extend(rows)
        if len(rows) < 100:
            return result
    raise GitHubReadError(f"Pagination limit exceeded for {path}")


def active_release(milestones: list[dict[str, Any]]) -> dict[str, str] | None:
    matches = []
    for milestone in milestones:
        match = MILESTONE_RE.fullmatch(str(milestone.get("title") or ""))
        if match and milestone.get("state") == "open":
            matches.append(match.group("version"))
    if not matches:
        return None
    if len(matches) != 1:
        raise GitHubReadError(f"Expected at most one active DDDA release train, found {sorted(matches)}")
    return {"version": matches[0]}


def primary_changes(body: str) -> list[int]:
    return sorted({int(x) for x in PRIMARY_RE.findall(body or "")})


def target_release(body: str) -> str | None:
    match = TARGET_RE.search(body or "")
    return match.group(1).strip() if match else None


def content_text(repository: str, path: str, ref: str, token: str) -> str:
    payload = request_json(f"repos/{repository}/contents/{path}?ref={ref}", token)
    if not isinstance(payload, dict) or payload.get("encoding") != "base64":
        raise GitHubReadError(f"Expected base64 file content for {path} at {ref}")
    try:
        return base64.b64decode(str(payload.get("content") or "")).decode("utf-8-sig")
    except (ValueError, UnicodeDecodeError) as exc:
        raise GitHubReadError(f"Invalid UTF-8 JSON content for {path} at {ref}") from exc


def pr_files(repository: str, pr_number: int, token: str) -> list[dict[str, Any]]:
    rows = pages(f"repos/{repository}/pulls/{pr_number}/files", token)
    if not all(isinstance(row, dict) for row in rows):
        raise GitHubReadError("PR files response contains an invalid row")
    return rows


def milestone_spec(config: dict[str, Any], version: str) -> dict[str, Any] | None:
    wanted = f"DDDA {version}"
    matches = [row for row in config.get("milestones", []) if isinstance(row, dict) and row.get("title") == wanted]
    if len(matches) != 1:
        return None
    return matches[0]


def issue_metadata(config: dict[str, Any], issue_numbers: set[int]) -> dict[str, Any] | None:
    result: dict[str, Any] = {}
    for group in config.get("item_groups", []):
        if not isinstance(group, dict) or group.get("kind") != "issue":
            continue
        metadata = group.get("metadata")
        numbers = group.get("numbers")
        if not isinstance(metadata, dict) or not isinstance(numbers, list):
            return None
        for value in numbers:
            try:
                number = int(value)
            except (TypeError, ValueError):
                return None
            if number in issue_numbers:
                if str(number) in result:
                    return None
                result[str(number)] = metadata
    return result if set(result) == {str(n) for n in issue_numbers} else None


def future_release_metadata_evidence(
    *,
    repository: str,
    pr: dict[str, Any],
    active: dict[str, str] | None,
    active_issue_numbers: set[int],
    token: str,
) -> dict[str, Any] | None:
    """Prove that a PR changes only future planning and preserves active scope."""
    if active is None:
        return None
    version = active["version"]
    base_sha = str(((pr.get("base") or {}).get("sha")) or "")
    head_sha = str(((pr.get("head") or {}).get("sha")) or "")
    failures: list[str] = []
    try:
        rows = pr_files(repository, int(pr["number"]), token)
        paths = {str(row.get("filename") or "") for row in rows}
        if paths != FUTURE_RELEASE_METADATA_PATHS:
            failures.append("MERGE_ELIGIBILITY_FUTURE_RELEASE_PATHS_INVALID")
        if any(str(row.get("status") or "") != "modified" for row in rows):
            failures.append("MERGE_ELIGIBILITY_FUTURE_RELEASE_FILE_STATUS_INVALID")

        base = json.loads(content_text(repository, "config/governance/github-bootstrap.json", base_sha, token))
        head = json.loads(content_text(repository, "config/governance/github-bootstrap.json", head_sha, token))
        if not isinstance(base, dict) or not isinstance(head, dict):
            raise ValueError("bootstrap root is not an object")
        base_spec = milestone_spec(base, version)
        head_spec = milestone_spec(head, version)
        if base_spec is None or head_spec is None or base_spec != head_spec:
            failures.append("MERGE_ELIGIBILITY_FUTURE_RELEASE_ACTIVE_SCOPE_CHANGED")
        if base_spec is None or set(base_spec.get("issues") or []) != active_issue_numbers:
            failures.append("MERGE_ELIGIBILITY_FUTURE_RELEASE_ACTIVE_SCOPE_EVIDENCE_INVALID")
        base_meta = issue_metadata(base, active_issue_numbers)
        head_meta = issue_metadata(head, active_issue_numbers)
        if base_meta is None or head_meta is None or base_meta != head_meta:
            failures.append("MERGE_ELIGIBILITY_FUTURE_RELEASE_ACTIVE_METADATA_CHANGED")
        future_specs_changed = base.get("milestones") != head.get("milestones")
        if not future_specs_changed:
            failures.append("MERGE_ELIGIBILITY_FUTURE_RELEASE_NO_FUTURE_PLAN_CHANGE")
    except (GitHubReadError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        failures.append("MERGE_ELIGIBILITY_FUTURE_RELEASE_EVIDENCE_INVALID")
        paths = set()
    return {
        "status": "PASS" if not failures else "FAIL",
        "exception": "FUTURE_RELEASE_METADATA_ONLY",
        "changed_paths": sorted(paths),
        "active_scope_unchanged": not failures,
        "failures": sorted(set(failures)),
    }


def governance_repair_evidence(
    *,
    repository: str,
    pr: dict[str, Any],
    active: dict[str, str] | None,
    active_issue_numbers: set[int],
    primary: list[int],
    token: str,
) -> dict[str, Any] | None:
    """Prove a guard-only repair cannot change the active release contract."""
    if active is None:
        return None
    base_sha = str(((pr.get("base") or {}).get("sha")) or "")
    head_sha = str(((pr.get("head") or {}).get("sha")) or "")
    failures: list[str] = []
    try:
        rows = pr_files(repository, int(pr["number"]), token)
        paths = {str(row.get("filename") or "") for row in rows}
        integration_merge = False
        if paths != GOVERNANCE_REPAIR_PATHS:
            normalized = integration_merge_files(repository, pr, token)
            if normalized is not None:
                head_sha, rows = normalized
                paths = {str(row.get("filename") or "") for row in rows}
                integration_merge = True
        if primary != [TRANSITION_PRIMARY_CR]:
            failures.append("MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_PRIMARY_CR_INVALID")
        if paths != GOVERNANCE_REPAIR_PATHS:
            failures.append("MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_PATHS_INVALID")
        if any(str(row.get("status") or "") != "modified" for row in rows):
            failures.append("MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_FILE_STATUS_INVALID")

        base = json.loads(content_text(repository, "config/governance/github-bootstrap.json", base_sha, token))
        head = json.loads(content_text(repository, "config/governance/github-bootstrap.json", head_sha, token))
        if not isinstance(base, dict) or not isinstance(head, dict) or base != head:
            failures.append("MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_GOVERNANCE_CHANGED")
        spec = milestone_spec(base, active["version"]) if isinstance(base, dict) else None
        if spec is None or set(spec.get("issues") or []) != active_issue_numbers:
            failures.append("MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_ACTIVE_SCOPE_EVIDENCE_INVALID")
    except (GitHubReadError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        failures.append("MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_EVIDENCE_INVALID")
        paths = set()
    return {
        "status": "PASS" if not failures else "FAIL",
        "exception": "MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_ONLY",
        "changed_paths": sorted(paths),
        "integration_merge_normalized": integration_merge if "integration_merge" in locals() else False,
        "active_scope_unchanged": not failures,
        "failures": sorted(set(failures)),
    }


def transition_evidence(pr: dict[str, Any], repository: str, primary: list[int], token: str) -> dict[str, Any] | None:
    """Validate the one-time exact-base transition for this guard remediation."""
    base_sha = str(((pr.get("base") or {}).get("sha")) or "")
    failures: list[str] = []
    if base_sha != TRANSITION_BASE_SHA:
        failures.append("MERGE_ELIGIBILITY_TRANSITION_BASE_MISMATCH")
    if primary != [TRANSITION_PRIMARY_CR]:
        failures.append("MERGE_ELIGIBILITY_TRANSITION_PRIMARY_CR_MISMATCH")
    try:
        record_match = TRANSITION_RE.search(str(pr.get("body") or ""))
        record = json.loads(record_match.group(1)) if record_match else None
        if not isinstance(record, dict) or record != {
            "schema_version": 1,
            "kind": "future_release_metadata_merge_eligibility_transition",
            "base_sha": TRANSITION_BASE_SHA,
        }:
            failures.append("MERGE_ELIGIBILITY_TRANSITION_RECORD_INVALID")
        rows = pr_files(repository, int(pr["number"]), token)
        paths = {str(row.get("filename") or "") for row in rows}
        if paths != TRANSITION_PATHS:
            failures.append("MERGE_ELIGIBILITY_TRANSITION_PATHS_INVALID")
        observed_statuses = {str(row.get("filename") or ""): str(row.get("status") or "") for row in rows}
        if observed_statuses != TRANSITION_FILE_STATUSES:
            failures.append("MERGE_ELIGIBILITY_TRANSITION_FILE_STATUS_INVALID")
    except (GitHubReadError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        failures.append("MERGE_ELIGIBILITY_TRANSITION_EVIDENCE_INVALID")
        paths = set()
    return {
        "status": "PASS" if not failures else "FAIL",
        "exception": "FUTURE_RELEASE_METADATA_GUARD_TRANSITION_V1",
        "changed_paths": sorted(paths),
        "failures": sorted(set(failures)),
    }


def governance_repair_transition_evidence(
    pr: dict[str, Any], repository: str, primary: list[int], token: str
) -> dict[str, Any] | None:
    """Validate the exact-base bootstrap for the guard-repair allowance."""
    base_sha = str(((pr.get("base") or {}).get("sha")) or "")
    failures: list[str] = []
    if base_sha != GOVERNANCE_REPAIR_TRANSITION_BASE_SHA:
        failures.append("MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_TRANSITION_BASE_MISMATCH")
    if primary != [TRANSITION_PRIMARY_CR]:
        failures.append("MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_TRANSITION_PRIMARY_CR_MISMATCH")
    try:
        record_match = GOVERNANCE_REPAIR_RE.search(str(pr.get("body") or ""))
        record = json.loads(record_match.group(1)) if record_match else None
        if not isinstance(record, dict) or record != {
            "schema_version": 1,
            "kind": "merge_eligibility_governance_repair_transition",
            "base_sha": GOVERNANCE_REPAIR_TRANSITION_BASE_SHA,
        }:
            failures.append("MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_TRANSITION_RECORD_INVALID")
        rows = pr_files(repository, int(pr["number"]), token)
        paths = {str(row.get("filename") or "") for row in rows}
        if paths != GOVERNANCE_REPAIR_TRANSITION_PATHS:
            failures.append("MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_TRANSITION_PATHS_INVALID")
        statuses = {str(row.get("filename") or ""): str(row.get("status") or "") for row in rows}
        if statuses != GOVERNANCE_REPAIR_TRANSITION_FILE_STATUSES:
            failures.append("MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_TRANSITION_FILE_STATUS_INVALID")
    except (GitHubReadError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        failures.append("MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_TRANSITION_EVIDENCE_INVALID")
        paths = set()
    return {
        "status": "PASS" if not failures else "FAIL",
        "exception": "MERGE_ELIGIBILITY_GOVERNANCE_REPAIR_TRANSITION_V1",
        "changed_paths": sorted(paths),
        "failures": sorted(set(failures)),
    }


def collect(repository: str, pr_number: int, expected_sha: str, token: str) -> dict[str, Any]:
    pr = request_json(f"repos/{repository}/pulls/{pr_number}", token)
    head = str(((pr or {}).get("head") or {}).get("sha") or "")
    if head != expected_sha:
        raise GitHubReadError("PR head changed before merge eligibility evaluation")
    primary = primary_changes(str((pr or {}).get("body") or ""))
    issue: dict[str, Any] = {}
    if len(primary) == 1:
        issue = request_json(f"repos/{repository}/issues/{primary[0]}", token) or {}
    active = active_release(pages(f"repos/{repository}/milestones?state=all", token))
    active_issue_numbers: set[int] = set()
    if active is not None:
        milestones = pages(f"repos/{repository}/milestones?state=all", token)
        matches = [row for row in milestones if row.get("title") == f"DDDA {active['version']}" and row.get("state") == "open"]
        if len(matches) != 1:
            raise GitHubReadError("Active release milestone evidence is ambiguous")
        active_issue_numbers = {
            int(row["number"])
            for row in pages(f"repos/{repository}/issues?state=all&milestone={int(matches[0]['number'])}", token)
            if isinstance(row, dict) and "number" in row
        }
    snapshot = {
        "repository": repository,
        "pr": pr_number,
        "source_sha": head,
        "active_release": active,
        "primary_crs": primary,
        "primary_cr": {
            "milestone": ((issue.get("milestone") or {}).get("title")),
            "target_release": target_release(str(issue.get("body") or "")),
        },
    }
    snapshot["future_release_metadata"] = future_release_metadata_evidence(
        repository=repository,
        pr=pr,
        active=active,
        active_issue_numbers=active_issue_numbers,
        token=token,
    )
    snapshot["governance_repair"] = governance_repair_evidence(
        repository=repository,
        pr=pr,
        active=active,
        active_issue_numbers=active_issue_numbers,
        primary=primary,
        token=token,
    )
    snapshot["merge_eligibility_transition"] = transition_evidence(pr, repository, primary, token)
    snapshot["governance_repair_transition"] = governance_repair_transition_evidence(
        pr, repository, primary, token
    )
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Merge eligibility FAIL: GH_TOKEN or GITHUB_TOKEN is required.", file=sys.stderr)
        return 2
    try:
        snapshot = collect(args.repository, args.pr, args.expected_sha, token)
        failures = evaluate_merge_release_eligibility(snapshot)
        result = {
            "schema_version": 1,
            **snapshot,
            "status": "PASS" if not failures else "FAIL",
            "failing_invariants": failures,
            "side_effects_allowed": not failures,
        }
        text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
        print(text, end="")
        return 0 if not failures else 1
    except (GitHubReadError, OSError, ValueError) as exc:
        print(f"Merge eligibility FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
