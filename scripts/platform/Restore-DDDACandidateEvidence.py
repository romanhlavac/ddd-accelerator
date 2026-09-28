#!/usr/bin/env python3
"""Restore one exact report-bound candidate package from an artifact root."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.platform.candidate_evidence import (
    restore_candidate_evidence,
    restore_candidate_evidence_paths,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--artifact-root", type=Path)
    source.add_argument("--validation-report", type=Path)
    parser.add_argument("--candidate-package", type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.candidate_package and not args.validation_report:
        parser.error("--candidate-package requires --validation-report")
    if args.artifact_root:
        result = restore_candidate_evidence(
            args.artifact_root,
            repository=args.repository,
            pr_number=args.pr,
            source_sha=args.source_sha,
        )
    else:
        result = restore_candidate_evidence_paths(
            args.validation_report,
            repository=args.repository,
            pr_number=args.pr,
            source_sha=args.source_sha,
            candidate_package_path=args.candidate_package,
        )
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
