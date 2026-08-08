from __future__ import annotations

from typing import Any

from . import review_board_recovery as base
from . import review_board_recovery_wirefix as wirefix


_ORIGINAL_RESTORE_FRAME00 = wirefix._ORIGINAL_RESTORE_FRAME00
frame00_state_accepted_container = wirefix.frame00_state_accepted_container


def _frame_top_left(frame: dict[str, Any]) -> tuple[float, float]:
    geometry = frame.get("geometry") or {}
    position = frame.get("position") or {}
    return (
        float(position["x"]) - float(geometry["width"]) / 2.0,
        float(position["y"]) - float(geometry["height"]) / 2.0,
    )


def restore_frame00_accepted_geometry_preserve_top_left(
    client: Any, manifest: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    """Use the proven safe child-recreate/shrink ordering, then restore canvas top-left."""
    board, frame_id = str(manifest["board_id"]), str(manifest["frame00_id"])
    frame_before = base._get_frame(client, board, frame_id)
    old_top_left = _frame_top_left(frame_before)
    target_width = float(contract["frame"]["width"])
    target_height = float(contract["frame"]["height"])
    resized = not (
        base._close((frame_before.get("geometry") or {}).get("width"), target_width)
        and base._close((frame_before.get("geometry") or {}).get("height"), target_height)
    )

    # Proven Miro-safe ordering from review_board_recovery.restore_frame00:
    # delete stale children -> recreate accepted children while the parent is still large
    # enough -> shrink the parent. Directly shrinking a populated frame triggers 3.0204.
    recovery = _ORIGINAL_RESTORE_FRAME00(client, manifest, contract)

    frame_after_restore = base._get_frame(client, board, frame_id)
    geometry = frame_after_restore.get("geometry") or {}
    if not (
        base._close(geometry.get("width"), target_width)
        and base._close(geometry.get("height"), target_height)
    ):
        raise ValueError("Frame 00 container did not converge to accepted geometry")

    desired_x = old_top_left[0] + target_width / 2.0
    desired_y = old_top_left[1] + target_height / 2.0
    position = frame_after_restore.get("position") or {}
    moved = not (
        base._close(position.get("x"), desired_x)
        and base._close(position.get("y"), desired_y)
    )
    if moved:
        # Position only: do not resend geometry after the safe shrink.
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

    frame_after = base._get_frame(client, board, frame_id)
    new_top_left = _frame_top_left(frame_after)
    if not (
        base._close((frame_after.get("geometry") or {}).get("width"), target_width)
        and base._close((frame_after.get("geometry") or {}).get("height"), target_height)
    ):
        raise ValueError("Frame 00 geometry changed while restoring top-left position")
    if not (
        base._close(old_top_left[0], new_top_left[0])
        and base._close(old_top_left[1], new_top_left[1])
    ):
        raise ValueError("Frame 00 top-left did not converge after safe resize ordering")

    ok, verified = frame00_state_accepted_container(client, manifest, contract)
    if not ok:
        raise ValueError("Frame 00 did not reach the accepted visual contract")

    result = dict(recovery)
    result.update(
        {
            "role_ids": verified,
            "container_resized": int(resized),
            "container_moved": int(moved),
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
