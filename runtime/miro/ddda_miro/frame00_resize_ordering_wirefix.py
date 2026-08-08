from __future__ import annotations

from copy import deepcopy
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


def _replacement_config(manifest: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    config = manifest.get("frame00_replacement") or {}
    if str(config.get("policy") or "") != "discover_verified_or_replace_legacy_container":
        raise ValueError("Frame 00 replacement policy is missing or invalid")
    legacy_frame_id = str(config.get("legacy_frame_id") or "")
    title = str(config.get("title") or "")
    top_left = config.get("target_top_left") or {}
    staging = config.get("staging_center") or {}
    if not legacy_frame_id or not title:
        raise ValueError("Frame 00 replacement contract is missing legacy id or title")
    for section_name, section in (("target_top_left", top_left), ("staging_center", staging)):
        for key in ("x", "y"):
            if section.get(key) is None:
                raise ValueError(f"Frame 00 replacement {section_name} is missing {key}")

    target_width = float(contract["frame"]["width"])
    target_height = float(contract["frame"]["height"])
    target_center = {
        "x": float(top_left["x"]) + target_width / 2.0,
        "y": float(top_left["y"]) + target_height / 2.0,
    }
    return {
        "legacy_frame_id": legacy_frame_id,
        "title": title,
        "target_top_left": {"x": float(top_left["x"]), "y": float(top_left["y"])},
        "target_center": target_center,
        "staging_center": {"x": float(staging["x"]), "y": float(staging["y"])},
        "fill_color": str(config.get("fill_color") or "#f8fafc"),
        "target_width": target_width,
        "target_height": target_height,
    }


def _manifest_for_frame(manifest: dict[str, Any], frame_id: str) -> dict[str, Any]:
    resolved = dict(manifest)
    resolved["frame00_id"] = str(frame_id)
    return resolved


def _list_frames(client: Any, board: str) -> list[dict[str, Any]]:
    return list(client.list_items(board, "frame"))


def _find_frame(client: Any, board: str, frame_id: str) -> dict[str, Any] | None:
    return next(
        (
            frame
            for frame in _list_frames(client, board)
            if str(frame.get("id") or "") == frame_id
        ),
        None,
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
            raise ValueError(
                f"Frame 00 role {role or '<missing>'} has invalid accepted visual bounds"
            )
        left, right = x - width / 2.0, x + width / 2.0
        top, bottom = y - visual_height / 2.0, y + visual_height / 2.0
        if left < 0 or top < 0 or right > target_width or bottom > target_height:
            raise ValueError(
                f"Frame 00 role {role} does not fit accepted {target_width}x{target_height} bounds"
            )


def _items_state_for_frame(
    client: Any, manifest: dict[str, Any], contract: dict[str, Any], frame_id: str
) -> tuple[bool, dict[str, str]]:
    return _frame00_items_state(
        client, _manifest_for_frame(manifest, frame_id), contract
    )


def _container_state_for_frame(
    client: Any, manifest: dict[str, Any], contract: dict[str, Any], frame_id: str
) -> tuple[bool, dict[str, str]]:
    return frame00_state_accepted_container(
        client, _manifest_for_frame(manifest, frame_id), contract
    )


def _close_position(frame: dict[str, Any], center: dict[str, float]) -> bool:
    position = frame.get("position") or {}
    return base._close(position.get("x"), center["x"]) and base._close(
        position.get("y"), center["y"]
    )


def _find_verified_replacements(
    client: Any,
    manifest: dict[str, Any],
    contract: dict[str, Any],
    config: dict[str, Any],
) -> tuple[
    tuple[dict[str, Any] | None, dict[str, str]],
    tuple[dict[str, Any] | None, dict[str, str]],
]:
    """Return (target, staging), accepting only verified candidates at deterministic positions."""
    board = str(manifest["board_id"])
    target_candidates: list[tuple[dict[str, Any], dict[str, str]]] = []
    staging_candidates: list[tuple[dict[str, Any], dict[str, str]]] = []

    for frame in _list_frames(client, board):
        frame_id = str(frame.get("id") or "")
        if not frame_id or frame_id == config["legacy_frame_id"]:
            continue
        if str((frame.get("data") or {}).get("title") or "") != config["title"]:
            continue
        geometry = frame.get("geometry") or {}
        if not (
            base._close(geometry.get("width"), config["target_width"])
            and base._close(geometry.get("height"), config["target_height"])
        ):
            continue
        if frame.get("parent"):
            continue

        items_ok, mapping = _items_state_for_frame(
            client, manifest, contract, frame_id
        )
        if not items_ok:
            continue

        if _close_position(frame, config["target_center"]):
            target_candidates.append((frame, mapping))
        elif _close_position(frame, config["staging_center"]):
            staging_candidates.append((frame, mapping))

    if len(target_candidates) > 1:
        raise ValueError(
            "multiple verified final Frame 00 replacement candidates found: "
            + ", ".join(str(frame["id"]) for frame, _ in target_candidates)
        )
    if len(staging_candidates) > 1:
        raise ValueError(
            "multiple verified staging Frame 00 replacement candidates found: "
            + ", ".join(str(frame["id"]) for frame, _ in staging_candidates)
        )
    return (
        target_candidates[0] if target_candidates else (None, {}),
        staging_candidates[0] if staging_candidates else (None, {}),
    )


def _create_accepted_children(
    client: Any,
    manifest: dict[str, Any],
    contract: dict[str, Any],
    frame_id: str,
) -> dict[str, str]:
    board = str(manifest["board_id"])
    target_manifest = _manifest_for_frame(manifest, frame_id)
    mapping: dict[str, str] = {}
    created_ids: list[str] = []
    try:
        for update in contract["managed_updates"]:
            item_type = str(update["type"])
            payload = frame00_payload(update, frame_id, target_manifest)
            created = client._request(
                "POST",
                f"boards/{base._seg(board)}/{base.EP[item_type]}",
                body=payload,
            )
            item_id = str(created["id"])
            created_ids.append(item_id)
            fresh = client._request(
                "GET", f"boards/{base._seg(board)}/items/{base._seg(item_id)}"
            )
            if not same_item(fresh, payload):
                raise ValueError(
                    f"replacement Frame 00 role {update['role']} read-back mismatch"
                )
            mapping[str(update["role"])] = item_id
    except Exception as exc:
        rollback_errors: list[str] = []
        for item_id in reversed(created_ids):
            try:
                client.delete_item(board, item_id)
            except Exception as rollback_exc:  # pragma: no cover - external rollback
                rollback_errors.append(f"{item_id}: {rollback_exc}")
        if rollback_errors:
            raise ValueError(
                "Frame 00 replacement child creation failed and rollback was incomplete: "
                + "; ".join(rollback_errors)
            ) from exc
        raise
    return mapping


def _cleanup_frame(client: Any, board: str, frame_id: str) -> tuple[int, int, int]:
    frame = _find_frame(client, board, frame_id)
    if frame is None:
        return 0, 0, 0
    children = base._children(client, board, frame_id)
    ids = {str(item["id"]) for item in children}
    related = base._related_connectors(client, board, ids)
    for connector in related:
        client.delete_connector(board, str(connector["id"]))
    for item in children:
        client.delete_item(board, str(item["id"]))
    client.delete_item(board, frame_id)
    if _find_frame(client, board, frame_id) is not None:
        raise ValueError(f"Frame 00 container {frame_id} remained after cleanup")
    return len(children), len(related), 1


def _create_verified_frame(
    client: Any,
    manifest: dict[str, Any],
    contract: dict[str, Any],
    config: dict[str, Any],
    center: dict[str, float],
    style_source: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, str]]:
    board = str(manifest["board_id"])
    style = deepcopy((style_source or {}).get("style") or {})
    if not style:
        style = {"fillColor": config["fill_color"]}
    payload: dict[str, Any] = {
        "data": {"title": config["title"]},
        "style": style,
        "geometry": {
            "width": config["target_width"],
            "height": config["target_height"],
        },
        "position": {
            "x": center["x"],
            "y": center["y"],
            "origin": "center",
        },
    }
    created = client.create_item(board, "frame", payload)
    frame_id = str(created["id"])
    try:
        fresh = base._get_frame(client, board, frame_id)
        geometry = fresh.get("geometry") or {}
        if not (
            base._close(geometry.get("width"), config["target_width"])
            and base._close(geometry.get("height"), config["target_height"])
        ):
            raise ValueError("replacement Frame 00 geometry mismatch")
        if not _close_position(fresh, center):
            raise ValueError("replacement Frame 00 position mismatch")
        if fresh.get("parent"):
            raise ValueError("replacement Frame 00 must be a top-level frame")

        _create_accepted_children(client, manifest, contract, frame_id)
        items_ok, mapping = _items_state_for_frame(
            client, manifest, contract, frame_id
        )
        if not items_ok:
            raise ValueError(
                "replacement Frame 00 children failed accepted contract verification"
            )
        return fresh, mapping
    except Exception:
        try:
            _cleanup_frame(client, board, frame_id)
        except Exception:
            pass
        raise


def _legacy_precondition(
    client: Any,
    manifest: dict[str, Any],
    contract: dict[str, Any],
    legacy_frame_id: str,
) -> tuple[int, int]:
    board = str(manifest["board_id"])
    children = base._children(client, board, legacy_frame_id)
    if children:
        if len(children) != 8:
            raise ValueError(
                "legacy Frame 00 is partially populated and no verified replacement exists"
            )
        items_ok, _ = _items_state_for_frame(
            client, manifest, contract, legacy_frame_id
        )
        if not items_ok:
            raise ValueError(
                "legacy Frame 00 populated state does not match the accepted eight-item contract"
            )
    related = base._related_connectors(
        client, board, {str(item["id"]) for item in children}
    )
    if related:
        raise ValueError(
            "legacy Frame 00 accepted contract must not contain connectors"
        )
    return len(children), len(related)


def _final_frame_state(
    client: Any,
    manifest: dict[str, Any],
    contract: dict[str, Any],
    config: dict[str, Any],
    frame_id: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    board = str(manifest["board_id"])
    frame = base._get_frame(client, board, frame_id)
    geometry = frame.get("geometry") or {}
    top_left = _frame_top_left(frame)
    if not (
        base._close(geometry.get("width"), config["target_width"])
        and base._close(geometry.get("height"), config["target_height"])
    ):
        raise ValueError("replacement Frame 00 final geometry mismatch")
    if not (
        base._close(top_left[0], config["target_top_left"]["x"])
        and base._close(top_left[1], config["target_top_left"]["y"])
    ):
        raise ValueError("replacement Frame 00 final top-left mismatch")
    if frame.get("parent"):
        raise ValueError("replacement Frame 00 final container is nested")
    ok, mapping = _container_state_for_frame(
        client, manifest, contract, frame_id
    )
    if not ok:
        raise ValueError("replacement Frame 00 did not reach accepted visual contract")
    return frame, mapping


def restore_frame00_accepted_geometry_preserve_top_left(
    client: Any, manifest: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    """Transactionally replace the irreducible legacy Frame 00 without frame PATCH."""
    board = str(manifest["board_id"])
    _validate_target_envelope(contract)
    config = _replacement_config(manifest, contract)

    current_id = str(manifest.get("frame00_id") or "")
    if current_id and current_id != config["legacy_frame_id"]:
        ok, mapping = _container_state_for_frame(
            client, manifest, contract, current_id
        )
        if ok:
            frame, mapping = _final_frame_state(
                client, manifest, contract, config, current_id
            )
            return {
                "created": 0, "deleted": 0, "connectors_deleted": 0, "updated": 0,
                "unchanged": 8, "role_ids": mapping, "container_replaced": 0,
                "replacement_reused": 1, "legacy_frame_id": config["legacy_frame_id"],
                "replacement_frame_id": current_id, "legacy_container_deleted": 0,
                "staging_container_deleted": 0, "container_resized": 0,
                "container_moved": 0, "top_left_preserved": True,
                "container_geometry": dict(frame.get("geometry") or {}),
                "container_position": dict(frame.get("position") or {}),
            }

    legacy_frame = _find_frame(client, board, config["legacy_frame_id"])
    (target, _), (staging, _) = _find_verified_replacements(
        client, manifest, contract, config
    )

    if target is not None:
        legacy_deleted = (
            _cleanup_frame(client, board, config["legacy_frame_id"])
            if legacy_frame is not None else (0, 0, 0)
        )
        staging_deleted = (
            _cleanup_frame(client, board, str(staging["id"]))
            if staging is not None else (0, 0, 0)
        )
        target_id = str(target["id"])
        manifest["frame00_id"] = target_id
        frame, verified = _final_frame_state(
            client, manifest, contract, config, target_id
        )
        return {
            "created": 0,
            "deleted": legacy_deleted[0] + staging_deleted[0],
            "connectors_deleted": legacy_deleted[1] + staging_deleted[1],
            "updated": 0, "unchanged": 8, "role_ids": verified,
            "container_replaced": int(bool(legacy_deleted[2] or staging_deleted[2])),
            "replacement_reused": 1, "legacy_frame_id": config["legacy_frame_id"],
            "replacement_frame_id": target_id,
            "legacy_container_deleted": legacy_deleted[2],
            "staging_container_deleted": staging_deleted[2],
            "container_resized": 0, "container_moved": 0,
            "top_left_preserved": True,
            "container_geometry": dict(frame.get("geometry") or {}),
            "container_position": dict(frame.get("position") or {}),
        }

    staging_created = 0
    if staging is None:
        if legacy_frame is None:
            raise ValueError(
                "legacy Frame 00 is missing and no verified staging/final replacement exists"
            )
        _legacy_precondition(client, manifest, contract, config["legacy_frame_id"])
        staging, _ = _create_verified_frame(
            client, manifest, contract, config, config["staging_center"], legacy_frame
        )
        staging_created = 1

    staging_id = str(staging["id"])
    if staging_id == config["legacy_frame_id"]:
        raise ValueError("Frame 00 staging replacement reused legacy id")

    legacy_deleted = (
        _cleanup_frame(client, board, config["legacy_frame_id"])
        if legacy_frame is not None else (0, 0, 0)
    )

    final, _ = _create_verified_frame(
        client, manifest, contract, config, config["target_center"], staging
    )
    final_id = str(final["id"])
    if final_id in {config["legacy_frame_id"], staging_id}:
        raise ValueError("Frame 00 final replacement id is not unique")

    staging_deleted = _cleanup_frame(client, board, staging_id)

    manifest["frame00_id"] = final_id
    frame, verified = _final_frame_state(
        client, manifest, contract, config, final_id
    )
    return {
        "created": 16 if staging_created else 8,
        "deleted": legacy_deleted[0] + staging_deleted[0],
        "connectors_deleted": legacy_deleted[1] + staging_deleted[1],
        "updated": 0, "unchanged": 0, "role_ids": verified,
        "container_replaced": 1, "replacement_reused": int(not staging_created),
        "legacy_frame_id": config["legacy_frame_id"],
        "replacement_frame_id": final_id,
        "legacy_container_deleted": legacy_deleted[2],
        "staging_container_deleted": staging_deleted[2],
        "container_resized": 0, "container_moved": 0,
        "top_left_preserved": True,
        "container_geometry": dict(frame.get("geometry") or {}),
        "container_position": dict(frame.get("position") or {}),
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
