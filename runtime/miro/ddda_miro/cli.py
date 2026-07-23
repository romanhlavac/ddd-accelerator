from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from .client import MiroClient
from .config import ProjectConfig
from .render import render_board
from .sync import sync_project


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ddda-miro")
    parser.add_argument("--project", required=True, type=Path, help="DDDA project root")
    parser.add_argument("--platform", type=Path, help="DDDA platform root")
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="Validate local Miro configuration")
    doctor.add_argument("--online", action="store_true", help="Call Miro GET board")
    render = sub.add_parser("render", help="Create or update the DDDA board scaffold")
    render.add_argument("--create-board", action="store_true")
    render.add_argument("--dry-run", action="store_true")
    sync = sub.add_parser("sync", help="Synchronize managed YAML artifacts and Miro items")
    sync.add_argument("--direction", choices=["pull", "push", "both"], default="both")
    sync.add_argument("--dry-run", action="store_true")
    sync.add_argument("--include-layout", action="store_true")
    sync.add_argument("--confirm-delete", action="store_true")
    sync.add_argument("--recreate-missing", action="store_true")
    sync.add_argument("--promote-new", action="store_true", help="Create YAML for new marked Miro items")
    watch = sub.add_parser("watch", help="Poll Miro and run controlled bidirectional sync")
    watch.add_argument("--interval-seconds", type=int, default=60)
    watch.add_argument("--include-layout", action="store_true")
    watch.add_argument("--max-cycles", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = ProjectConfig.load(args.project, args.platform)
        if args.command == "doctor":
            result = {
                "project_id": config.project_id, "project_root": str(config.root),
                "scaffold": str(config.scaffold_path), "scaffold_exists": config.scaffold_path.exists(),
                "board_id": config.board_id, "board_id_env": config.board_id_env,
                "token_env": config.token_env, "token_present": bool(os.environ.get(config.token_env)),
                "synchronization": config.synchronization,
            }
            if args.online:
                if not config.board_id:
                    raise ValueError("Board ID is required for --online doctor")
                result["board"] = MiroClient(config.access_token()).get_board(config.board_id)
        elif args.command == "render":
            client = None if args.dry_run and not os.environ.get(config.token_env) else MiroClient(config.access_token())
            result = render_board(config, client, create_board=args.create_board, dry_run=args.dry_run)
        elif args.command == "sync":
            result = sync_project(
                config, MiroClient(config.access_token()), direction=args.direction,
                dry_run=args.dry_run, include_layout=args.include_layout,
                confirm_delete=args.confirm_delete, recreate_missing=args.recreate_missing,
                promote_new=args.promote_new,
            )
        else:
            if args.interval_seconds < 30:
                raise ValueError("watch interval must be at least 30 seconds")
            client = MiroClient(config.access_token())
            cycle = 0
            while True:
                cycle += 1
                result = sync_project(
                    config, client, direction="both", dry_run=False,
                    include_layout=args.include_layout, confirm_delete=False,
                    promote_new=False,
                )
                print(json.dumps({"cycle": cycle, **result}, ensure_ascii=False, indent=2, default=str), flush=True)
                if result.get("conflict_count", 0):
                    return 2
                if args.max_cycles and cycle >= args.max_cycles:
                    return 0
                time.sleep(args.interval_seconds)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 2 if result.get("conflict_count", 0) else 0
    except Exception as exc:
        print(f"DDDA Miro error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
