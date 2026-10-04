#!/usr/bin/env python3
"""Fail closed on new PR/push branch names; never mutate the repository."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from runtime.platform.branch_policy import evaluate_branch  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--pr", type=int, default=0)
    parser.add_argument("--policy", type=Path, default=Path("config/governance/branch-policy.json"))
    parser.add_argument("--bootstrap", action="store_true", help="first policy PR: canonical names only")
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    if args.bootstrap:
        policy["legacy_exceptions"] = []
    decision = evaluate_branch(
        args.branch, head_sha=args.sha, pr_number=args.pr or None, policy=policy
    )
    print(json.dumps({
        "schema_version": 1, "branch": args.branch, "sha": args.sha,
        "pr": args.pr or None, "classification": decision.classification,
        "allowed": decision.allowed_implementation_pr, "reason": decision.reason,
        "policy_source": str(args.policy), "bootstrap": args.bootstrap,
    }, sort_keys=True))
    return 0 if decision.allowed_implementation_pr else 1


if __name__ == "__main__":
    raise SystemExit(main())
