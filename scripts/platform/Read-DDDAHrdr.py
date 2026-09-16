#!/usr/bin/env python3
"""Extract one authoritative Human Release Decision Record from issue comments."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

MARKER = "<!-- ddda:human-release-decision:v1 -->"
JSON_RE = re.compile(r"(?s)```json\s*(?P<json>\{.*?\})\s*```")


def extract_hrdr(comments: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [row for row in comments if MARKER in str(row.get("body") or "")]
    if len(matches) != 1:
        raise ValueError("Expected exactly one authoritative HRDR comment")
    comment = matches[0]
    match = JSON_RE.search(str(comment.get("body") or ""))
    if not match:
        raise ValueError("Authoritative HRDR comment has no fenced JSON record")
    record = json.loads(match.group("json"))
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        raise ValueError("Authoritative HRDR record has an unsupported schema")
    author = str(((comment.get("user") or {}).get("login")) or "")
    if not author:
        raise ValueError("Authoritative HRDR comment has no GitHub author")
    if record.get("decision") != "pending" and author != str(record.get("reviewer") or ""):
        raise ValueError("Positive/negative HRDR must have human reviewer provenance")
    return record


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
