#!/usr/bin/env python3
"""GitHub Actions automation-branch lifecycle; no implementation authority.

Use managed_branch(...) in a workflow's try/finally body. The existing Project
reconciler invokes audit only; it never deletes historical ambiguous branches.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from runtime.platform.branch_policy import (  # noqa: E402
    PROVENANCE_PATH, evaluate_automation_cleanup, parse_automation_name,
)


class GitHub:
    def __init__(self, repository: str, token: str):
        if not repository or repository.count("/") != 1 or not token:
            raise ValueError("Repository and Actions token are required")
        self.repository = repository
        self.root = f"https://api.github.com/repos/{repository}"
        self.token = token

    def request(self, path: str, *, method: str = "GET", payload=None):
        url = self.root + path
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + self.token,
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        })
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
        return json.loads(content) if content else None

    def pages(self, path: str):
        page = 1
        while True:
            separator = "&" if "?" in path else "?"
            items = self.request(f"{path}{separator}per_page=100&page={page}")
            if not isinstance(items, list):
                raise ValueError("Expected a paginated GitHub array")
            yield from items
            if len(items) < 100:
                return
            page += 1


def create_branch(api: GitHub, *, purpose: str, run_id: int, owner: str, source_sha: str):
    """Create one manifest-only commit and one new ref, bound to the source SHA."""
    branch = f"automation/{purpose}-{run_id}"
    if parse_automation_name(branch) != (purpose, run_id):
        raise ValueError("Noncanonical automation branch identity")
    if len(source_sha) != 40 or any(c not in "0123456789abcdef" for c in source_sha):
        raise ValueError("Source SHA must be exact")
    if int(os.environ.get("GITHUB_RUN_ID", "0")) != run_id or os.environ.get("GITHUB_ACTOR") != owner:
        raise ValueError("Owner/run identity differs from current GitHub Actions run")
    if os.environ.get("GITHUB_SHA") != source_sha:
        raise ValueError("Source differs from current workflow checkout")
    commit = api.request(f"/git/commits/{source_sha}")
    manifest = {
        "schema_version": 1, "kind": "ddda_automation_branch", "branch": branch,
        "owner": owner, "purpose": purpose, "run_id": run_id,
        "source_sha": source_sha, "allowed_staging_prefix": ".ddda/automation-staging/",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    blob = api.request("/git/blobs", method="POST", payload={
        "content": json.dumps(manifest, sort_keys=True) + "\n", "encoding": "utf-8"
    })["sha"]
    tree = api.request("/git/trees", method="POST", payload={
        "base_tree": commit["tree"]["sha"],
        "tree": [{"path": PROVENANCE_PATH, "mode": "100644", "type": "blob", "sha": blob}],
    })["sha"]
    head = api.request("/git/commits", method="POST", payload={
        "message": f"chore(automation): stage {purpose} run {run_id}", "tree": tree,
        "parents": [source_sha],
    })["sha"]
    api.request("/git/refs", method="POST", payload={"ref": "refs/heads/" + branch, "sha": head})
    return branch, head


def inspect_branch(api: GitHub, name: str, *, expected_head: str | None = None):
    """Fresh exact ref, PR, release, run, manifest and changed-path inspection."""
    identity = parse_automation_name(name)
    if identity is None:
        return {"branch": name, "classification": "AMBIGUOUS", "reason": "Noncanonical name"}
    encoded = urllib.parse.quote(name, safe="/")
    ref = api.request(f"/git/ref/heads/{encoded}")
    head = ref["object"]["sha"]
    if expected_head is not None and expected_head != head:
        return {"branch": name, "head_sha": head, "classification": "AMBIGUOUS", "reason": "Expected HEAD moved"}
    prs = list(api.pages("/pulls?state=all&head=" + urllib.parse.quote(api.repository.split("/")[0] + ":" + name)))
    release_refs = list(api.pages("/releases"))
    protected = any(r.get("target_commitish") in (name, head) for r in release_refs)
    tag_refs = api.request("/git/matching-refs/tags")
    for tag in tag_refs:
        obj = tag.get("object", {})
        # An annotated tag points at a tag object, not directly at its commit.
        while obj.get("type") == "tag":
            obj = api.request("/git/tags/" + obj["sha"])["object"]
        protected = protected or obj.get("sha") == head
    provenance = None
    try:
        raw = api.request(f"/contents/{PROVENANCE_PATH}?ref={head}")
        provenance = json.loads(base64.b64decode(raw["content"]).decode("utf-8"))
    except (urllib.error.HTTPError, KeyError, ValueError, json.JSONDecodeError):
        pass
    compare = None
    run = None
    if provenance and isinstance(provenance.get("source_sha"), str):
        try:
            compare = api.request(f"/compare/{provenance['source_sha']}...{head}")
        except urllib.error.HTTPError:
            pass
    if provenance and provenance.get("run_id") == identity[1]:
        try:
            run = api.request(f"/actions/runs/{identity[1]}")
        except urllib.error.HTTPError:
            pass
    if run and (
        run.get("head_sha") != (provenance or {}).get("source_sha")
        or run.get("actor", {}).get("login") != (provenance or {}).get("owner")
        or run.get("repository", {}).get("full_name") != api.repository
    ):
        run = None
    files = compare.get("files", []) if isinstance(compare, dict) else []
    # GitHub compare caps files at 300 and commits at 250; either cap is ambiguous.
    complete = len(files) < 300 and bool(compare) and compare.get("ahead_by", 0) < 250
    paths = [path for f in files for path in (f.get("filename"), f.get("previous_filename")) if path]
    decision = evaluate_automation_cleanup(
        name, head_sha=head, provenance=provenance,
        open_pr_numbers=[p["number"] for p in prs],
        changed_paths=paths if complete else [],
        source_ancestor=bool(compare and compare.get("behind_by") == 0 and compare.get("ahead_by", 0) >= 1),
        run_id=run["id"] if run else None,
        run_terminal=bool(run and run.get("status") == "completed"),
        same_owner_run=bool(
            os.environ.get("GITHUB_RUN_ID") == str(identity[1])
            and os.environ.get("GITHUB_ACTOR") == (provenance or {}).get("owner")
        ),
        referenced_by_release_or_audit=protected,
    )
    stale = False
    if provenance and run and run.get("status") == "completed":
        try:
            created_at = datetime.fromisoformat(str(provenance["created_at"]))
            stale = datetime.now(timezone.utc) - created_at >= timedelta(days=7)
        except (KeyError, TypeError, ValueError):
            pass
    return {
        "branch": name, "head_sha": head, "source_sha": (provenance or {}).get("source_sha"),
        "run_id": identity[1], "owner": (provenance or {}).get("owner"),
        "associated_prs": [p["number"] for p in prs], "release_reference": protected,
        "changed_paths": paths,
        "run_status": run.get("status") if run else None,
        "classification": decision.classification, "reason": decision.reason,
        "stale": stale,
    }


def cleanup_branch(api: GitHub, name: str, *, expected_head: str):
    evidence = inspect_branch(api, name, expected_head=expected_head)
    if evidence["classification"] != "SAFE_TO_DELETE":
        return evidence | {"deleted": False}
    # Re-read immediately before the ordinary non-force ref deletion.
    path = "/git/refs/heads/" + urllib.parse.quote(name, safe="/")
    if api.request(path)["object"]["sha"] != expected_head:
        return evidence | {"classification": "AMBIGUOUS", "reason": "HEAD moved before deletion", "deleted": False}
    api.request(path, method="DELETE")
    return evidence | {"deleted": True}


@contextmanager
def managed_branch(api: GitHub, *, purpose: str, run_id: int, owner: str, source_sha: str):
    """Success/failure cleanup; only a branch with proven identity is deleted."""
    name, head = create_branch(api, purpose=purpose, run_id=run_id, owner=owner, source_sha=source_sha)
    work_error = None
    try:
        yield name, head
    except BaseException as exc:
        work_error = exc
        raise
    finally:
        try:
            current = api.request("/git/ref/heads/" + urllib.parse.quote(name, safe="/"))["object"]["sha"]
            result = cleanup_branch(api, name, expected_head=current)
            if not result["deleted"]:
                raise RuntimeError(json.dumps({"cleanup": result}, sort_keys=True))
        except Exception as cleanup_error:
            if work_error is not None:
                work_error.add_note(f"Automation branch cleanup failed: {cleanup_error}")
            else:
                raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("audit", "cleanup"), required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--token-env", default="GH_TOKEN")
    parser.add_argument("--branch")
    parser.add_argument("--expected-head")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    api = GitHub(args.repository, os.environ.get(args.token_env, ""))
    if args.mode == "cleanup":
        if not args.branch or not args.expected_head:
            parser.error("cleanup needs branch and expected-head")
        result = cleanup_branch(api, args.branch, expected_head=args.expected_head)
    else:
        branches = [b for b in api.pages("/branches") if b["name"].startswith("automation/")]
        result = {"schema_version": 1, "source_sha": os.environ.get("GITHUB_SHA"), "branches": [inspect_branch(api, b["name"], expected_head=b["commit"]["sha"]) for b in branches]}
        result["safe_to_delete"] = [b["branch"] for b in result["branches"] if b["classification"] == "SAFE_TO_DELETE" and b["stale"]]
        result["ambiguous"] = [b["branch"] for b in result["branches"] if b["classification"] == "AMBIGUOUS"]
        result["deleted"] = []  # The Project workflow is a read-only stale audit.
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0 if args.mode != "cleanup" or result["deleted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
