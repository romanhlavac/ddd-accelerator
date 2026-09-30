#!/usr/bin/env python3
"""Collect GitHub checks and evaluate canonical latest-by-name evidence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.platform.check_evidence import evaluate_check_evidence


def _get_json(url: str, token: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _collect(repository: str, commit: str, token: str) -> tuple[list[Any], list[Any]]:
    runs: list[Any] = []
    for page in range(1, 101):
        payload = _get_json(
            f"https://api.github.com/repos/{repository}/commits/{commit}/check-runs"
            f"?per_page=100&page={page}",
            token,
        )
        batch = payload.get("check_runs", []) if isinstance(payload, dict) else []
        runs.extend(batch)
        if len(batch) < 100:
            break
    combined = _get_json(
        f"https://api.github.com/repos/{repository}/commits/{commit}/status",
        token,
    )
    statuses = combined.get("statuses", []) if isinstance(combined, dict) else []
    return runs, statuses


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository")
    parser.add_argument("--commit")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--token-env", default="DDDA_CHECKS_GITHUB_TOKEN")
    parser.add_argument("--required-check", action="append")
    parser.add_argument("--ignored-check", action="append", default=[])
    parser.add_argument("--accepted-conclusion", action="append")
    parser.add_argument("--wait-seconds", type=int, default=0)
    parser.add_argument("--poll-seconds", type=int, default=10)
    args = parser.parse_args()

    if args.input is None and (not args.repository or not args.commit):
        parser.error("--repository and --commit are required without --input")
    token = os.environ.get(args.token_env, "")
    if args.input is None and not token:
        raise SystemExit(f"GitHub token environment variable is empty: {args.token_env}")
    deadline = time.monotonic() + max(0, args.wait_seconds)
    while True:
        if args.input is not None:
            payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
            runs = payload.get("check_runs", []) if isinstance(payload, dict) else []
            statuses = payload.get("statuses", []) if isinstance(payload, dict) else []
        else:
            runs, statuses = _collect(args.repository, args.commit, token)
        kwargs: dict[str, Any] = {
            "commit_statuses": statuses,
            "required_checks": args.required_check,
            "ignored_checks": args.ignored_check,
        }
        if args.accepted_conclusion is not None:
            kwargs["accepted_conclusions"] = args.accepted_conclusion
        result = evaluate_check_evidence(runs, **kwargs)
        if result["status"] == "PASS" or time.monotonic() >= deadline:
            break
        required = set(result.get("summary", {}).get("required_checks", []))
        accepted = set(result.get("summary", {}).get("accepted_conclusions", []))
        terminal = any(
            row.get("name") in required
            and row.get("status") == "COMPLETED"
            and row.get("conclusion") not in accepted
            for row in result.get("summary", {}).get("latest_results", [])
        )
        if terminal or args.wait_seconds <= 0:
            break
        if args.input is not None:
            break
        time.sleep(max(1, args.poll_seconds))

    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
