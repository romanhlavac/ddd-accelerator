#!/usr/bin/env python3
"""Collect read-only STANDARD payload diagnostics; never claim a release gate PASS."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "runtime/platform"))
from governance_kernel import evaluate_physical_scope_binding
from standard_scope_collection import collect_content_scope


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--package-path", required=True)
    parser.add_argument("--version")
    parser.add_argument("--request-body-env")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    version = args.version
    if args.request_body_env:
        values = re.findall(r"<!-- ddda:standard-scope-inventory:v2 version=((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)) -->", os.environ.get(args.request_body_env, ""))
        if len(values) != 1 or version is not None:
            raise ValueError("Expected one explicit versioned diagnostic request")
        version = values[0]
    if not version or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("Stable diagnostic version is required")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("Read-only GitHub authentication is required")
    spec = importlib.util.spec_from_file_location("standard_scope_live", ROOT / "scripts/platform/Test-DDDAReleaseScope.py")
    ns = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ns)
    inventory = ns.physical_scope_snapshot(args.repository, version, args.source_sha, token, {})
    milestone = ns.find_milestone(args.repository, version, token)
    rows = ns.milestone_issue_rows(args.repository, milestone["number"], token)
    digest = hashlib.sha256(Path(args.package_path).read_bytes()).hexdigest()
    physical = collect_content_scope(
        ROOT, args.repository, version, args.source_sha, args.package_path, digest,
        {"tag": inventory["previous_release_tag"], "sha": inventory["previous_release_sha"]},
        token, ns.rest_get, ns.rest_pages, inventory["shipping_prs"], rows,
    )
    scope = sorted(row["number"] for row in rows)
    decision = evaluate_physical_scope_binding(
        physical, expected_source_sha=args.source_sha, expected_version=version, declared_scope=scope,
        expected_repository=args.repository, expected_package_sha256=digest,
    )
    result = {"schema_version": 2, "collection_status": "PASS", "release_scope_gate_status": "NOT_RUN",
              "kernel_preview": decision.as_dict(), "declared_scope": scope, "physical_scope": physical,
              "git_inventory": inventory}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"collection_status": "PASS", "kernel_preview_status": decision.status,
                      "failure_codes": decision.failure_codes}, ensure_ascii=True))
    return 0  # acquisition PASS is distinct from the deliberately blocked preview


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Standard scope acquisition failed: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1)
