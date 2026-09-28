#!/usr/bin/env python3
"""Evaluate authoritative HRDR comment evidence through the shared collector."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.platform.hrdr_evidence import collect_hrdr_evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comments", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--repository")
    parser.add_argument("--pr", type=int)
    parser.add_argument("--source-sha")
    parser.add_argument("--candidate-package-sha256")
    parser.add_argument("--version")
    args = parser.parse_args()

    comments = json.loads(args.comments.read_text(encoding="utf-8-sig"))
    result = collect_hrdr_evidence(
        comments,
        allow_missing=args.allow_missing,
        expected_repository=args.repository,
        expected_pr=args.pr,
        expected_source_sha=args.source_sha,
        expected_package_sha256=args.candidate_package_sha256,
        expected_version=args.version,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] in {"PASS", "MISSING"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
