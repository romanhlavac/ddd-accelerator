from __future__ import annotations

from typing import Any

from . import review_board_recovery as base

_ORIGINAL_FRAME00_PAYLOAD = base.frame00_payload
_ORIGINAL_RESIZE_FRAME00 = base._resize_frame00
_ORIGINAL_RESTORE_FRAME00 = base.restore_frame00


def frame00_payload(update: dict[str, Any], frame_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    """Return the REM-012.5 Frame-00 payload without Miro read-only position metadata."""
    payload = _ORIGINAL_FRAME00_PAYLOAD(update, frame_id, manifest)
    position = dict(payload.get("position") or {})
    position.pop("relativeTo", None)
    payload["position"] = position
    return payload


def frame_patch_preserving_top_left(frame: dict[str, Any], target_geometry: dict[str, float]) -> dict[str, Any]:
    """Resize a frame while preserving its board-absolute top-left anchor."""
    geometry = dict(frame.get("geometry") or {})
    position = dict(frame.get("position") or {})
    for key in ("width", "height"):
        if key not in geometry:
            raise ValueError(f"Frame 00 current geometry is missing {key}")
    for key in ("x", "y"):
        if key not in position:
            raise ValueError(f"Frame 00 current position is missing {key}")

    old_width = float(geometry["width"])
    old_height = float(geometry["height"])
    old_x = float(position["x"])
    old_y = float(position["y"])
    new_width = float(target_geometry["width"])
    new_height = float(target_geometry["height"])

    top_left_x = old_x - old_width / 2.0
    top_left_y = old_y - old_height / 2.0
    return {
        "geometry": {"width": new_width, "height": new_height},
        "position": {
            "x": top_left_x + new_width / 2.0,
            "y": top_left_y + new_height / 2.0,
            "origin": "center",
        },
    }


def resize_frame00_preserving_top_left(client: Any, board: str, frame_id: str, contract: dict[str, Any]) -> None:
    target = {"width": float(contract["frame"]["width"]), "height": float(contract["frame"]["height"])}
    current = base._get_frame(client, board, frame_id)
    if base._close((current.get("geometry") or {}).get("width"), target["width"]) and base._close((current.get("geometry") or {}).get("height"), target["height"]):
        return

    payload = frame_patch_preserving_top_left(current, target)
    base._patch(client, board, "frame", frame_id, payload)
    fresh = base._get_frame(client, board, frame_id)
    if not (
        base._close((fresh.get("geometry") or {}).get("width"), target["width"])
        and base._close((fresh.get("geometry") or {}).get("height"), target["height"])
        and base._close((fresh.get("position") or {}).get("x"), payload["position"]["x"])
        and base._close((fresh.get("position") or {}).get("y"), payload["position"]["y"])
    ):
        raise ValueError("Frame 00 top-left-preserving resize did not converge")


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


def restore_frame00_without_recreating_matching_children(client: Any, manifest: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    board, frame_id = str(manifest["board_id"]), str(manifest["frame00_id"])
    items_ok, mapping = _frame00_items_state(client, manifest, contract)
    if items_ok:
        resize_frame00_preserving_top_left(client, board, frame_id, contract)
        ok, verified = base.frame00_state(client, manifest, contract)
        if not ok:
            raise ValueError("Frame 00 accepted children matched before resize but final accepted contract did not converge")
        return {"created": 0, "deleted": 0, "connectors_deleted": 0, "unchanged": 8, "role_ids": verified or mapping}
    return _ORIGINAL_RESTORE_FRAME00(client, manifest, contract)


def main(argv: list[str] | None = None) -> int:
    original_payload = base.frame00_payload
    original_resize = base._resize_frame00
    original_restore = base.restore_frame00
    base.frame00_payload = frame00_payload
    base._resize_frame00 = resize_frame00_preserving_top_left
    base.restore_frame00 = restore_frame00_without_recreating_matching_children
    try:
        return base.main(argv)
    finally:
        base.frame00_payload = original_payload
        base._resize_frame00 = original_resize
        base.restore_frame00 = original_restore


if __name__ == "__main__":
    raise SystemExit(main())
