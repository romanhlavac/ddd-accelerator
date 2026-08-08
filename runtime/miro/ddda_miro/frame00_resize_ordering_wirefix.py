from __future__ import annotations

from typing import Any

from . import review_board_recovery as base
from . import review_board_recovery_wirefix as wirefix


_ORIGINAL_RESTORE_FRAME00 = wirefix._ORIGINAL_RESTORE_FRAME00
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


def _restore_parent_top_left(
    client: Any,
    board: str,
    frame_id: str,
    old_top_left: tuple[float, float],
    target_width: float,
    target_height: float,
) -> int:
    frame = base._get_frame(client, board, frame_id)
    desired_x = old_top_left[0] + target_width / 2.0
    desired_y = old_top_left[1] + target_height / 2.0
    position = frame.get("position") or {}
    moved = not (
        base._close(position.get("x"), desired_x)
        and base._close(position.get("y"), desired_y)
    )
    if moved:
        client.update_item(
            board,
            "frame",
            frame_id,
            {
                "position": {
                    "x": desired_x,
                    "y": desired_y,
                    "origin": "center",
                }
            },
        )
    return int(moved)


def restore_frame00_accepted_geometry_preserve_top_left(
    client: Any, manifest: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    """Shrink Frame 00 only while empty, then recreate the accepted eight children."""
    board, frame_id = str(manifest["board_id"]), str(manifest["frame00_id"])
    target_width = float(contract["frame"]["width"])
    target_height = float(contract["frame"]["height"])

    already_ok, mapping = frame00_state_accepted_container(client, manifest, contract)
    if already_ok:
        frame = base._get_frame(client, board, frame_id)
        return {
            "created": 0,
            "deleted": 0,
            "connectors_deleted": 0,
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
    resized = not (
        base._close((frame_before.get("geometry") or {}).get("width"), target_width)
        and base._close((frame_before.get("geometry") or {}).get("height"), target_height)
    )

    children = base._children(client, board, frame_id)
    if children:
        items_ok, _ = _frame00_items_state(client, manifest, contract)
        if not items_ok:
            raise ValueError(
                "Frame 00 populated state does not match the accepted eight-item contract; refusing destructive recovery"
            )

    child_ids = {str(item["id"]) for item in children}
    related = base._related_connectors(client, board, child_ids)
    for connector in related:
        client.delete_connector(board, str(connector["id"]))
    for item in children:
        client.delete_item(board, str(item["id"]))

    # Hard precondition for the shrink: Miro must report the parent as empty.
    base._wait_frame_empty(client, board, frame_id)

    # review_board_recovery._resize_frame00 is already bounded: it retries the Miro
    # 3.0204 / child-out-of-bounds condition at most five times, then fails closed.
    base._resize_frame00(client, board, frame_id, contract)

    frame_after_shrink = base._get_frame(client, board, frame_id)
    geometry = frame_after_shrink.get("geometry") or {}
    if not (
        base._close(geometry.get("width"), target_width)
        and base._close(geometry.get("height"), target_height)
    ):
        raise ValueError("Frame 00 empty-frame shrink did not converge to accepted geometry")

    moved = _restore_parent_top_left(
        client,
        board,
        frame_id,
        old_top_left,
        target_width,
        target_height,
    )

    # Reuse the existing accepted-child recovery after geometry/top-left are final.
    # Because the parent is already at target geometry and empty, its internal resize is a no-op.
    recovery = _ORIGINAL_RESTORE_FRAME00(client, manifest, contract)

    frame_after = base._get_frame(client, board, frame_id)
    new_top_left = _frame_top_left(frame_after)
    if not (
        base._close((frame_after.get("geometry") or {}).get("width"), target_width)
        and base._close((frame_after.get("geometry") or {}).get("height"), target_height)
    ):
        raise ValueError("Frame 00 geometry changed while recreating accepted children")
    if not (
        base._close(old_top_left[0], new_top_left[0])
        and base._close(old_top_left[1], new_top_left[1])
    ):
        raise ValueError("Frame 00 top-left did not converge after empty-frame shrink recovery")

    ok, verified = frame00_state_accepted_container(client, manifest, contract)
    if not ok:
        raise ValueError("Frame 00 did not reach the accepted visual contract")

    result = dict(recovery)
    result.update(
        {
            "deleted": len(children),
            "connectors_deleted": len(related),
            "role_ids": verified,
            "container_resized": int(resized),
            "container_moved": moved,
            "top_left_preserved": True,
            "container_geometry": dict(frame_after.get("geometry") or {}),
            "container_position": dict(frame_after.get("position") or {}),
        }
    )
    return result


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
