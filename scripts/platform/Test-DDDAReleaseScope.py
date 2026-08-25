#!/usr/bin/env python3
"""Collect live GitHub/Project release-scope state and evaluate the DDDA Release Scope Gate.

This script is deliberately read-only. It uses GitHub REST for PR/milestone/Issue
state and Project V2 GraphQL for the operational planning projection. All
business invariants are evaluated by runtime/platform/release_governance.py.
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

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
PLATFORM_RUNTIME = REPO_ROOT / "runtime" / "platform"
if str(PLATFORM_RUNTIME) not in sys.path:
    sys.path.insert(0, str(PLATFORM_RUNTIME))

from release_governance import evaluate_release_scope  # noqa: E402


API_ROOT = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"
PROJECT_TITLE = "DDDA Platform Backlog & Delivery"
PLANNING_VIEW = "Plánování a Backlog"
DELIVERY_VIEW = "Implementace a Delivery"
TARGET_RELEASE_RE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?Target\s+(?:Release|resolution|horizon)(?:\*\*)?\s*:\s*`?([^`\r\n]+)"
)
SEMVER_TAG_RE = re.compile(r"^v(?P<version>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$")
PRIMARY_CHANGE_RE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:Implements|Closes)\s+#(\d+)\s*$"
)


class GitHubReadError(RuntimeError):
    pass


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "DDDA-Release-Scope-Gate",
    }


def _request_json(
    url: str,
    token: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> tuple[Any, dict[str, str]]:
    data = None
    headers = _headers(token)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
            return (json.loads(payload) if payload.strip() else None, dict(response.headers.items()))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")[:1000]
        raise GitHubReadError(f"GitHub {method} {url} failed: HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise GitHubReadError(f"GitHub {method} {url} failed: {exc}") from exc


def rest_get(path: str, token: str) -> Any:
    payload, _ = _request_json(f"{API_ROOT}/{path.lstrip('/')}", token)
    return payload


def rest_pages(path: str, token: str) -> list[Any]:
    rows: list[Any] = []
    page = 1
    separator = "&" if "?" in path else "?"
    while True:
        batch = rest_get(f"{path}{separator}per_page=100&page={page}", token) or []
        if not isinstance(batch, list):
            raise GitHubReadError(f"Paginated endpoint did not return a list: {path}")
        rows.extend(batch)
        if len(batch) < 100:
            return rows
        page += 1


def graphql(query: str, variables: dict[str, Any], token: str) -> dict[str, Any]:
    payload, _ = _request_json(
        GRAPHQL_URL,
        token,
        method="POST",
        body={"query": query, "variables": variables},
    )
    if not isinstance(payload, dict):
        raise GitHubReadError("GitHub GraphQL returned a non-object payload")
    if payload.get("errors"):
        raise GitHubReadError("GitHub GraphQL failed: " + json.dumps(payload["errors"], ensure_ascii=False))
    return payload.get("data") or {}


def project_number(owner: str, project_token: str) -> int:
    query = """
    query($login:String!,$after:String){
      user(login:$login){
        projectsV2(first:100,after:$after){
          pageInfo{hasNextPage endCursor}
          nodes{number title closed}
        }
      }
    }
    """
    after = None
    matches: list[int] = []
    while True:
        data = graphql(query, {"login": owner, "after": after}, project_token)
        user = data.get("user")
        if not user:
            raise GitHubReadError(f"Project owner not found: {owner}")
        block = user["projectsV2"]
        for node in block["nodes"]:
            if node.get("title") == PROJECT_TITLE and not node.get("closed"):
                matches.append(int(node["number"]))
        if not block["pageInfo"]["hasNextPage"]:
            break
        after = block["pageInfo"]["endCursor"]
    if len(matches) != 1:
        raise GitHubReadError(
            f"Expected exactly one open Project named '{PROJECT_TITLE}', found {matches}"
        )
    return matches[0]


Q_PROJECT = """
query($login:String!,$number:Int!,$after:String){
  user(login:$login){
    projectV2(number:$number){
      title
      views(first:50){nodes{name layout filter}}
      items(first:100,after:$after){
        pageInfo{hasNextPage endCursor}
        nodes{
          content{
            __typename
            ... on Issue{number state}
          }
          fieldValues(first:50){nodes{
            __typename
            ... on ProjectV2ItemFieldSingleSelectValue{
              name
              field{... on ProjectV2FieldCommon{name}}
            }
            ... on ProjectV2ItemFieldTextValue{
              text
              field{... on ProjectV2FieldCommon{name}}
            }
          }}
        }
      }
    }
  }
}
"""


def _project_values(item: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for node in (item.get("fieldValues") or {}).get("nodes", []):
        field = node.get("field") or {}
        name = field.get("name")
        if not name:
            continue
        result[name] = node.get("name") if node.get("name") is not None else node.get("text")
    return result


def project_snapshot(owner: str, number: int, token: str) -> tuple[dict[str, Any], dict[int, dict[str, Any]]]:
    after = None
    rows: dict[int, dict[str, Any]] = {}
    meta: dict[str, Any] | None = None
    while True:
        data = graphql(Q_PROJECT, {"login": owner, "number": number, "after": after}, token)
        user = data.get("user")
        project = (user or {}).get("projectV2")
        if not project:
            raise GitHubReadError(f"Project #{number} not found for owner {owner}")
        if meta is None:
            views = project.get("views", {}).get("nodes", [])
            by_name = {v.get("name"): v for v in views}
            meta = {
                "title": project.get("title"),
                "planning_view_filter": (by_name.get(PLANNING_VIEW) or {}).get("filter") or "",
                "delivery_view_filter": (by_name.get(DELIVERY_VIEW) or {}).get("filter") or "",
            }
        block = project["items"]
        for item in block["nodes"]:
            content = item.get("content") or {}
            if content.get("__typename") != "Issue":
                continue
            number_value = content.get("number")
            if number_value is None:
                continue
            rows[int(number_value)] = _project_values(item)
        if not block["pageInfo"]["hasNextPage"]:
            break
        after = block["pageInfo"]["endCursor"]
    assert meta is not None
    return meta, rows


def find_milestone(repository: str, version: str, token: str) -> dict[str, Any]:
    wanted = f"DDDA {version}"
    milestones = rest_pages(f"repos/{repository}/milestones?state=all", token)
    matches = [m for m in milestones if m.get("title") == wanted]
    if len(matches) != 1:
        raise GitHubReadError(f"Expected exactly one milestone '{wanted}', found {len(matches)}")
    return matches[0]


def milestone_issue_rows(repository: str, milestone_number: int, token: str) -> list[dict[str, Any]]:
    all_rows = rest_pages(
        f"repos/{repository}/issues?state=all&milestone={milestone_number}", token
    )
    return [row for row in all_rows if "pull_request" not in row]


def active_blockers(repository: str, issue: int, token: str) -> list[int]:
    rows = rest_pages(
        f"repos/{repository}/issues/{issue}/dependencies/blocked_by", token
    )
    return sorted(
        int(row["number"])
        for row in rows
        if row.get("state") != "closed" and row.get("number") is not None
    )


def risk_horizon(body: str) -> str:
    match = TARGET_RELEASE_RE.search(body or "")
    return match.group(1).strip() if match else ""


def _tag_version(name: str) -> tuple[int, int, int] | None:
    match = SEMVER_TAG_RE.fullmatch(name)
    if not match:
        return None
    return (int(match.group("version")), int(match.group("minor")), int(match.group("patch")))


def _dereference_tag(repository: str, sha: str, object_type: str, token: str) -> str:
    """Resolve annotated tags without accepting an ambiguous non-commit object."""
    current_sha, current_type = sha, object_type
    for _ in range(4):
        if current_type == "commit":
            return current_sha
        if current_type != "tag":
            break
        tag = rest_get(f"repos/{repository}/git/tags/{current_sha}", token)
        obj = (tag or {}).get("object") or {}
        current_sha, current_type = str(obj.get("sha") or ""), str(obj.get("type") or "")
    raise GitHubReadError("Release tag does not resolve to a commit")


def previous_release_tag(repository: str, version: str, token: str) -> dict[str, str]:
    current = _tag_version(f"v{version}")
    if current is None:
        raise GitHubReadError(f"Release version is not stable SemVer: {version}")
    refs = rest_get(f"repos/{repository}/git/matching-refs/tags/", token)
    candidates: list[tuple[tuple[int, int, int], str, str, str]] = []
    for ref in refs or []:
        name = str(ref.get("ref") or "").removeprefix("refs/tags/")
        parsed = _tag_version(name)
        obj = ref.get("object") or {}
        if parsed is not None and parsed < current:
            candidates.append((parsed, name, str(obj.get("sha") or ""), str(obj.get("type") or "")))
    if not candidates:
        raise GitHubReadError(f"No canonical previous SemVer tag exists before v{version}")
    _, name, sha, object_type = max(candidates)
    return {"tag": name, "sha": _dereference_tag(repository, sha, object_type, token)}


def compare_commits(repository: str, base: str, head: str, token: str) -> tuple[str, list[dict[str, Any]]]:
    first = rest_get(f"repos/{repository}/compare/{base}...{head}?per_page=100&page=1", token)
    status = str((first or {}).get("status") or "")
    total = int((first or {}).get("total_commits") or 0)
    commits = list((first or {}).get("commits") or [])
    page = 2
    while len(commits) < total:
        more = rest_get(f"repos/{repository}/compare/{base}...{head}?per_page=100&page={page}", token)
        batch = list((more or {}).get("commits") or [])
        if not batch:
            raise GitHubReadError("Compare pagination ended before all physical source commits were read")
        commits.extend(batch)
        page += 1
    if len(commits) != total:
        raise GitHubReadError("Compare returned an ambiguous physical source commit count")
    return status, commits


def primary_change_requests(body: str) -> list[int]:
    return sorted({int(value) for value in PRIMARY_CHANGE_RE.findall(body or "")})


def physical_scope_snapshot(
    repository: str,
    version: str,
    source_sha: str,
    token: str,
    project_rows: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    previous = previous_release_tag(repository, version, token)
    compare_status, commits = compare_commits(repository, previous["tag"], source_sha, token)
    pr_numbers: set[int] = set()
    unmapped: set[str] = set()
    for commit in commits:
        sha = str(commit.get("sha") or "")
        linked = rest_pages(f"repos/{repository}/commits/{sha}/pulls", token)
        numbers = {int(row["number"]) for row in linked if row.get("number") is not None}
        if not numbers:
            unmapped.add(sha)
        pr_numbers.update(numbers)

    shipping: list[dict[str, Any]] = []
    for number in sorted(pr_numbers):
        pr = rest_get(f"repos/{repository}/pulls/{number}", token)
        primary = primary_change_requests(str((pr or {}).get("body") or ""))
        authority: dict[str, Any] = {}
        if len(primary) == 1:
            authority = rest_get(f"repos/{repository}/issues/{primary[0]}", token) or {}
        milestone = (authority.get("milestone") or {}).get("title")
        project = project_rows.get(primary[0], {}) if len(primary) == 1 else {}
        shipping.append(
            {
                "number": number,
                "merged": bool((pr or {}).get("merged_at")),
                "merge_commit_sha": (pr or {}).get("merge_commit_sha"),
                "primary_crs": primary,
                "milestone": milestone,
                "target_release": project.get("Target Release"),
            }
        )

    return {
        "previous_release_tag": previous["tag"],
        "previous_release_sha": previous["sha"],
        "release_source_sha": source_sha,
        "compare_status": compare_status,
        "commit_count": len(commits),
        "unmapped_commit_shas": sorted(unmapped),
        "shipping_prs": shipping,
    }


def collect_snapshot(
    record: dict[str, Any],
    *,
    repository: str,
    pr: int,
    version: str,
    api_token: str,
    project_token: str,
) -> dict[str, Any]:
    pr_info = rest_get(f"repos/{repository}/pulls/{pr}", api_token)
    current_head = ((pr_info or {}).get("head") or {}).get("sha")

    milestone = find_milestone(repository, version, api_token)
    scope_rows = milestone_issue_rows(repository, int(milestone["number"]), api_token)
    milestone_issues = sorted(int(row["number"]) for row in scope_rows)

    issue_states = {int(row["number"]): row.get("state") for row in scope_rows}
    blockers = {
        issue: active_blockers(repository, issue, api_token)
        for issue in milestone_issues
    }

    risk_states: dict[int, str] = {}
    risk_assignees: dict[int, list[str]] = {}
    risk_horizons: dict[int, str] = {}
    for risk in record.get("accepted_risks", []):
        if not isinstance(risk, dict):
            continue
        try:
            issue = int(risk.get("issue", 0))
        except (TypeError, ValueError):
            continue
        if issue <= 0:
            continue
        data = rest_get(f"repos/{repository}/issues/{issue}", api_token)
        if "pull_request" in data:
            raise GitHubReadError(f"Accepted-risk reference #{issue} is a pull request, not an Issue")
        risk_states[issue] = str(data.get("state", ""))
        risk_assignees[issue] = [
            str(x.get("login"))
            for x in data.get("assignees", [])
            if x.get("login")
        ]
        risk_horizons[issue] = risk_horizon(str(data.get("body") or ""))

    owner = repository.split("/", 1)[0]
    proj_number = project_number(owner, project_token)
    project_meta, project_rows = project_snapshot(owner, proj_number, project_token)
    physical_scope = physical_scope_snapshot(
        repository,
        version,
        current_head,
        api_token,
        project_rows,
    )

    return {
        "current_pr_head": current_head,
        "milestone_title": milestone.get("title"),
        "milestone_number": int(milestone["number"]),
        "milestone_issues": milestone_issues,
        "issue_states": issue_states,
        "blockers": blockers,
        "project": project_meta,
        "project_number": proj_number,
        "project_rows": project_rows,
        "risk_issue_states": risk_states,
        "risk_issue_assignees": risk_assignees,
        "risk_issue_horizons": risk_horizons,
        "physical_scope": physical_scope,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--hrdr", required=True)
    parser.add_argument("--output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    project_token = os.environ.get("DDDA_GITHUB_PROJECT_TOKEN")
    if not api_token:
        print("Release Scope Gate FAIL: GH_TOKEN or GITHUB_TOKEN is required for read-only GitHub evidence.", file=sys.stderr)
        return 2
    if not project_token:
        print("Release Scope Gate FAIL: DDDA_GITHUB_PROJECT_TOKEN is required for authoritative Project V2 read-back.", file=sys.stderr)
        return 2

    try:
        record = json.loads(Path(args.hrdr).read_text(encoding="utf-8-sig"))
        snapshot = collect_snapshot(
            record,
            repository=args.repository,
            pr=args.pr,
            version=args.version,
            api_token=api_token,
            project_token=project_token,
        )
        result = evaluate_release_scope(
            record,
            snapshot,
            expected_repository=args.repository,
            expected_pr=args.pr,
            expected_source_sha=args.source_sha,
            expected_package_sha256=args.candidate_sha256,
            expected_version=args.version,
        )
        evidence = {
            "schema_version": 1,
            "repository": args.repository,
            "pr": args.pr,
            "source_sha": args.source_sha,
            "candidate_package_sha256": args.candidate_sha256,
            "version": args.version,
            "scope_source": "GitHub Milestone + Issue/native dependency + Project V2 live read-back",
            "milestone": snapshot.get("milestone_title"),
            "scope_items": result.as_dict()["scope_issues"],
            "terminal_items": sorted(
                int(k) for k, state in snapshot.get("issue_states", {}).items() if state == "closed"
            ),
            "deferred_items": result.as_dict()["accepted_risk_issues"],
            "unresolved_blockers": snapshot.get("blockers"),
            "project_mismatches": [
                failure for failure in result.failures if "PROJECT" in failure
            ],
            "milestone_mismatches": [
                failure for failure in result.failures if "MILESTONE" in failure
            ],
            "residual_risks": record.get("accepted_risks", []),
            "hrdr_risk_set": result.as_dict()["accepted_risk_issues"],
            "physical_scope": snapshot.get("physical_scope"),
            **result.as_dict(),
            "snapshot": snapshot,
        }
        text = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
        print(text, end="")
        return 0 if result.status == "PASS" else 1
    except (OSError, ValueError, GitHubReadError) as exc:
        print(f"Release Scope Gate FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
