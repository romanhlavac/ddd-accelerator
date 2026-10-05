#!/usr/bin/env python3
"""Read-only adapter: fresh PR metadata into the S1 Governance Kernel."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from runtime.platform.governance_kernel import evaluate_release_candidate_pr_identity


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-json", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--kind", choices=("NORMAL", "RECOVERY"), required=True)
    parser.add_argument("--operation", choices=("validate", "publish_hrdr_scaffold",
                        "release_scope_validation", "promotion_dry_run", "release"),
                        default="validate")
    args = parser.parse_args()
    pr = json.loads(args.pr_json.read_text(encoding="utf-8-sig"))
    if not isinstance(pr, dict):
        parser.error("PR JSON must be an object")
    head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
    base = pr.get("base") if isinstance(pr.get("base"), dict) else {}
    ref = str(head.get("ref") or "")
    suffix = ref.rsplit("-v", 1)[-1] if "-v" in ref else ""
    generation = int(suffix) if suffix.isdigit() and int(suffix) >= 2 else 1
    context = {
        "schema_version": 1,
        "context_kind": "ddda_candidate_context",
        "candidate_kind": args.kind,
        "release_mode": "CONTROLLED_RECOVERY" if args.kind == "RECOVERY" else "STANDARD",
        "operation": args.operation,
        "repository": args.repository,
        "pr": args.pr,
        "base_branch": str(base.get("ref") or ""),
        "source_branch": ref,
        "source_sha": args.source_sha,
        "version": args.version,
        "generation": generation,
        "pr_state": "MERGED_CLOSED" if pr.get("state") != "open"
                    else ("DRAFT" if pr.get("draft") is True else "READY"),
        "validation_evidence": None,
        "authoritative_check_summary": None,
        "human_review_reference": None,
        "hrdr_reference": None,
        "physical_scope_reference": None,
        "project_evidence_reference": None,
    }
    decision = evaluate_release_candidate_pr_identity(context, pr)
    print(json.dumps(decision.as_dict(), sort_keys=True))
    return 0 if decision.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
