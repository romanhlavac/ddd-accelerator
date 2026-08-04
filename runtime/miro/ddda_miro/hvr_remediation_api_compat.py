from __future__ import annotations

"""Compatibility entry point for a deterministic Miro text-item update defect.

Miro currently returns HTTP 500 when fontSize is changed on the existing
Control Center instruction text item. Creating an equivalent text item with the
same REST representation succeeds. This module keeps the REM-012.3 product
contract unchanged while replacing only that one item through create/verify/
cleanup semantics. The original implementation remains the canonical broker.
"""

from copy import deepcopy
from pathlib import Path
from typing import Any

from . import hvr_remediation as base
from .anchor_contract import _get_item, _seg
from .client import MiroApiError

REPLACED_TEXT_ITEM_ID = "3458764679756505810"
REPLACEMENT_STYLE = {
    "fillColor": "#ffffff",
    "fillOpacity": "0.0",
    "fontFamily": "arial",
    "fontSize": 36,
    "textAlign": "left",
    "color": "#365a8c",
}
_CREATED_REPLACEMENT_IDS: list[str] = []
_ORIGINAL_LOAD = base._load
_ORIGINAL_APPLY_UPDATE = base._apply_update
_ORIGINAL_ROLLBACK = base._rollback


def _compat_load(path: Path) -> dict[str, Any]:
    manifest = _ORIGINAL_LOAD(path)
    matches = [item for item in manifest["updates"] if str(item.get("id") or "") == REPLACED_TEXT_ITEM_ID]
    if len(matches) != 1 or str(matches[0].get("type") or "") != "text":
        raise ValueError("REM-012.3 compatibility replacement identity mismatch")
    matches[0]["replace_by_create"] = True
    cleanup = [str(item) for item in manifest.get("cleanup_ids") or []]
    if REPLACED_TEXT_ITEM_ID not in cleanup:
        cleanup.append(REPLACED_TEXT_ITEM_ID)
    manifest["cleanup_ids"] = cleanup
    return manifest


def _replacement_payload(target_frame_id: str, update: dict[str, Any]) -> dict[str, Any]:
    style = deepcopy(REPLACEMENT_STYLE)
    style["fontSize"] = int(update["font_size"])
    return {
        "data": {"content": str(update["content"])},
        "style": style,
        "geometry": {"width": float(update["width"])},
        "position": {
            "x": float(update["x"]),
            "y": float(update["y"]),
            "origin": "center",
        },
        "parent": {"id": str(target_frame_id)},
    }


def _compat_apply_update(
    client: Any,
    board: str,
    frames: dict[str, str],
    update: dict[str, Any],
    snapshots: dict[str, Any],
) -> str:
    if not bool(update.get("replace_by_create")):
        return _ORIGINAL_APPLY_UPDATE(client, board, frames, update, snapshots)

    target_frame_id = str(frames[str(update["frame"])])
    payload = _replacement_payload(target_frame_id, update)
    exact = [
        item
        for item in client.list_items(board, "text")
        if str(item.get("id") or "") != REPLACED_TEXT_ITEM_ID
        and base._same_item(item, payload)
    ]
    if len(exact) > 1:
        raise ValueError("duplicate REM-012.3 replacement instruction texts")
    if exact:
        return "unchanged"

    try:
        original = _get_item(client, board, REPLACED_TEXT_ITEM_ID)
    except MiroApiError as exc:
        if exc.status != 404:
            raise
        original = None
    if original is None:
        raise ValueError("replacement instruction text is absent and no exact replacement exists")
    if str((original.get("parent") or {}).get("id") or "") != target_frame_id:
        raise ValueError("replacement instruction source is outside the authorized Control Center")

    created = client._request("POST", f"boards/{_seg(board)}/texts", body=payload)
    if not base._same_item(created, payload):
        try:
            client.delete_item(board, str(created.get("id") or ""))
        finally:
            raise ValueError("created replacement instruction text did not reach target")
    created_id = str(created["id"])
    _CREATED_REPLACEMENT_IDS.append(created_id)
    return "updated"


def _compat_rollback(
    client: Any,
    board: str,
    snapshots: dict[str, Any],
    created_native: list[str],
    images_before: set[str],
    image_manifest_id: str,
) -> dict[str, Any]:
    result = _ORIGINAL_ROLLBACK(
        client,
        board,
        snapshots,
        created_native,
        images_before,
        image_manifest_id,
    )
    errors = list(result.get("errors") or [])
    for item_id in reversed(_CREATED_REPLACEMENT_IDS):
        try:
            client.delete_item(board, item_id)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"replacement text {item_id}: {exc}")
    _CREATED_REPLACEMENT_IDS.clear()
    return {"status": "PASS" if not errors else "PARTIAL", "errors": errors}


def main(argv: list[str] | None = None) -> int:
    base._load = _compat_load
    base._apply_update = _compat_apply_update
    base._rollback = _compat_rollback
    try:
        return base.main(argv)
    finally:
        base._load = _ORIGINAL_LOAD
        base._apply_update = _ORIGINAL_APPLY_UPDATE
        base._rollback = _ORIGINAL_ROLLBACK
        _CREATED_REPLACEMENT_IDS.clear()


if __name__ == "__main__":
    raise SystemExit(main())
