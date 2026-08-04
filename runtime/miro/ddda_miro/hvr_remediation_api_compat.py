from __future__ import annotations

"""Compatibility entry point for deterministic Miro item and source-contract defects.

Miro currently returns HTTP 500 when fontSize is changed on the existing
Control Center instruction text item. It also accepts width updates for
existing sticky notes but keeps their original width on read-back. Creating
replacement items with the intended REST representation succeeds.

The source onboarding frame contains seven supported native child items and
four images. One of those images is already transported independently as the
pinned ``align-bmc`` asset. The original REM-012.3 manifest counted that image
as an eighth native item. This module validates the exact source identity and
normalizes the effective native-clone contract to seven items.

The original implementation remains the canonical broker.
"""

from copy import deepcopy
from pathlib import Path
from typing import Any

from . import hvr_remediation as base
from .anchor_contract import _close, _get_item, _seg, canonical_miro_text
from .client import MiroApiError

REPLACED_TEXT_ITEM_ID = "3458764679756505810"
REPLACED_STICKY_ITEM_TOKENS = {
    "3458764679756548469": "acceptance-claims-modernization.project-charter",
    "3458764679756548472": "ddda.current-status",
    "3458764679756548475": "ddda.next-actions",
}
REPLACED_ITEM_TYPES = {
    REPLACED_TEXT_ITEM_ID: "text",
    **{item_id: "sticky_note" for item_id in REPLACED_STICKY_ITEM_TOKENS},
}
ALIGN_ONBOARDING_NATIVE_COUNT = 7
ALIGN_ONBOARDING_PINNED_IMAGE_ID = "align-bmc"
ALIGN_ONBOARDING_PINNED_SOURCE_ITEM_ID = "3458764567890733049"
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
    updates = {str(item.get("id") or ""): item for item in manifest["updates"]}
    if set(REPLACED_ITEM_TYPES) - set(updates):
        raise ValueError("REM-012.3 compatibility replacement identity mismatch")
    for item_id, item_type in REPLACED_ITEM_TYPES.items():
        update = updates[item_id]
        if str(update.get("type") or "") != item_type:
            raise ValueError(f"REM-012.3 replacement type mismatch for {item_id}")
        update["replace_by_create"] = True
    cleanup = [str(item) for item in manifest.get("cleanup_ids") or []]
    for item_id in REPLACED_ITEM_TYPES:
        if item_id not in cleanup:
            cleanup.append(item_id)
    manifest["cleanup_ids"] = cleanup

    clones = {str(item.get("name") or ""): item for item in manifest["native_clones"]}
    align_clone = clones.get("align-onboarding")
    if not isinstance(align_clone, dict):
        raise ValueError("REM-012.3 align-onboarding clone is missing")
    declared_count = int(align_clone.get("expected_supported_count") or 0)
    if declared_count not in {ALIGN_ONBOARDING_NATIVE_COUNT, ALIGN_ONBOARDING_NATIVE_COUNT + 1}:
        raise ValueError(f"unexpected align-onboarding declared count: {declared_count}")
    align_clone["expected_supported_count"] = ALIGN_ONBOARDING_NATIVE_COUNT

    images = {
        str(item.get("id") or ""): item
        for item in (manifest.get("images") or {}).get("assets") or []
    }
    pinned = images.get(ALIGN_ONBOARDING_PINNED_IMAGE_ID)
    if (
        not isinstance(pinned, dict)
        or str(pinned.get("source_item_id") or "") != ALIGN_ONBOARDING_PINNED_SOURCE_ITEM_ID
        or str(pinned.get("source_frame_id") or "") != str(align_clone.get("source_frame_id") or "")
        or str(pinned.get("target_frame") or "") != "align"
    ):
        raise ValueError("REM-012.3 align onboarding pinned-image identity mismatch")
    return manifest


def _replacement_payload(
    target_frame_id: str,
    update: dict[str, Any],
    original: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item_type = str(update["type"])
    if item_type == "text":
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
    if item_type != "sticky_note" or original is None:
        raise ValueError(f"replacement source is required for {item_type}")
    payload = base._writable(original)
    payload["parent"] = {"id": str(target_frame_id)}
    payload["position"] = {
        "x": float(update["x"]),
        "y": float(update["y"]),
        "origin": "center",
    }
    payload["geometry"] = {"width": float(update["width"])}
    return payload


def _sticky_replacement_matches(
    remote: dict[str, Any],
    target_frame_id: str,
    update: dict[str, Any],
    identity_token: str,
) -> bool:
    position = remote.get("position") or {}
    geometry = remote.get("geometry") or {}
    content = canonical_miro_text((remote.get("data") or {}).get("content"))
    return (
        str(remote.get("type") or "") == "sticky_note"
        and str((remote.get("parent") or {}).get("id") or "") == str(target_frame_id)
        and _close(position.get("x"), update["x"])
        and _close(position.get("y"), update["y"])
        and _close(geometry.get("width"), update["width"])
        and identity_token in content
    )


def _compat_apply_update(
    client: Any,
    board: str,
    frames: dict[str, str],
    update: dict[str, Any],
    snapshots: dict[str, Any],
) -> str:
    if not bool(update.get("replace_by_create")):
        return _ORIGINAL_APPLY_UPDATE(client, board, frames, update, snapshots)

    item_id = str(update["id"])
    item_type = str(update["type"])
    target_frame_id = str(frames[str(update["frame"])])
    try:
        original = _get_item(client, board, item_id)
    except MiroApiError as exc:
        if exc.status != 404:
            raise
        original = None

    if original is not None and str((original.get("parent") or {}).get("id") or "") != target_frame_id:
        raise ValueError(f"replacement source {item_id} is outside the authorized Control Center")

    candidates = [
        item
        for item in client.list_items(board, item_type)
        if str(item.get("id") or "") != item_id
    ]
    if item_type == "sticky_note" and original is None:
        identity_token = REPLACED_STICKY_ITEM_TOKENS[item_id]
        exact = [
            item
            for item in candidates
            if _sticky_replacement_matches(item, target_frame_id, update, identity_token)
        ]
        if len(exact) > 1:
            raise ValueError(f"duplicate REM-012.3 sticky replacement for {item_id}")
        if exact:
            return "unchanged"
        raise ValueError(f"replacement sticky {item_id} is absent and no exact replacement exists")

    payload = _replacement_payload(target_frame_id, update, original)
    exact = [item for item in candidates if base._same_item(item, payload)]
    if len(exact) > 1:
        raise ValueError(f"duplicate REM-012.3 replacement for {item_id}")
    if exact:
        return "unchanged"
    if original is None:
        raise ValueError(f"replacement source {item_id} is absent and no exact replacement exists")

    created = client._request("POST", f"boards/{_seg(board)}/{base.ENDPOINT[item_type]}", body=payload)
    if not base._same_item(created, payload):
        try:
            client.delete_item(board, str(created.get("id") or ""))
        finally:
            raise ValueError(f"created replacement {item_id} did not reach target")
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
            errors.append(f"replacement item {item_id}: {exc}")
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
