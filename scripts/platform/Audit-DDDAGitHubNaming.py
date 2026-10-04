"""Inventory GitHub naming and perform a digest-bound additive label backfill.

Only a structured Platform Areas declaration containing DOC can propose the
pre-existing 'documentation' navigation label. No title, ref, release record
or review evidence is rewritten. Project fields are reconciled by their owner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from typing import Any

REPO = "romanhlavac/ddd-accelerator"
DOC_AREA = re.compile(r"(?im)^\s*(?:[-*]\s*)?Platform Areas:\s*([^\n]+)$")
PREFIX = re.compile(r"^\[(WP-\d+|CR|CHR|DEFECT|ENABLER|RELEASE|GAP)\]")


def api(path: str, *, method: str = "GET", fields: tuple[str, ...] = (),
        collection_key: str | None = None) -> Any:
    command = ["gh", "api"]
    if method != "GET":
        command += ["-X", method]
    command += [path]
    for field in fields:
        command += ["-f", field]
    if method == "GET" and "per_page=100" in path:
        command += ["--paginate", "--slurp"]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    value = json.loads(result.stdout)
    if method == "GET" and "per_page=100" in path:
        if collection_key:
            return [item for page in value for item in page[collection_key]]
        return [item for page in value for item in page]
    return value


def explicit_doc_area(body: str) -> bool:
    matches = DOC_AREA.findall(body or "")
    return len(matches) == 1 and "DOC" in re.split(r"[^A-Z-]+", matches[0].upper())


def classify_issue(row: dict[str, Any]) -> dict[str, Any]:
    labels = sorted(label["name"] for label in row.get("labels", []))
    title = row.get("title") or ""
    prefix = PREFIX.match(title)
    is_pr = "pull_request" in row
    result = {
        "artifact": "PR" if is_pr else "Issue",
        "number": row["number"],
        "title": title,
        "state": row["state"],
        "labels": labels,
        "classification": "PRESERVE_AS_HISTORICAL_IDENTITY",
        "reason": "historical title and evidence retained",
        "add_labels": [],
    }
    if is_pr:
        if row["state"] == "open" and title.startswith("[RELEASE]"):
            result.update(classification="AMBIGUOUS", reason="candidate role requires #131 Kernel")
        return result
    if prefix and prefix.group(1) == "CHR":
        result.update(classification="AMBIGUOUS", reason="[CHR] needs independent CR authority")
        return result
    if title.count("[") != title.count("]"):
        result.update(classification="AMBIGUOUS", reason="unbalanced role prefix")
        return result
    if explicit_doc_area(row.get("body") or "") and "documentation" not in labels:
        result.update(
            classification="SAFE_TO_NORMALIZE",
            reason="one explicit Platform Areas: DOC declaration; additive existing label",
            add_labels=["documentation"],
        )
    elif not prefix:
        result.update(classification="AMBIGUOUS", reason="no recognized role prefix")
    return result


def plan(issues: list[dict[str, Any]], branches: list[dict[str, Any]],
         tags: list[dict[str, Any]], releases: list[dict[str, Any]],
         workflows: list[dict[str, Any]]) -> dict[str, Any]:
    records = [classify_issue(row) for row in issues]
    records += [
        {"artifact": "Branch", "ref": x["name"],
         "classification": "PRESERVE_AS_HISTORICAL_IDENTITY", "add_labels": []}
        for x in branches
    ]
    records += [
        {"artifact": "Tag", "ref": x["name"],
         "classification": "PRESERVE_AS_HISTORICAL_IDENTITY", "add_labels": []}
        for x in tags
    ]
    records += [
        {"artifact": "Release", "ref": x["tag_name"], "name": x["name"],
         "classification": "PRESERVE_AS_HISTORICAL_IDENTITY", "add_labels": []}
        for x in releases
    ]
    records += [
        {"artifact": "Workflow", "name": x["name"], "path": x["path"],
         "classification": "PRESERVE_AS_HISTORICAL_IDENTITY", "add_labels": []}
        for x in workflows
    ]
    records.sort(key=lambda x: (x["artifact"], x.get("number", 0), x.get("ref", ""), x.get("path", "")))
    writes = [
        {"number": x["number"], "add_labels": x["add_labels"]}
        for x in records if x["add_labels"]
    ]
    source = {"repository": REPO, "records": records, "writes": writes}
    digest = hashlib.sha256(json.dumps(source, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return {"schema_version": 1, **source, "plan_sha256": digest,
            "write_count": len(writes), "mode": "dry-run"}


def live_plan() -> dict[str, Any]:
    issues = api(f"repos/{REPO}/issues?state=all&per_page=100")
    branches = api(f"repos/{REPO}/branches?per_page=100")
    tags = api(f"repos/{REPO}/tags?per_page=100")
    releases = api(f"repos/{REPO}/releases?per_page=100")
    workflows = api(f"repos/{REPO}/actions/workflows?per_page=100",
                    collection_key="workflows")
    return plan(issues, branches, tags, releases, workflows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-plan-sha256")
    parser.add_argument("--max-writes", type=int, default=0)
    parser.add_argument("--target-issue", type=int)
    args = parser.parse_args()
    if args.apply and (not args.expected_plan_sha256 or args.max_writes != 1
                       or not args.target_issue):
        parser.error("apply requires a reviewed plan SHA-256, one target Issue and max-writes=1")
    report = live_plan()
    if args.apply:
        if report["plan_sha256"] != args.expected_plan_sha256:
            raise SystemExit("live inventory differs from approved dry-run")
        selected = [x for x in report["writes"] if x["number"] == args.target_issue]
        if len(selected) != 1:
            raise SystemExit("target Issue is not one safe additive write in the live plan")
        report["mode"] = "apply"
        report["applied_count"] = 0
        with open(args.report, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        for write in selected:
            number = write["number"]
            api(f"repos/{REPO}/issues/{number}/labels", method="POST",
                fields=tuple(f"labels[]={label}" for label in write["add_labels"]))
            observed = api(f"repos/{REPO}/issues/{number}")
            present = {label["name"] for label in observed["labels"]}
            if not set(write["add_labels"]).issubset(present):
                raise SystemExit(f"read-back failed for Issue #{number}")
        report["applied_count"] = len(selected)
        report["remaining_plan"] = live_plan()["write_count"]
    with open(args.report, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"mode": report["mode"], "plan_sha256": report["plan_sha256"],
                      "write_count": report["write_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
