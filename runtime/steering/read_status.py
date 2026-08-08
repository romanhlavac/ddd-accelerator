from __future__ import annotations

import json
from pathlib import Path
import sys

from ruamel.yaml import YAML


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        print("Usage: read_status.py <reports/project-status.yaml>", file=sys.stderr)
        return 2

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    path = Path(arguments[0]).resolve()
    if not path.is_file():
        print(f"Status report neexistuje: {path}", file=sys.stderr)
        return 2

    with path.open("r", encoding="utf-8-sig") as handle:
        document = YAML(typ="safe").load(handle) or {}

    report = document.get("status_report")
    if not isinstance(report, dict):
        print(f"Status report nemá objekt status_report: {path}", file=sys.stderr)
        return 2

    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
