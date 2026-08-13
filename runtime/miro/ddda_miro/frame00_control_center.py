from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .anchor_contract import _close, _get_frame, _protected_snapshot, canonical_miro_text
from .client import MiroClient
from .frame00_contract import (
    EXPECTED_ROLES,
    REMEDIATION_ID,
    _matches,
    _selector_matches,
    _target_payload,
    load_contract,
)
from .frame00_reconcile import reconcile_once, rollback


def _verify_remote(client: MiroClient, contract: dict[str, Any]) -> dict[str, Any]:
    board, frame_id = str(contract["board_id"]), str(contract["frame"]["id"])
    items = [item for item in client.list_items(board) if str((item.get("parent") or {}).get("id") or "") == frame_id]
    text = " ".join(canonical_miro_text((item.get("data") or {}).get("content")) for item in items)
    for phrase in contract["verification"]["required_phrases"]:
        if str(phrase) not in text:
            raise ValueError(f"remote frame 00 missing: {phrase}")
    for phrase in contract["verification"]["forbidden_phrases"]:
        if str(phrase) in text:
            raise ValueError(f"remote frame 00 retains: {phrase}")
    remote_by_id = {str(item.get("id") or ""): item for item in items}
    for update in contract["managed_updates"]:
        remote = remote_by_id.get(str(update["id"]))
        if remote is None or not _matches(remote, _target_payload(remote, update, frame_id)):
            raise ValueError(f"read-back failed for {update['role']}")
    managed_ids = {str(item["id"]) for item in contract["managed_updates"]}
    residual = sum(
        1 for selector in contract["cleanup"].get("selectors") or [] for item in items
        if str(item.get("id") or "") not in managed_ids and _selector_matches(item, selector)
    )
    if residual:
        raise ValueError(f"frame 00 retains {residual} superseded generated items")
    roles = {item["role"]: item for item in contract["managed_updates"]}
    if int(roles["decision_now"]["font_size"]) <= int(roles["artifact_status"]["font_size"]):
        raise ValueError("decision must dominate Artifact Health")
    if float(roles["artifact_panel"]["y"]) <= float(roles["decision_now"]["y"]):
        raise ValueError("Artifact Health must remain in the lower zone")
    return {"status": "PASS", "managed_item_count": 8, "frame_item_count": len(items), "residual_cleanup_matches": 0}


def apply_remediation(client: MiroClient, contract: dict[str, Any], source_sha: str | None = None) -> dict[str, Any]:
    board, frame_id = str(contract["board_id"]), str(contract["frame"]["id"])
    geometry = (_get_frame(client, board, frame_id).get("geometry") or {})
    if not _close(geometry.get("width"), contract["frame"]["width"]) or not _close(geometry.get("height"), contract["frame"]["height"]):
        raise ValueError("frame 00 geometry mismatch")
    protected_ids = [str(item) for item in contract["protected_frame_ids"]]
    before = _protected_snapshot(client, board, protected_ids)
    original: dict[str, dict[str, Any]] = {}
    deleted: list[dict[str, Any]] = []
    try:
        first = reconcile_once(client, contract, original, deleted)
        if _protected_snapshot(client, board, protected_ids)["digest"] != before["digest"]:
            raise ValueError("protected frames changed in first reconcile")
        second = reconcile_once(client, contract, original, deleted)
        if second["updated"] or second["deleted"] or second["unchanged"] != 8:
            raise ValueError(f"second reconcile is not zero mutation: {second}")
        verification = _verify_remote(client, contract)
        after = _protected_snapshot(client, board, protected_ids)
        if after["digest"] != before["digest"]:
            raise ValueError("protected frames changed")
        return {
            "status": "PASS", "remediation_id": REMEDIATION_ID, "source_sha": source_sha,
            "board_id": board, "frame_id": frame_id, "first_run": first, "second_run": second,
            "remote_verification": verification,
            "protected_frames": {"status": "PASS", "count": 17, "before_digest": before["digest"], "after_digest": after["digest"], "unchanged": True},
            "merge_allowed": False, "promotion_allowed": False, "release_allowed": False, "gate_approval_allowed": False,
            "technical_status": "PASS", "human_review_status": "PENDING", "overall_status": "READY_FOR_HUMAN_REVIEW",
        }
    except Exception as exc:
        state = rollback(client, board, original, deleted)
        raise RuntimeError(f"REM-012.4 failed; rollback={state}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ddda_miro.frame00_control_center")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source-sha")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        contract = load_contract(args.manifest)
        report = apply_remediation(MiroClient(os.environ["MIRO_ACCESS_TOKEN"]), contract, args.source_sha) if args.apply else {
            "status": "DRY_RUN", "remediation_id": REMEDIATION_ID, "board_id": contract["board_id"],
            "frame_id": contract["frame"]["id"], "managed_item_count": 8, "protected_frame_count": 17,
        }
        code = 0
    except Exception as exc:  # noqa: BLE001
        report = {"status": "FAIL", "remediation_id": REMEDIATION_ID, "source_sha": args.source_sha, "error": str(exc),
                  "technical_status": "FAIL", "human_review_status": "PENDING", "overall_status": "CHANGES_REQUIRED"}
        code = 1
        print(f"DDDA REM-012.4 error: {exc}", file=sys.stderr)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if code == 0:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
