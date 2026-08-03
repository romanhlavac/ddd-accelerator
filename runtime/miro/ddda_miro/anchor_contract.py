from __future__ import annotations

import hashlib
import json
import urllib.parse
from copy import deepcopy
from pathlib import Path
from typing import Any

from .client import MiroClient
from .image_transport import canonical_miro_text
from .yamlio import load_yaml

ENDPOINT = {"frame": "frames", "shape": "shapes", "text": "texts", "sticky_note": "sticky_notes"}
VOLATILE = {"createdAt", "modifiedAt", "createdBy", "modifiedBy", "links"}


def load_manifest(path: Path) -> dict[str, Any]:
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError("anchor remediation manifest must be a mapping")
    required = {"schema_version", "remediation_id", "authorized_base_sha", "board_id", "frames", "protected_frames", "updates", "journey", "images"}
    missing = sorted(required - set(data))
    if missing or int(data["schema_version"]) != 1 or str(data["remediation_id"]) != "REM-PR8-HVA-CC-012.2":
        raise ValueError(f"invalid anchor remediation manifest; missing={missing}")
    if set(data["frames"]) != {"control", "journey", "align"} or len(data["protected_frames"]) != 15:
        raise ValueError("anchor/protected frame scope mismatch")
    assets = data["images"].get("assets") or []
    if len(assets) != 17:
        raise ValueError("REM-012.2 requires exactly 17 managed images")
    for asset in assets:
        digest = str(asset.get("expected_sha256") or "")
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError(f"asset {asset.get('id')} has no pinned SHA-256")
    return data


def _seg(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def _get_item(client: MiroClient, board: str, item: str) -> dict[str, Any]:
    return client._request("GET", f"boards/{_seg(board)}/items/{_seg(item)}")


def _get_frame(client: MiroClient, board: str, frame: str) -> dict[str, Any]:
    return client._request("GET", f"boards/{_seg(board)}/frames/{_seg(frame)}")


def _writable(remote: dict[str, Any], frame: bool = False) -> dict[str, Any]:
    result = {key: deepcopy(remote[key]) for key in ("data", "style", "geometry", "position") if remote.get(key) is not None}
    if not frame and remote.get("parent") is not None:
        result["parent"] = deepcopy(remote["parent"])
    return result


def _strip(value: Any) -> Any:
    if isinstance(value, list):
        return [_strip(item) for item in value]
    if isinstance(value, dict):
        return {key: _strip(item) for key, item in sorted(value.items()) if key not in VOLATILE}
    return value


def _digest(value: Any) -> str:
    raw = json.dumps(_strip(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _close(left: Any, right: Any, tolerance: float = 0.75) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return left == right


def _frame_matches(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    position, geometry = remote.get("position") or {}, remote.get("geometry") or {}
    return all((_close(position.get("x"), expected["x"]), _close(position.get("y"), expected["y"]), _close(geometry.get("width"), expected["width"]), _close(geometry.get("height"), expected["height"])))


def detect_board_state(client: MiroClient, manifest: dict[str, Any]):
    board, frames, before, target = str(manifest["board_id"]), {}, [], []
    for key, spec in manifest["frames"].items():
        remote = _get_frame(client, board, str(spec["id"]))
        frames[key] = remote
        before.append(_frame_matches(remote, spec["expected_current"]))
        target.append(_frame_matches(remote, spec["target"]))
    if all(before):
        return "before", frames
    if all(target):
        return "target", frames
    raise ValueError(f"anchor frames are in a mixed or unexpected state; current={before}, target={target}")


def _protected_snapshot(client: MiroClient, board: str, frame_ids: list[str]):
    items, connectors, result = client.list_items(board), client.list_connectors(board), {}
    for frame_id in frame_ids:
        children = [item for item in items if str((item.get("parent") or {}).get("id") or "") == frame_id]
        child_ids = {str(item.get("id") or "") for item in children}
        related = [connector for connector in connectors if str((connector.get("startItem") or {}).get("id") or "") in child_ids or str((connector.get("endItem") or {}).get("id") or "") in child_ids]
        result[frame_id] = {"frame": _get_frame(client, board, frame_id), "items": sorted(children, key=lambda item: str(item.get("id") or "")), "connectors": sorted(related, key=lambda item: str(item.get("id") or ""))}
    return {"digest": _digest(result), "frames": result}


def _patch(client: MiroClient, board: str, item_type: str, item_id: str, payload: dict[str, Any]):
    if item_type not in ENDPOINT:
        raise ValueError(f"unsupported managed item type: {item_type}")
    return client._request("PATCH", f"boards/{_seg(board)}/{ENDPOINT[item_type]}/{_seg(item_id)}", body=payload)


def _item_matches(remote: dict[str, Any], payload: dict[str, Any]) -> bool:
    if payload.get("parent") and str((remote.get("parent") or {}).get("id") or "") != str(payload["parent"].get("id") or ""):
        return False
    for key, value in (payload.get("data") or {}).items():
        actual = (remote.get("data") or {}).get(key)
        if (canonical_miro_text(actual) != canonical_miro_text(value)) if key in {"content", "title"} else (actual != value):
            return False
    for section in ("style", "geometry", "position"):
        actual = remote.get(section) or {}
        for key, value in (payload.get(section) or {}).items():
            if (not _close(actual.get(key), value)) if key in {"x", "y", "width", "height", "fontSize"} else (actual.get(key) != value):
                return False
    return True


def _target_payload(remote: dict[str, Any], update: dict[str, Any], frame_id: str):
    if str((remote.get("parent") or {}).get("id") or "") != frame_id:
        raise ValueError(f"item {remote.get('id')} is outside authorized frame {frame_id}")
    payload = _writable(remote)
    data, style, geometry = dict(payload.get("data") or {}), dict(payload.get("style") or {}), dict(payload.get("geometry") or {})
    if "content" in update:
        data["content"] = str(update["content"])
    if "font_size" in update:
        style["fontSize"] = int(update["font_size"])
    for key in ("width", "height"):
        if key in update:
            geometry[key] = float(update[key])
    payload.update({"data": data, "position": {"x": float(update["x"]), "y": float(update["y"]), "origin": "center", "relativeTo": "parent_top_left"}, "parent": {"id": frame_id}})
    if style:
        payload["style"] = style
    if geometry:
        payload["geometry"] = geometry
    return payload


