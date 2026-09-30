#!/usr/bin/env python3
"""Normalize one authoritative Human Review and bind it through the kernel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.platform.human_review_evidence import collect_human_review_evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comments", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--candidate-package-sha256", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    comments = json.loads(args.comments.read_text(encoding="utf-8-sig"))
    result = collect_human_review_evidence(
        comments,
        repository=args.repository,
        pr_number=args.pr,
        source_sha=args.source_sha,
        candidate_package_sha256=args.candidate_package_sha256,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
