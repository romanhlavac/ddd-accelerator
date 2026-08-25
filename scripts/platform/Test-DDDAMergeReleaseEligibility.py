#!/usr/bin/env python3
"""Read-only releasable-main guard for governed implementation merges.

The active train is the single open ``DDDA X.Y.Z`` Milestone.  While it
exists, a PR may merge to main only when its one primary Change Request is in
that Milestone.  The script never changes a Milestone, Project field or PR.
"""

from __future__ import annotations

import argparse
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


def collect(repository: str, pr_number: int, expected_sha: str, token: str) -> dict[str, Any]:
    pr = request_json(f"repos/{repository}/pulls/{pr_number}", token)
    head = str(((pr or {}).get("head") or {}).get("sha") or "")
    if head != expected_sha:
        raise GitHubReadError("PR head changed before merge eligibility evaluation")
    primary = primary_changes(str((pr or {}).get("body") or ""))
    issue: dict[str, Any] = {}
    if len(primary) == 1:
        issue = request_json(f"repos/{repository}/issues/{primary[0]}", token) or {}
    return {
        "repository": repository,
        "pr": pr_number,
        "source_sha": head,
        "active_release": active_release(pages(f"repos/{repository}/milestones?state=all", token)),
        "primary_crs": primary,
        "primary_cr": {
            "milestone": ((issue.get("milestone") or {}).get("title")),
            "target_release": target_release(str(issue.get("body") or "")),
        },
    }


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
