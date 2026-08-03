from __future__ import annotations

from .anchor_contract import _close, _get_frame, _get_item, _patch, _writable
from .client import MiroApiError
from .image_transport import canonical_miro_text


def _image_manifest(manifest):
    assets = []
    for asset in manifest["images"]["assets"]:
        key, target = str(asset["target_frame"]), manifest["frames"][str(asset["target_frame"])]["target"]
        assets.append({"id": str(asset["id"]), "usage": "REM-012.2 anchor-frame visual", "source": {"board_id": str(asset["source_board_id"]), "frame_id": str(asset["source_frame_id"]), "item_id": str(asset["source_item_id"]), "title": str(asset["id"]), "expected_sha256": str(asset["expected_sha256"])}, "target": {"frame_id": key, "position": {"x": float(asset["x"]) - float(target["width"]) / 2, "y": float(asset["y"]) - float(target["height"]) / 2}, "width": float(asset["width"])}})
    return {"manifest_id": str(manifest["images"]["manifest_id"]), "diagnostic_only": bool(manifest["images"].get("diagnostic_only", False)), "assets": assets}


def _verify_images(client, board, frame_ids, image_manifest, result):
    assets, verified = {str(item["id"]): item for item in image_manifest["assets"]}, []
    for evidence in result["assets"]:
        asset, remote = assets[str(evidence["asset_id"])], _get_item(client, board, str(evidence["target_item_id"]))
        parent = frame_ids[str(asset["target"]["frame_id"])]
        title = f"DDDA-IMAGE:{image_manifest['manifest_id']}:{evidence['asset_id']}:sha256={evidence['sha256']}"
        if remote.get("type") != "image" or str((remote.get("parent") or {}).get("id") or "") != parent or canonical_miro_text((remote.get("data") or {}).get("title")) != title:
            raise ValueError(f"managed asset {evidence['asset_id']} remote contract mismatch")
        verified.append({"asset_id": str(evidence["asset_id"]), "target_item_id": str(evidence["target_item_id"]), "remote_type": "image", "target_parent_id": parent, "sha256": str(evidence["sha256"]), "source_board_id": str(evidence["source_board_id"]), "source_frame_id": str(evidence["source_frame_id"]), "source_item_id": str(evidence["source_item_id"])})
    return {"status": "PASS", "items": verified}


def _bbox(frame):
    position, geometry = frame.get("position") or {}, frame.get("geometry") or {}
    x, y, width, height = float(position["x"]), float(position["y"]), float(geometry["width"]), float(geometry["height"])
    return x - width / 2, y - height / 2, x + width / 2, y + height / 2


def _overlaps(left, right):
    return not (left[2] <= right[0] or right[2] <= left[0] or left[3] <= right[1] or right[3] <= left[1])


def _verify_no_anchor_overlap(client, manifest):
    board = str(manifest["board_id"])
    anchors = {key: _get_frame(client, board, str(spec["id"])) for key, spec in manifest["frames"].items()}
    protected = {frame: _get_frame(client, board, str(frame)) for frame in manifest["protected_frames"]}
    collisions, entries = [], list(anchors.items())
    for index, (left_key, left) in enumerate(entries):
        for right_key, right in entries[index + 1:]:
            if _overlaps(_bbox(left), _bbox(right)):
                collisions.append({"left": left_key, "right": right_key})
        for right_key, right in protected.items():
            if _overlaps(_bbox(left), _bbox(right)):
                collisions.append({"left": left_key, "right": right_key})
    if collisions:
        raise ValueError(f"anchor-frame overlap detected: {collisions}")
    return {"status": "PASS", "collision_count": 0}


def _verify_table(client, manifest):
    item = _get_item(client, str(manifest["board_id"]), str(manifest["table_item_id"]))
    position, target = item.get("position") or {}, manifest["table_target"]
    if item.get("type") != "data_table_format" or str((item.get("parent") or {}).get("id") or "") != str(manifest["frames"]["control"]["id"]) or not _close(position.get("x"), target["x"]) or not _close(position.get("y"), target["y"]):
        raise ValueError(f"native artifact registry table contract mismatch: {item}")
    return {"status": "PASS", "item_id": str(item["id"]), "type": "data_table_format", "parent_id": str((item.get("parent") or {}).get("id") or ""), "position": {"x": float(position["x"]), "y": float(position["y"])}}


def _delete_if_present(client, board, item_id):
    try:
        _get_item(client, board, item_id)
    except MiroApiError as exc:
        if exc.status == 404:
            return "absent"
        raise
    client.delete_item(board, item_id)
    try:
        _get_item(client, board, item_id)
    except MiroApiError as exc:
        if exc.status == 404:
            return "deleted"
        raise
    raise ValueError(f"item {item_id} still exists after deletion")


def _rollback(client, board, frames, items, images_before, manifest_id):
    errors = []
    for item_id, snapshot in reversed(list(items.items())):
        try:
            _patch(client, board, str(snapshot["type"]), item_id, _writable(snapshot))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"item {item_id}: {exc}")
    for frame_id, snapshot in reversed(list(frames.items())):
        try:
            _patch(client, board, "frame", frame_id, _writable(snapshot, True))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"frame {frame_id}: {exc}")
    try:
        for image in client.list_items(board, "image"):
            image_id, title = str(image.get("id") or ""), canonical_miro_text((image.get("data") or {}).get("title"))
            if image_id not in images_before and title.startswith(f"DDDA-IMAGE:{manifest_id}:"):
                client.delete_item(board, image_id)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"managed images: {exc}")
    return {"status": "PASS" if not errors else "PARTIAL", "errors": errors}


