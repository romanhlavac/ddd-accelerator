from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .anchor_contract import (
    _item_matches, _protected_snapshot, _target_payload, detect_board_state, load_manifest,
)
from .anchor_plan import (
    _apply_frame, _apply_update, _assert_no_connected_deletions, _deletion_candidates,
    _journey_updates, _park_dynamic_obsolete_items,
)
from .anchor_evidence import (
    _delete_if_present, _image_manifest, _rollback, _verify_images, _verify_no_anchor_overlap,
    _verify_table,
)
from .client import MiroApiError, MiroClient
from .image_transport import reconcile as reconcile_images

# Re-export selected helpers for the remediation contract tests.
__all__ = [
    "apply_remediation", "detect_board_state", "load_manifest", "_deletion_candidates",
    "_image_manifest", "_item_matches", "_protected_snapshot", "_target_payload",
    "_verify_no_anchor_overlap",
]


def apply_remediation(client: MiroClient, manifest: dict[str, Any], source_sha: str | None = None):
    board = str(manifest["board_id"])
    if source_sha and os.environ.get("GITHUB_SHA") and source_sha != os.environ["GITHUB_SHA"]:
        raise ValueError("source SHA does not match GITHUB_SHA")
    state, _ = detect_board_state(client, manifest)
    frame_ids = {key: str(spec["id"]) for key, spec in manifest["frames"].items()}
    protected_before = _protected_snapshot(client, board, [str(item) for item in manifest["protected_frames"]])
    deletion_ids = _deletion_candidates(client, manifest, state)
    _assert_no_connected_deletions(client, board, deletion_ids)
    _verify_table(client, manifest)
    frame_snapshots, item_snapshots = {}, {}
    images_before = {str(item.get("id") or "") for item in client.list_items(board, "image")}
    irreversible = False
    try:
        item_result = {"updated": 0, "unchanged": 0}
        for update in list(manifest["updates"]) + _journey_updates(client, manifest, state):
            item_result[_apply_update(client, board, update, frame_ids, item_snapshots)] += 1
        parked = _park_dynamic_obsolete_items(client, manifest, state, item_snapshots)
        frame_result = {"updated": 0, "unchanged": 0}
        for key, spec in manifest["frames"].items():
            frame_result[_apply_frame(client, board, key, spec, frame_snapshots)] += 1
        image_manifest = _image_manifest(manifest)
        first = reconcile_images(client, board, frame_ids, image_manifest)
        first_remote = _verify_images(client, board, frame_ids, image_manifest, first)
        second = reconcile_images(client, board, frame_ids, image_manifest)
        second_remote = _verify_images(client, board, frame_ids, image_manifest, second)
        if {i["asset_id"]: i["target_item_id"] for i in first["assets"]} != {i["asset_id"]: i["target_item_id"] for i in second["assets"]} or second["created"] or second["updated"] or second["unchanged"] != 17:
            raise ValueError(f"managed image second run is not stable zero mutation: {second}")
        geometry, table = _verify_no_anchor_overlap(client, manifest), _verify_table(client, manifest)
        if _protected_snapshot(client, board, [str(item) for item in manifest["protected_frames"]])["digest"] != protected_before["digest"]:
            raise ValueError("protected frames 20+ changed before cleanup")
        irreversible = True
        deleted = {item: _delete_if_present(client, board, item) for item in deletion_ids}
        remaining = []
        for item in deletion_ids:
            try:
                _get_item(client, board, item)
            except MiroApiError as exc:
                if exc.status == 404:
                    continue
                raise
            remaining.append(item)
        if remaining:
            raise ValueError(f"obsolete items remain: {remaining}")
        _deletion_candidates(client, manifest, "target")
        protected_after = _protected_snapshot(client, board, [str(item) for item in manifest["protected_frames"]])
        if protected_after["digest"] != protected_before["digest"]:
            raise ValueError("protected frames 20+ changed during cleanup")
        return {"status": "PASS", "remediation_id": str(manifest["remediation_id"]), "source_sha": source_sha, "board_id": board, "initial_board_state": state, "frames": frame_result, "items": item_result, "parked_obsolete_items": parked, "images": {"asset_count": 17, "first_run": first, "second_run": second, "remote_verification": {"status": "PASS", "items": second_remote["items"], "first_run": first_remote, "second_run": second_remote}, "stable_item_ids": True, "zero_mutation_second_run": True}, "native_table": table, "geometry": geometry, "deleted": deleted, "protected_frames": {"status": "PASS", "count": 15, "before_digest": protected_before["digest"], "after_digest": protected_after["digest"], "unchanged": True}, "technical_status": "PASS", "human_review_status": "PENDING", "overall_status": "READY_FOR_HUMAN_REVIEW"}
    except Exception as exc:
        rollback = {"status": "NOT_ATTEMPTED", "reason": "irreversible cleanup already started"} if irreversible else _rollback(client, board, frame_snapshots, item_snapshots, images_before, str(manifest["images"]["manifest_id"]))
        raise RuntimeError(f"REM-012.2 failed; rollback={rollback}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ddda_miro.anchor_remediation")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source-sha")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest.resolve())
        report = apply_remediation(MiroClient(os.environ["MIRO_ACCESS_TOKEN"]), manifest, args.source_sha) if args.apply else {"status": "DRY_RUN", "remediation_id": manifest["remediation_id"], "board_id": manifest["board_id"], "asset_count": 17}
        code = 0
    except Exception as exc:  # noqa: BLE001
        report, code = {"status": "FAIL", "error": str(exc), "source_sha": args.source_sha, "technical_status": "FAIL", "human_review_status": "PENDING", "overall_status": "CHANGES_REQUIRED"}, 1
        print(f"DDDA Miro anchor remediation error: {exc}", file=sys.stderr)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if code == 0:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
