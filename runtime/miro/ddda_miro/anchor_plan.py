from __future__ import annotations

from .anchor_contract import (
    _frame_matches, _get_frame, _get_item, _item_matches, _patch, _target_payload, _writable,
)
from .image_transport import canonical_miro_text


def _apply_update(client, board, update, frame_ids, snapshots):
    item_id, item_type = str(update["id"]), str(update["type"])
    remote = _get_item(client, board, item_id)
    if str(remote.get("type") or "") != item_type:
        raise ValueError(f"item {item_id} type mismatch")
    snapshots.setdefault(item_id, remote)
    payload = _target_payload(remote, update, frame_ids[str(update["frame"])])
    if _item_matches(remote, payload):
        return "unchanged"
    updated = _patch(client, board, item_type, item_id, payload)
    if not _item_matches(updated, payload):
        raise ValueError(f"item {item_id} did not reach target")
    return "updated"


def _apply_frame(client, board, key, spec, snapshots):
    frame_id, target = str(spec["id"]), spec["target"]
    remote = _get_frame(client, board, frame_id)
    snapshots.setdefault(frame_id, remote)
    payload = _writable(remote, True)
    payload["position"] = {"x": float(target["x"]), "y": float(target["y"]), "origin": "center"}
    payload["geometry"] = {"width": float(target["width"]), "height": float(target["height"])}
    if _frame_matches(remote, target):
        client._frame_geometry_cache[(board, frame_id)] = dict(payload["geometry"])
        return "unchanged"
    updated = _patch(client, board, "frame", frame_id, payload)
    if not _frame_matches(updated, target):
        raise ValueError(f"frame {key}/{frame_id} did not reach target")
    client._frame_geometry_cache[(board, frame_id)] = dict(payload["geometry"])
    return "updated"


def _journey_updates(client, manifest, state):
    board, journey, result = str(manifest["board_id"]), manifest["journey"], []
    for item, x in zip(journey["stage_ids"], journey["stage_x"], strict=True):
        result.append({"id": str(item), "type": "shape", "frame": "journey", "x": x, "y": journey["stage_y"], "font_size": journey["stage_font"]})
    for item, x in zip(journey["gate_ids"], journey["stage_x"], strict=True):
        result.append({"id": str(item), "type": "shape", "frame": "journey", "x": x, "y": journey["gate_y"], "font_size": journey["gate_font"]})
    for ids, item_type, y, font, shift in ((journey["semantic_shape_ids"], "shape", journey["lower_y"], journey["lower_font"], journey["lower_x_shift"]), (journey["semantic_sticky_ids"], "sticky_note", journey["lower_y"], None, journey["lower_x_shift"]), (journey["zone_ids"], "shape", journey["zone_y"], journey["zone_font"], journey["zone_x_shift"])):
        for item in ids:
            remote = _get_item(client, board, str(item))
            update = {"id": str(item), "type": item_type, "frame": "journey", "x": float((remote.get("position") or {})["x"]) + (float(shift) if state == "before" else 0), "y": y}
            if font is not None:
                update["font_size"] = font
            result.append(update)
    return result


def _deletion_candidates(client, manifest, state):
    board, frames, dynamic = str(manifest["board_id"]), {key: str(spec["id"]) for key, spec in manifest["frames"].items()}, manifest["delete_dynamic"]
    items = client.list_items(board)
    control = [str(item["id"]) for item in items if item.get("type") == "shape" and str((item.get("parent") or {}).get("id") or "") == frames["control"] and float((item.get("position") or {}).get("y") or 0) >= float(dynamic["control_shape_y_at_least"])]
    journey = [str(item["id"]) for item in items if item.get("type") == "shape" and str((item.get("parent") or {}).get("id") or "") == frames["journey"] and str(dynamic["journey_content_contains"]) in canonical_miro_text((item.get("data") or {}).get("content"))]
    if state == "before" and (len(control) != int(dynamic["expected_control_shape_count"]) or len(journey) != int(dynamic["expected_journey_shape_count"])):
        label = "control obsolete grid count mismatch" if len(control) != int(dynamic["expected_control_shape_count"]) else "journey obsolete inspiration count mismatch"
        raise ValueError(f"{label}: control={len(control)}, journey={len(journey)}")
    if state == "target" and (control or journey):
        raise ValueError("target-state board still contains obsolete dynamic items")
    return list(dict.fromkeys(control + journey + [str(item) for item in manifest["delete_exact_ids"]] + [str(manifest["obsolete_table_item_id"])]))


def _assert_no_connected_deletions(client, board, ids):
    candidates, connected = set(ids), []
    for connector in client.list_connectors(board):
        if str((connector.get("startItem") or {}).get("id") or "") in candidates or str((connector.get("endItem") or {}).get("id") or "") in candidates:
            connected.append(str(connector.get("id") or ""))
    if connected:
        raise ValueError(f"obsolete items are connected: {connected}")


def _park_dynamic_obsolete_items(client, manifest, state, snapshots):
    if state != "before":
        return {"updated": 0, "unchanged": 0}
    board, frames, dynamic, result = str(manifest["board_id"]), {key: str(spec["id"]) for key, spec in manifest["frames"].items()}, manifest["delete_dynamic"], {"updated": 0, "unchanged": 0}
    for item in client.list_items(board, "shape"):
        parent, position, content = str((item.get("parent") or {}).get("id") or ""), item.get("position") or {}, canonical_miro_text((item.get("data") or {}).get("content"))
        target = None
        if parent == frames["control"] and float(position.get("y") or 0) >= float(dynamic["control_shape_y_at_least"]):
            target = {"x": 3500.0, "y": 4400.0, "origin": "center", "relativeTo": "parent_top_left"}
        elif parent == frames["journey"] and str(dynamic["journey_content_contains"]) in content:
            target = {"x": float(position.get("x") or 0), "y": 9500.0, "origin": "center", "relativeTo": "parent_top_left"}
        if target is None:
            continue
        item_id, payload = str(item["id"]), _writable(item)
        snapshots.setdefault(item_id, item)
        payload["position"] = target
        if _item_matches(item, payload):
            result["unchanged"] += 1
        else:
            if not _item_matches(_patch(client, board, "shape", item_id, payload), payload):
                raise ValueError(f"obsolete item {item_id} could not be parked")
            result["updated"] += 1
    expected = int(dynamic["expected_control_shape_count"]) + int(dynamic["expected_journey_shape_count"])
    if result["updated"] + result["unchanged"] != expected:
        raise ValueError(f"obsolete parking count mismatch: {result}")
    return result


