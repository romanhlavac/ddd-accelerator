"""Project history projection from GitHub release and merged-PR evidence.

The Project is a read-back surface. This command never creates a release,
tag, package, report, decision, or release authority. An evidence mismatch
stops the entire projection before any Project mutation.
"""

import argparse
import base64
import hashlib
import importlib.util
import json
import re
import tempfile
from pathlib import Path

CORE_PATH = Path(__file__).with_name("Reconcile-DDDAProjectBacklogCore.py")
spec = importlib.util.spec_from_file_location("ddda_project_core_history", CORE_PATH)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

CONTRACT = Path("config/governance/release-history.json")
FIELD_NAMES = (
    "Released Version", "Release Status", "Release SHA", "Release Tag",
    "Released At", "Release Decision", "Package SHA-256", "Release Evidence",
)
HISTORY_VIEW = "Release & Delivery History"
SHA = re.compile(r"^[0-9a-f]{40}$")


def api(path):
    return core.gh("api", f"repos/{core.REPO}/{path}", json_out=True)


def tagged_source(record):
    ref = api(f"git/ref/tags/{record['tag']}")
    obj = ref["object"]
    if obj["type"] != "tag":
        raise RuntimeError(f"{record['tag']}: annotated tag required")
    tag = api(f"git/tags/{obj['sha']}")
    if tag["tag"] != record["tag"] or tag["object"]["type"] != "commit":
        raise RuntimeError(f"{record['tag']}: tag identity mismatch")
    if tag["object"]["sha"] != record["source_sha"]:
        raise RuntimeError(f"{record['tag']}: source SHA mismatch")


def source_ledger(record):
    path = record["pulls_from_source_ledger"]
    result = api(f"contents/{path}?ref={record['tag']}")
    ledger = json.loads(base64.b64decode(result["content"]).decode("utf-8"))
    if ledger["version"] != record["version"] or ledger["schema_version"] != 2:
        raise RuntimeError("Release source ledger identity mismatch")
    entries = ledger["entries"]
    if not entries or len(entries) != len({e["source_pr"] for e in entries}):
        raise RuntimeError("Ambiguous release source PR mapping")
    return {int(e["source_pr"]): e for e in entries}


def read_report(record, release):
    version = record["version"]
    names = {a["name"]: a for a in release["assets"]}
    expected = {
        f"ddda-{version}.zip": record["package_sha256"],
        f"ddda-{version}-release-report.json": record["release_report_sha256"],
        f"ddda-{version}-release-report.md": None,
    }
    if set(names) != set(expected):
        raise RuntimeError(f"{version}: canonical Release asset set mismatch")
    for name, digest in expected.items():
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", names[name].get("digest") or ""):
            raise RuntimeError(f"{version}: asset digest unavailable for {name}")
        if digest and names[name]["digest"] != f"sha256:{digest}":
            raise RuntimeError(f"{version}: asset digest mismatch for {name}")
    with tempfile.TemporaryDirectory() as tmp:
        core.gh("release", "download", record["tag"], "--repo", core.REPO,
                "--pattern", f"ddda-{version}*", "--dir", tmp)
        data = Path(tmp, f"ddda-{version}-release-report.json").read_bytes()
        for name, asset in names.items():
            physical_digest = hashlib.sha256(Path(tmp, name).read_bytes()).hexdigest()
            if asset["digest"] != f"sha256:{physical_digest}":
                raise RuntimeError(f"{version}: physical asset digest mismatch for {name}")
    if hashlib.sha256(data).hexdigest() != record["release_report_sha256"]:
        raise RuntimeError(f"{version}: portable report bytes mismatch")
    report = json.loads(data)
    if (report.get("status") != "PASS"
            or report.get("source", {}).get("commit") != record["source_sha"]
            or report.get("source", {}).get("pr") != record["decision_pr"]
            or report.get("package", {}).get("sha256") != record["package_sha256"]):
        raise RuntimeError(f"{version}: portable validation report disagrees")
    return report


def decision(record, scope_issues):
    comment = api(f"issues/comments/{record['decision_comment_id']}")
    if comment["user"]["login"] != core.OWNER:
        raise RuntimeError("Human Release Decision owner mismatch")
    body = comment["body"]
    if body.count("<!-- ddda:human-release-decision:v1 -->") != 1:
        raise RuntimeError("Human Release Decision marker mismatch")
    matches = re.findall(r"```json\s*(\{.*?\})\s*```", body, re.S)
    if len(matches) != 1:
        raise RuntimeError("Human Release Decision JSON cardinality mismatch")
    d = json.loads(matches[0])
    if (d.get("repository") != core.REPO or d.get("pr") != record["decision_pr"]
            or d.get("source_sha") != record["source_sha"]
            or d.get("version") != record["version"]
            or d.get("candidate_package_sha256") != record["candidate_package_sha256"]
            or d.get("decision") != "go" or d.get("reviewer") != core.OWNER
            or d.get("decision_owner") != core.OWNER
            or set(d.get("scope_issues") or []) != scope_issues):
        raise RuntimeError("Human Release Decision exact identity mismatch")
    return comment["html_url"]


def release_rows(record):
    version = record["version"]
    tagged_source(record)
    if record["status"] == "Historical evidence incomplete":
        try:
            api(f"releases/tags/{record['tag']}")
        except RuntimeError as exc:
            if "404" not in str(exc):
                raise
        else:
            raise RuntimeError(f"{version}: publication changed; rebaseline required")
        if record["package_sha256"] or record["release_report_sha256"]:
            raise RuntimeError(f"{version}: unsupported historical physical claim")
        comment = api(f"issues/comments/{record['decision_comment_id']}")
        body = comment["body"]
        if (comment["user"]["login"] != core.OWNER
                or record["source_sha"] not in body or record["tag"] not in body
                or record["recorded_package_sha256"] not in body
                or "GO_WITH_ACCEPTED_RISKS" not in body):
            raise RuntimeError(f"{version}: historical decision identity mismatch")
        mapping = {n: None for n in record["pulls"]}
        released_at = ""
        evidence = comment["html_url"]
    else:
        if record["status"] != "Released" or record["github_release"] != "published":
            raise RuntimeError(f"{version}: unknown evidence state")
        release = api(f"releases/tags/{record['tag']}")
        if (release.get("draft") or release.get("prerelease")
                or release["tag_name"] != record["tag"]
                or release["target_commitish"] != record["source_sha"]):
            raise RuntimeError(f"{version}: GitHub Release identity mismatch")
        read_report(record, release)
        mapping = source_ledger(record)
        evidence = release["html_url"] + " | " + decision(
            record, {entry["primary_cr"] for entry in mapping.values()})
        released_at = release["published_at"]
    rows = {}
    for number, entry in mapping.items():
        pr = api(f"pulls/{number}")
        if not pr.get("merged_at") or not pr.get("merge_commit_sha"):
            raise RuntimeError(f"#{number}: source PR is not merged")
        if entry and pr["merge_commit_sha"] != entry["source_merge_commit_sha"]:
            raise RuntimeError(f"#{number}: recovery ledger disagrees with merge")
        if not entry and pr["merge_commit_sha"] != record["source_sha"]:
            raise RuntimeError(f"#{number}: historical source mismatch")
        rows[number] = (pr, {
            "Released Version": version,
            "Release Status": record["status"],
            "Release SHA": record["source_sha"],
            "Release Tag": record["tag"],
            "Released At": released_at,
            "Release Decision": record["decision"],
            "Package SHA-256": record["package_sha256"] or "Unverified / unavailable",
            "Release Evidence": evidence,
        })
    return rows


def failed_outcome_rows(record):
    """Project can show a failed train only with exact failed Actions evidence."""
    status = record.get("status")
    if status not in ("Release validation failed", "Recovery required"):
        raise RuntimeError("Unknown non-release history status")
    version, source = record["version"], record["source_sha"]
    if not SHA.fullmatch(source) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise RuntimeError("Failed outcome identity is incomplete")
    run = api(f"actions/runs/{record['failed_run_id']}")
    if (run["head_sha"] != source or run["conclusion"] != "failure"
            or run["repository"]["full_name"] != core.REPO):
        raise RuntimeError("Failed Actions run identity mismatch")
    if status == "Recovery required":
        if record.get("tag") != f"v{version}":
            raise RuntimeError("Recovery tag/version disagreement")
        tagged_source(record)
        try:
            api(f"releases/tags/{record['tag']}")
        except RuntimeError as exc:
            if "404" not in str(exc):
                raise
        else:
            raise RuntimeError("Recovery record needs fresh publication rebaseline")
    elif record.get("tag"):
        raise RuntimeError("Failed validation cannot claim a tag")
    else:
        try:
            api(f"git/ref/tags/v{version}")
        except RuntimeError as exc:
            if "404" not in str(exc):
                raise
        else:
            raise RuntimeError("Failed validation has a tag; rebaseline required")
    pulls = record["pulls"]
    if not pulls or len(pulls) != len(set(pulls)):
        raise RuntimeError("Ambiguous failed release PR mapping")
    rows = {}
    for number in pulls:
        pr = api(f"pulls/{number}")
        if not pr.get("merged_at"):
            raise RuntimeError(f"#{number}: failed outcome PR is not merged")
        rows[number] = (pr, {
            "Released Version": version,
            "Release Status": status,
            "Release SHA": source,
            "Release Tag": record.get("tag") or "",
            "Released At": "",
            "Release Decision": "",
            "Package SHA-256": "Unverified / unavailable",
            "Release Evidence": run["html_url"],
        })
    return rows


def merged_prs():
    pages = core.gh("api", "--paginate", "--slurp",
                    f"repos/{core.REPO}/pulls?state=closed&per_page=100", json_out=True)
    return {int(p["number"]): p for page in pages for p in page if p.get("merged_at")}


def expected_rows(contract):
    published = core.gh("api", "--paginate", "--slurp",
                        f"repos/{core.REPO}/releases?per_page=100", json_out=True)
    known = {r["tag"] for r in contract["releases"] if r["github_release"] == "published"}
    unknown = {r["tag_name"] for page in published for r in page
               if not r.get("draft") and r["tag_name"].startswith("v") and r["tag_name"] not in known}
    if unknown:
        raise RuntimeError("Published release lacks versioned history contract: " + ", ".join(sorted(unknown)))
    merged = merged_prs()
    rows = {n: (p, {"Release Status": "Merged / awaiting release validation"})
            for n, p in merged.items()}
    for record in contract["releases"]:
        for n, (pr, fields) in release_rows(record).items():
            if n not in merged or n in rows and "Released Version" in rows[n][1]:
                raise RuntimeError(f"#{n}: ambiguous release-to-PR mapping")
            rows[n] = (pr, fields)
    for record in contract.get("unreleased_outcomes", []):
        for n, (pr, fields) in failed_outcome_rows(record).items():
            if n not in merged or "Released Version" in rows[n][1]:
                raise RuntimeError(f"#{n}: ambiguous release outcome mapping")
            rows[n] = (pr, fields)
    return rows


def reconcile_view(project_id, project_number, expected, repair):
    p = core.gql(core.Q_PROJECT, {"login": core.OWNER, "number": project_number})["data"]["user"]["projectV2"]
    by_name = {v["name"]: v for v in p["views"]["nodes"]}
    view = by_name.get(HISTORY_VIEW)
    if not view and repair:
        core.create_view(project_id, HISTORY_VIEW, expected["filter"])
        view = {"name": HISTORY_VIEW, "layout": "TABLE_LAYOUT", "filter": expected["filter"]}
    elif view and repair and (view["layout"] != "TABLE_LAYOUT" or view["filter"] != expected["filter"]):
        core.update_view(view["id"], HISTORY_VIEW, expected["filter"])
        view = {"name": HISTORY_VIEW, "layout": "TABLE_LAYOUT", "filter": expected["filter"]}
    return bool(view and view["layout"] == "TABLE_LAYOUT" and view["filter"] == expected["filter"])


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("evidence", "reconcile", "verify"), default="verify")
    args = parser.parse_args(argv)
    repair = args.mode == "reconcile"
    contract = json.loads(CONTRACT.read_text())
    if contract["schema_version"] != 1 or contract["view"]["name"] != HISTORY_VIEW:
        raise RuntimeError("Unknown history contract")
    rows = expected_rows(contract)  # All release authority is checked before writes.
    if args.mode == "evidence":
        print(json.dumps({"source_sha": core.cmd("git", "rev-parse", "HEAD"),
                          "release_versions": [r["version"] for r in contract["releases"]],
                          "merged_prs": len(rows), "evidence_status": "PASS"}))
        return
    repairs = []
    number, project_id, fields, _ = core.resolve_project(repairs, read_only=True)
    if repair:
        for name in FIELD_NAMES:
            if name not in fields:
                core.gh("project", "field-create", str(number), "--owner", core.OWNER,
                        "--name", name, "--data-type", "TEXT")
                repairs.append({"action": "ADD_HISTORY_FIELD", "field": name})
        _, _, fields, _ = core.resolve_project(repairs, read_only=True)
    missing_fields = set(FIELD_NAMES) - set(fields)
    view_ok = reconcile_view(project_id, number, contract["view"], repair)
    items = core.content_item_map(number, "PullRequest")
    problems = []
    for n, (pr, expected) in sorted(rows.items()):
        item = items.get(n)
        if not item and repair:
            item = {"id": core.add_project_item(project_id, pr), "fieldValues": {"nodes": []}}
            repairs.append({"pr": n, "action": "ADD_MERGED_HISTORY_ITEM"})
        if not item:
            problems.append({"pr": n, "result": "MISSING_HISTORY_ITEM"})
            continue
        current = core.values(item)
        for field in FIELD_NAMES:
            wanted = expected.get(field, "")
            if current.get(field, "") != wanted:
                if repair:
                    if wanted:
                        core.set_text(project_id, fields, item["id"], field, wanted)
                    else:
                        core.clear_field(project_id, fields, item["id"], field)
                    repairs.append({"pr": n, "action": "SET_HISTORY_FIELD", "field": field})
                else:
                    problems.append({"pr": n, "result": "HISTORY_FIELD_MISMATCH", "field": field,
                                     "actual": current.get(field), "expected": wanted})
    if repair:
        # A second independent pass reads back server state and must be zero-write.
        readback = main(["--mode", "verify"])
        path = Path(".reports/cr-delivery-audit-v6/release-history-reconcile.json")
        path.write_text(json.dumps({"repair_count": len(repairs), "repairs": repairs,
                                    "remaining_mismatches": readback["remaining_mismatches"]}, indent=2) + "\n")
        return readback
    if missing_fields or not view_ok:
        problems.append({"result": "HISTORY_SCHEMA_MISMATCH",
                         "missing_fields": sorted(missing_fields), "view_ok": view_ok})
    report = {"source_sha": core.cmd("git", "rev-parse", "HEAD"), "mode": args.mode,
              "merged_prs": len(rows), "release_versions": [r["version"] for r in contract["releases"]],
              "remaining_mismatches": len(problems), "problems": problems}
    path = Path(".reports/cr-delivery-audit-v6/release-history.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "problems"}))
    if problems:
        raise SystemExit(1)
    return report


if __name__ == "__main__":
    main()
