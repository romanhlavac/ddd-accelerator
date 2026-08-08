from __future__ import annotations

from typing import Any

from . import review_board_recovery as base
from . import review_board_recovery_wirefix as wirefix
from .frame01_redline import same_item


frame00_state_accepted_container = wirefix.frame00_state_accepted_container
_frame00_items_state = wirefix._frame00_items_state
frame00_payload = wirefix.frame00_payload


def _frame_top_left(frame: dict[str, Any]) -> tuple[float, float]:
    geometry = frame.get("geometry") or {}
    position = frame.get("position") or {}
    return (
        float(position["x"]) - float(geometry["width"]) / 2.0,
        float(position["y"]) - float(geometry["height"]) / 2.0,
    )


def _validate_target_envelope(contract: dict[str, Any]) -> None:
    target_width = float(contract["frame"]["width"])
    target_height = float(contract["frame"]["height"])
    updates = list(contract.get("managed_updates") or [])
    if len(updates) != 8:
        raise ValueError("Frame 00 accepted contract must contain exactly eight managed items")

    for update in updates:
        role = str(update.get("role") or "")
        width = float(update.get("width") or 0)
        visual_height = float(update.get("height") or update.get("visual_height") or 0)
        x = float(update.get("x") or 0)
        y = float(update.get("y") or 0)
        if not role or width <= 0 or visual_height <= 0:
            raise ValueError(f"Frame 00 role {role or '<missing>'} has invalid accepted visual bounds")
        left, right = x - width / 2.0, x + width / 2.0
        top, bottom = y - visual_height / 2.0, y + visual_height / 2.0
        if left < 0 or top < 0 or right > target_width or bottom > target_height:
            raise ValueError(
                f"Frame 00 role {role} does not fit accepted {target_width}x{target_height} bounds"
            )


def _create_accepted_children(
    client: Any, manifest: dict[str, Any], contract: dict[str, Any]
) -> dict[str, str]:
    board, frame_id = str(manifest["board_id"]), str(manifest["frame00_id"])
    mapping: dict[str, str] = {}
    created_ids: list[str] = []
    try:
        for update in contract["managed_updates"]:
            item_type = str(update["type"])
            payload = frame00_payload(update, frame_id, manifest)
            created = client._request(
                "POST", f"boards/{base._seg(board)}/{base.EP[item_type]}", body=payload
            )
            item_id = str(created["id"])
            created_ids.append(item_id)
            fresh = client._request(
                "GET", f"boards/{base._seg(board)}/items/{base._seg(item_id)}"
            )
            if not same_item(fresh, payload):
                raise ValueError(
                    f"recovered Frame 00 role {update['role']} read-back mismatch before parent resize"
                )
            mapping[str(update["role"])] = item_id
    except Exception as exc:
        rollback_errors: list[str] = []
        for item_id in reversed(created_ids):
            try:
                client.delete_item(board, item_id)
            except Exception as rollback_exc:  # pragma: no cover - defensive external rollback
                rollback_errors.append(f"{item_id}: {rollback_exc}")
        if rollback_errors:
            raise ValueError(
                "Frame 00 child creation failed and rollback was incomplete: "
                + "; ".join(rollback_errors)
            ) from exc
        raise
    return mapping


def _reapply_accepted_children(
    client: Any,
    manifest: dict[str, Any],
    contract: dict[str, Any],
    mapping: dict[str, str],
) -> int:
    board, frame_id = str(manifest["board_id"]), str(manifest["frame00_id"])
    updated = 0
    for update in contract["managed_updates"]:
        role = str(update["role"])
        item_id = mapping[role]
        payload = frame00_payload(update, frame_id, manifest)
        fresh = client._request(
            "GET", f"boards/{base._seg(board)}/items/{base._seg(item_id)}"
        )
        if same_item(fresh, payload):
            continue
        endpoint = base.EP[str(update["type"])]
        client._request(
            "PATCH",
            f"boards/{base._seg(board)}/{endpoint}/{base._seg(item_id)}",
            body=payload,
        )
        fresh = client._request(
            "GET", f"boards/{base._seg(board)}/items/{base._seg(item_id)}"
        )
        if not same_item(fresh, payload):
            raise ValueError(
                f"recovered Frame 00 role {role} read-back mismatch after parent resize"
            )
        updated += 1
    return updated


def restore_frame00_accepted_geometry_preserve_top_left(
    client: Any, manifest: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    """Ensure accepted children exist first, then atomically resize Frame 00 around them."""
    board, frame_id = str(manifest["board_id"]), str(manifest["frame00_id"])
    target_width = float(contract["frame"]["width"])
    target_height = float(contract["frame"]["height"])
    _validate_target_envelope(contract)

    already_ok, mapping = frame00_state_accepted_container(client, manifest, contract)
    if already_ok:
        frame = base._get_frame(client, board, frame_id)
        return {
            "created": 0,
            "deleted": 0,
            "connectors_deleted": 0,
            "updated": 0,
            "unchanged": 8,
            "role_ids": mapping,
            "container_resized": 0,
            "container_moved": 0,
            "top_left_preserved": True,
            "container_geometry": dict(frame.get("geometry") or {}),
            "container_position": dict(frame.get("position") or {}),
        }

    frame_before = base._get_frame(client, board, frame_id)
    old_top_left = _frame_top_left(frame_before)
    current_geometry = frame_before.get("geometry") or {}
    if (
        float(current_geometry.get("width") or 0) < target_width
        or float(current_geometry.get("height") or 0) < target_height
    ):
        raise ValueError("Frame 00 current container is smaller than the accepted target geometry")

    resized = not (
        base._close(current_geometry.get("width"), target_width)
        and base._close(current_geometry.get("height"), target_height)
    )

    children = base._children(client, board, frame_id)
    created_count = 0
    if children:
        if len(children) != 8:
            raise ValueError(
                "Frame 00 is partially populated; refusing destructive or ambiguous recovery"
            )
        items_ok, mapping = _frame00_items_state(client, manifest, contract)
        if not items_ok:
            raise ValueError(
                "Frame 00 populated state does not match the accepted eight-item contract; refusing destructive recovery"
            )
    else:
        mapping = _create_accepted_children(client, manifest, contract)
        created_count = 8
        populated = base._children(client, board, frame_id)
        if len(populated) != 8:
            raise ValueError("Frame 00 accepted children did not converge before parent resize")
        items_ok, verified_before_resize = _frame00_items_state(client, manifest, contract)
        if not items_ok:
            raise ValueError("Frame 00 accepted children failed pre-resize contract verification")
        mapping = verified_before_resize

    related = base._related_connectors(
        client, board, {str(item["id"]) for item in base._children(client, board, frame_id)}
    )
    if related:
        raise ValueError("Frame 00 accepted contract must not contain connectors")

    moved = 0
    if resized:
        frame_populated = base._get_frame(client, board, frame_id)
        resize_payload = wirefix.frame00_container_payload_preserve_top_left(
            frame_populated, target_width, target_height
        )
        current_position = frame_populated.get("position") or {}
        target_position = resize_payload.get("position") or {}
        moved = int(
            not (
                base._close(current_position.get("x"), target_position.get("x"))
                and base._close(current_position.get("y"), target_position.get("y"))
            )
        )
        client.update_item(board, "frame", frame_id, resize_payload)

    frame_after_resize = base._get_frame(client, board, frame_id)
    geometry = frame_after_resize.get("geometry") or {}
    new_top_left = _frame_top_left(frame_after_resize)
    if not (
        base._close(geometry.get("width"), target_width)
        and base._close(geometry.get("height"), target_height)
    ):
        raise ValueError("Frame 00 populated-frame resize did not converge to accepted geometry")
    if not (
        base._close(old_top_left[0], new_top_left[0])
        and base._close(old_top_left[1], new_top_left[1])
    ):
        raise ValueError("Frame 00 top-left changed during populated atomic resize")

    updated = _reapply_accepted_children(client, manifest, contract, mapping)
    ok, verified = frame00_state_accepted_container(client, manifest, contract)
    if not ok:
        raise ValueError("Frame 00 did not reach the accepted visual contract")

    return {
        "created": created_count,
        "deleted": 0,
        "connectors_deleted": 0,
        "updated": updated,
        "unchanged": 0 if created_count else 8 - updated,
        "role_ids": verified,
        "container_resized": int(resized),
        "container_moved": moved,
        "top_left_preserved": True,
        "container_geometry": dict(frame_after_resize.get("geometry") or {}),
        "container_position": dict(frame_after_resize.get("position") or {}),
    }


def main(argv: list[str] | None = None) -> int:
    original = wirefix.restore_frame00_accepted_geometry_preserve_top_left
    wirefix.restore_frame00_accepted_geometry_preserve_top_left = (
        restore_frame00_accepted_geometry_preserve_top_left
    )
    try:
        return wirefix.main(argv)
    finally:
        wirefix.restore_frame00_accepted_geometry_preserve_top_left = original


if __name__ == "__main__":
    raise SystemExit(main())
