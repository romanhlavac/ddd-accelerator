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

from runtime.platform.candidate_evidence import restore_candidate_evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = restore_candidate_evidence(
        args.artifact_root,
        repository=args.repository,
        pr_number=args.pr,
        source_sha=args.source_sha,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
