from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import review_board_recovery as base

_ORIGINAL_APPLY = base.apply
_ORIGINAL_FRAME00_PAYLOAD = base.frame00_payload
_ORIGINAL_FRAME00_STATE = base.frame00_state
_ORIGINAL_RESTORE_FRAME00 = base.restore_frame00


def frame00_payload(update: dict[str, Any], frame_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    """Return the REM-012.5 Frame-00 payload without Miro read-only position metadata."""
    payload = _ORIGINAL_FRAME00_PAYLOAD(update, frame_id, manifest)
    position = dict(payload.get("position") or {})
    position.pop("relativeTo", None)
    payload["position"] = position
    return payload


def _frame00_items_state(client: Any, manifest: dict[str, Any], contract: dict[str, Any]) -> tuple[bool, dict[str, str]]:
    board, frame_id = str(manifest["board_id"]), str(manifest["frame00_id"])
    items = base._children(client, board, frame_id)
    if len(items) != 8:
        return False, {}
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for update in contract["managed_updates"]:
        expected = frame00_payload(update, frame_id, manifest)
        hits = [item for item in items if str(item.get("id") or "") not in used and base._role_match(item, update, expected)]
        if len(hits) != 1 or not base.same_item(hits[0], expected):
            return False, {}
        item_id = str(hits[0]["id"])
        mapping[str(update["role"])] = item_id
        used.add(item_id)
    if base._related_connectors(client, board, {str(item["id"]) for item in items}):
        return False, {}
    return True, mapping


def frame00_state_allow_relocated_container(client: Any, manifest: dict[str, Any], contract: dict[str, Any]) -> tuple[bool, dict[str, str]]:
    """Validate the accepted eight-item visual contract while deferring container size to human relocation review."""
    return _frame00_items_state(client, manifest, contract)


def restore_frame00_without_container_resize(client: Any, manifest: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    ok, mapping = _frame00_items_state(client, manifest, contract)
    if not ok:
        raise ValueError("relocated Frame 00 no longer matches the Human-accepted eight-item contract")
    return {"created": 0, "deleted": 0, "connectors_deleted": 0, "unchanged": 8, "role_ids": mapping}


def frame01_replacement_payload(old_frame: dict[str, Any], source_frame: dict[str, Any]) -> dict[str, Any]:
    old_geometry = old_frame.get("geometry") or {}
    old_position = old_frame.get("position") or {}
    source_geometry = source_frame.get("geometry") or {}
    for key in ("width", "height"):
        if key not in old_geometry or key not in source_geometry:
            raise ValueError(f"Frame 01 geometry is missing {key}")
    for key in ("x", "y"):
        if key not in old_position:
            raise ValueError(f"Frame 01 position is missing {key}")

    old_width, old_height = float(old_geometry["width"]), float(old_geometry["height"])
    source_width, source_height = float(source_geometry["width"]), float(source_geometry["height"])
    top_left_x = float(old_position["x"]) - old_width / 2.0
    top_left_y = float(old_position["y"]) - old_height / 2.0
    payload: dict[str, Any] = {
        "data": {"title": str((source_frame.get("data") or {}).get("title") or (old_frame.get("data") or {}).get("title") or "01 – DDD Starter journey, gates a iterace")},
        "geometry": {"width": source_width, "height": source_height},
        "position": {"x": top_left_x + source_width / 2.0, "y": top_left_y + source_height / 2.0, "origin": "center"},
    }
    source_style = deepcopy(source_frame.get("style") or {})
    if source_style:
        payload["style"] = source_style
    return payload


def _frame_children_text(client: Any, board: str, frame_id: str) -> str:
    return " ".join(base._visible((item.get("data") or {}).get("content")) for item in base._children(client, board, frame_id))


def _find_recovered_frame01(client: Any, manifest: dict[str, Any], source_frame: dict[str, Any]) -> dict[str, Any] | None:
    board = str(manifest["board_id"])
    source_geometry = source_frame.get("geometry") or {}
    title = str(manifest["source_frame_title"])
    candidates: list[dict[str, Any]] = []
    for frame in client.list_items(board, "frame"):
        if str((frame.get("data") or {}).get("title") or "") != title:
            continue
        geometry = frame.get("geometry") or {}
        if not (base._close(geometry.get("width"), source_geometry.get("width")) and base._close(geometry.get("height"), source_geometry.get("height"))):
            continue
        text = _frame_children_text(client, board, str(frame["id"]))
        if all(str(marker) in text for marker in manifest["source_sentinels"]):
            candidates.append(frame)
    if len(candidates) > 1:
        raise ValueError(f"multiple recovered Frame 01 candidates found: {[item['id'] for item in candidates]}")
    return candidates[0] if candidates else None


def _cleanup_frame(client: Any, board: str, frame_id: str) -> None:
    children = base._children(client, board, frame_id)
    ids = {str(item["id"]) for item in children}
    for connector in base._related_connectors(client, board, ids):
        client.delete_connector(board, str(connector["id"]))
    for item in children:
        client.delete_item(board, str(item["id"]))
    try:
        client.delete_item(board, frame_id)
    except Exception:
        # Cleanup is best-effort here; the caller will still surface the original failure.
        pass


def _delete_old_frame01(client: Any, board: str, old_frame_id: str) -> None:
    children = base._children(client, board, old_frame_id)
    ids = {str(item["id"]) for item in children}
    for connector in base._related_connectors(client, board, ids):
        client.delete_connector(board, str(connector["id"]))
    for item in children:
        client.delete_item(board, str(item["id"]))
    client.delete_item(board, old_frame_id)


def _prepare_frame01_target(client: Any, manifest: dict[str, Any]) -> tuple[str | None, str, bool]:
    board = str(manifest["board_id"])
    source_frame = base._get_frame(client, str(manifest["source_board_id"]), str(manifest["source_frame_id"]))
    recovered = _find_recovered_frame01(client, manifest, source_frame)
    if recovered is not None:
        manifest["frame_id"] = str(recovered["id"])
        return None, str(recovered["id"]), False

    old_frame_id = str(manifest["frame_id"])
    old_frame = base._get_frame(client, board, old_frame_id)
    payload = frame01_replacement_payload(old_frame, source_frame)
    created = client.create_item(board, "frame", payload)
    new_frame_id = str(created["id"])
    manifest["frame_id"] = new_frame_id
    fresh = base._get_frame(client, board, new_frame_id)
    if not (
        base._close((fresh.get("geometry") or {}).get("width"), payload["geometry"]["width"])
        and base._close((fresh.get("geometry") or {}).get("height"), payload["geometry"]["height"])
    ):
        _cleanup_frame(client, board, new_frame_id)
        raise ValueError("new Frame 01 container geometry did not match the approved redline")
    return old_frame_id, new_frame_id, True


def apply_with_relocated_frame00_and_replaced_frame01(client: Any, manifest: dict[str, Any], source_sha: str) -> dict[str, Any]:
    board = str(manifest["board_id"])
    original_static_frame01 = str(manifest["frame_id"])
    old_frame_id: str | None = None
    new_frame_id: str | None = None
    created = False
    try:
        old_frame_id, new_frame_id, created = _prepare_frame01_target(client, manifest)
        result = _ORIGINAL_APPLY(client, manifest, source_sha)
        if created and old_frame_id and old_frame_id != new_frame_id:
            _delete_old_frame01(client, board, old_frame_id)
        frame00 = base._get_frame(client, board, str(manifest["frame00_id"]))
        result["frame00_container"] = {
            "frame_id": str(manifest["frame00_id"]),
            "geometry": dict(frame00.get("geometry") or {}),
            "position": dict(frame00.get("position") or {}),
            "geometry_status": "RELOCATED_CONTAINER_PENDING_HUMAN_EQUIVALENCE_CHECK",
        }
        result["frame01_container"] = {
            "old_frame_id": old_frame_id or original_static_frame01,
            "new_frame_id": str(manifest["frame_id"]),
            "replaced": bool(created),
        }
        result["frame_id"] = str(manifest["frame_id"])
        result["frame00_visual_equivalence_spot_check"] = "PENDING"
        return result
    except Exception:
        if created and new_frame_id:
            _cleanup_frame(client, board, new_frame_id)
        manifest["frame_id"] = original_static_frame01
        raise


def main(argv: list[str] | None = None) -> int:
    original_payload = base.frame00_payload
    original_state = base.frame00_state
    original_restore = base.restore_frame00
    original_apply = base.apply
    base.frame00_payload = frame00_payload
    base.frame00_state = frame00_state_allow_relocated_container
    base.restore_frame00 = restore_frame00_without_container_resize
    base.apply = apply_with_relocated_frame00_and_replaced_frame01
    try:
        return base.main(argv)
    finally:
        base.frame00_payload = original_payload
        base.frame00_state = original_state
        base.restore_frame00 = original_restore
        base.apply = original_apply


if __name__ == "__main__":
    raise SystemExit(main())
