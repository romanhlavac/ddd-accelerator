from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .engine import (
    SteeringError,
    bootstrap,
    generate_status,
    intake_summary,
    json_text,
    review_gate,
    validate_agent_contract,
)


def configure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="ddda-steering", description="DDDA project steering runtime")
    sub = root.add_subparsers(dest="command", required=True)

    summary = sub.add_parser("intake-summary", help="Validate intake and print normalized JSON")
    summary.add_argument("--platform-root", required=True)
    summary.add_argument("--intake", required=True)

    boot = sub.add_parser("bootstrap", help="Create project profile, tailoring, status and gate records")
    boot.add_argument("--platform-root", required=True)
    boot.add_argument("--project-root", required=True)
    boot.add_argument("--intake", required=True)

    status = sub.add_parser("status", help="Regenerate current status and next actions")
    status.add_argument("--platform-root", required=True)
    status.add_argument("--project-root", required=True)

    gate = sub.add_parser("review-gate", help="Record an explicit human gate decision")
    gate.add_argument("--platform-root", required=True)
    gate.add_argument("--project-root", required=True)
    gate.add_argument("--gate", required=True)
    gate.add_argument("--outcome", required=True, choices=["passed", "conditional", "rejected"])
    gate.add_argument("--reviewer", required=True)
    gate.add_argument("--approver", required=True)
    gate.add_argument("--decision-owner", required=True)
    gate.add_argument("--scope", required=True)
    gate.add_argument("--provenance", choices=["human"], default="human")
    gate.add_argument("--note", default=None)
    gate.add_argument("--condition", action="append", default=[])
    gate.add_argument("--condition-owner", default=None)
    gate.add_argument("--condition-due-at", default=None)
    gate.add_argument("--test-simulation", action="store_true")

    contract = sub.add_parser("validate-agent-contract", help="Validate the project agent contract")
    contract.add_argument("--project-root", required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    configure_utf8_streams()
    args = parser().parse_args(argv)
    try:
        if args.command == "intake-summary":
            result = intake_summary(Path(args.intake).resolve(), Path(args.platform_root).resolve())
        elif args.command == "bootstrap":
            result = bootstrap(Path(args.project_root).resolve(), Path(args.intake).resolve(), Path(args.platform_root).resolve())
        elif args.command == "status":
            result = generate_status(Path(args.project_root).resolve(), Path(args.platform_root).resolve())
        elif args.command == "review-gate":
            result = review_gate(
                Path(args.project_root).resolve(),
                Path(args.platform_root).resolve(),
                args.gate,
                args.outcome,
                args.reviewer,
                args.note,
                args.condition,
                decision_owner=args.decision_owner,
                approver=args.approver,
                scope=args.scope,
                provenance=args.provenance,
                condition_owner=args.condition_owner,
                condition_due_at=args.condition_due_at,
                test_simulation=args.test_simulation,
            )
        elif args.command == "validate-agent-contract":
            result = validate_agent_contract(Path(args.project_root).resolve())
            if result["status"] != "ok":
                print(json_text(result))
                return 2
        else:  # pragma: no cover
            raise SteeringError(f"Neznámý příkaz: {args.command}")
        print(json_text(result))
        return 0
    except (SteeringError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
