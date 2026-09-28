#!/usr/bin/env python3
"""Extract one authoritative Human Release Decision Record from issue comments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.platform.hrdr_evidence import collect_hrdr_evidence


def extract_hrdr(comments: list[dict[str, Any]]) -> dict[str, Any]:
    result = collect_hrdr_evidence(comments)
    if result["status"] != "PASS":
        raise ValueError(", ".join(result["failures"]))
    return result["record"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comments-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.comments_json.read_text(encoding="utf-8"))
    comments = payload if isinstance(payload, list) else []
    record = extract_hrdr(comments)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
