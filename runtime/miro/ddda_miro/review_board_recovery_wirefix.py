from __future__ import annotations

import base64
import urllib.parse
import urllib.request
from copy import deepcopy
from typing import Any

from . import frame01_redline as redline
from . import review_board_recovery as base


_ORIGINAL_APPLY = base.apply
_ORIGINAL_FRAME00_PAYLOAD = base.frame00_payload
_ORIGINAL_FRAME00_STATE = base.frame00_state
_ORIGINAL_RESTORE_FRAME00 = base.restore_frame00
_ORIGINAL_ITEM_PAYLOAD = redline.item_payload
_ORIGINAL_CONNECTOR_PAYLOAD = redline.connector_payload

METHODOLOGY_MARKER = "METODIKA A ZDROJE"
DEFAULT_METHODOLOGY_MIN_FONT = 80
DEFAULT_CONNECTOR_CAPTION_MIN_FONT = 48
NATIVE_TYPES = {"shape", "text", "sticky_note"}


def frame00_payload(update: dict[str, Any], frame_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a writable Frame-00 payload without Miro read-only relativeTo metadata."""
    payload = _ORIGINAL_FRAME00_PAYLOAD(update, frame_id, manifest)
    position = dict(payload.get("position") or {})
    position.pop("relativeTo", None)
    payload["position"] = position
    return payload


def _frame00_items_state(
    client: Any, manifest: dict[str, Any], contract: dict[str, Any]
) -> tuple[bool, dict[str, str]]:
    board, frame_id = str(manifest["board_id"]), str(manifest["frame00_id"])
    items = base._children(client, board, frame_id)
    if len(items) != 8:
        return False, {}
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for update in contract["managed_updates"]:
        expected = frame00_payload(update, frame_id, manifest)
        hits = [
            item
            for item in items
            if str(item.get("id") or "") not in used
            and base._role_match(item, update, expected)
        ]
        if len(hits) != 1 or not redline.same_item(hits[0], expected):
            return False, {}
        item_id = str(hits[0]["id"])
        mapping[str(update["role"])] = item_id
        used.add(item_id)
    if base._related_connectors(client, board, {str(item["id"]) for item in items}):
        return False, {}
    return True, mapping


def frame00_container_payload_preserve_top_left(
    frame: dict[str, Any], target_width: float, target_height: float
) -> dict[str, Any]:
    geometry = frame.get("geometry") or {}
    position = frame.get("position") or {}
    for key in ("width", "height"):
        if key not in geometry:
            raise ValueError(f"Frame 00 geometry is missing {key}")
    for key in ("x", "y"):
        if key not in position:
            raise ValueError(f"Frame 00 position is missing {key}")

    old_width, old_height = float(geometry["width"]), float(geometry["height"])
    top_left_x = float(position["x"]) - old_width / 2.0
    top_left_y = float(position["y"]) - old_height / 2.0
    return {
        "geometry": {"width": float(target_width), "height": float(target_height)},
        "position": {
            "x": top_left_x + float(target_width) / 2.0,
            "y": top_left_y + float(target_height) / 2.0,
            "origin": "center",
        },
    }


def _frame_top_left(frame: dict[str, Any]) -> tuple[float, float]:
    geometry = frame.get("geometry") or {}
    position = frame.get("position") or {}
    return (
        float(position["x"]) - float(geometry["width"]) / 2.0,
        float(position["y"]) - float(geometry["height"]) / 2.0,
    )


def frame00_state_accepted_container(
    client: Any, manifest: dict[str, Any], contract: dict[str, Any]
) -> tuple[bool, dict[str, str]]:
    frame = base._get_frame(client, str(manifest["board_id"]), str(manifest["frame00_id"]))
    geometry = frame.get("geometry") or {}
    if not (
        base._close(geometry.get("width"), contract["frame"]["width"])
        and base._close(geometry.get("height"), contract["frame"]["height"])
    ):
        return False, {}
    return _frame00_items_state(client, manifest, contract)


def restore_frame00_accepted_geometry_preserve_top_left(
    client: Any, manifest: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    board, frame_id = str(manifest["board_id"]), str(manifest["frame00_id"])
    items = base._children(client, board, frame_id)
    if len(items) != 8:
        raise ValueError("Frame 00 must contain exactly the eight accepted managed items")

    mapping: dict[str, str] = {}
    used: set[str] = set()
    updated = 0
    for update in contract["managed_updates"]:
        expected = frame00_payload(update, frame_id, manifest)
        hits = [
            item
            for item in items
            if str(item.get("id") or "") not in used
            and base._role_match(item, update, expected)
        ]
        if len(hits) != 1:
            raise ValueError(f"Frame 00 role {update['role']} could not be matched uniquely")
        item = hits[0]
        item_id = str(item["id"])
        if not redline.same_item(item, expected):
            endpoint = base.EP[str(update["type"])]
            client._request("PATCH", f"boards/{base._seg(board)}/{endpoint}/{base._seg(item_id)}", body=expected)
            fresh = client._request("GET", f"boards/{base._seg(board)}/items/{base._seg(item_id)}")
            if not redline.same_item(fresh, expected):
                raise ValueError(f"Frame 00 role {update['role']} did not converge to accepted contract")
            updated += 1
        mapping[str(update["role"])] = item_id
        used.add(item_id)

    if base._related_connectors(client, board, {str(item["id"]) for item in items}):
        raise ValueError("Frame 00 accepted contract must not contain connectors")

    frame_before = base._get_frame(client, board, frame_id)
    old_top_left = _frame_top_left(frame_before)
    target_width = float(contract["frame"]["width"])
    target_height = float(contract["frame"]["height"])
    resized = not (
        base._close((frame_before.get("geometry") or {}).get("width"), target_width)
        and base._close((frame_before.get("geometry") or {}).get("height"), target_height)
    )
    if resized:
        payload = frame00_container_payload_preserve_top_left(frame_before, target_width, target_height)
        client.update_item(board, "frame", frame_id, payload)

    frame_after = base._get_frame(client, board, frame_id)
    new_top_left = _frame_top_left(frame_after)
    if not (
        base._close((frame_after.get("geometry") or {}).get("width"), target_width)
        and base._close((frame_after.get("geometry") or {}).get("height"), target_height)
    ):
        raise ValueError("Frame 00 container did not converge to accepted geometry")
    if not (base._close(old_top_left[0], new_top_left[0]) and base._close(old_top_left[1], new_top_left[1])):
        raise ValueError("Frame 00 top-left moved while restoring accepted geometry")

    # Miro can normalize child coordinates when a parent frame is resized. Re-apply the
    # accepted parent-relative contract after the resize so the visual layout is exact.
    refreshed_items = base._children(client, board, frame_id)
    for update in contract["managed_updates"]:
        expected = frame00_payload(update, frame_id, manifest)
        hits = [
            item
            for item in refreshed_items
            if base._role_match(item, update, expected)
        ]
        if len(hits) != 1:
            raise ValueError(f"Frame 00 role {update['role']} was lost during container resize")
        if not redline.same_item(hits[0], expected):
            endpoint = base.EP[str(update["type"])]
            client._request(
                "PATCH",
                f"boards/{base._seg(board)}/{endpoint}/{base._seg(str(hits[0]['id']))}",
                body=expected,
            )
            updated += 1

    ok, verified = frame00_state_accepted_container(client, manifest, contract)
    if not ok:
        raise ValueError("Frame 00 did not reach the accepted visual contract")
    return {
        "created": 0,
        "deleted": 0,
        "connectors_deleted": 0,
        "updated": updated,
        "unchanged": 8 - updated,
        "role_ids": verified,
        "container_resized": int(resized),
        "top_left_preserved": True,
        "container_geometry": dict(frame_after.get("geometry") or {}),
        "container_position": dict(frame_after.get("position") or {}),
    }


def readable_frame01_item_payload(src: dict[str, Any], frame: str, manifest: dict[str, Any]) -> dict[str, Any]:
    payload = _ORIGINAL_ITEM_PAYLOAD(src, frame)
    if METHODOLOGY_MARKER not in redline.visible(src):
        return payload

    readability = manifest.get("readability") or {}
    min_font = int(readability.get("methodology_min_font_size") or DEFAULT_METHODOLOGY_MIN_FONT)
    style = dict(payload.get("style") or {})
    style["fontSize"] = max(int(style.get("fontSize") or 0), min_font)
    payload["style"] = style
    payload["geometry"] = {"width": float(readability.get("methodology_width") or 4800)}
    payload["position"] = {
        "x": float(readability.get("methodology_x") or 2600),
        "y": float(readability.get("methodology_y") or 850),
        "origin": "center",
    }
    return payload


def readable_connector_payload(
    src: dict[str, Any], start: str, end: str, manifest: dict[str, Any]
) -> dict[str, Any]:
    payload = _ORIGINAL_CONNECTOR_PAYLOAD(src, start, end)

    for name in ("startItem", "endItem"):
        source_endpoint = src.get(name) or {}
        if source_endpoint.get("position") is not None:
            payload.setdefault(name, {})["position"] = deepcopy(source_endpoint["position"])
        if source_endpoint.get("snapTo") is not None:
            payload.setdefault(name, {})["snapTo"] = deepcopy(source_endpoint["snapTo"])

    if src.get("captions"):
        readability = manifest.get("readability") or {}
        min_font = int(readability.get("connector_caption_min_font_size") or DEFAULT_CONNECTOR_CAPTION_MIN_FONT)
        source_style = src.get("style") or {}
        style = dict(payload.get("style") or {})
        for key in ("fontSize", "color", "textOrientation"):
            if source_style.get(key) is not None:
                style[key] = deepcopy(source_style[key])
        style["fontSize"] = max(int(style.get("fontSize") or 0), min_font)
        style["textOrientation"] = "horizontal"
        payload["style"] = style
    return payload


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
        "data": {
            "title": str(
                (source_frame.get("data") or {}).get("title")
                or (old_frame.get("data") or {}).get("title")
                or "01 – DDD Starter journey, gates a iterace"
            )
        },
        "geometry": {"width": source_width, "height": source_height},
        "position": {
            "x": top_left_x + source_width / 2.0,
            "y": top_left_y + source_height / 2.0,
            "origin": "center",
        },
    }
    source_style = deepcopy(source_frame.get("style") or {})
    if source_style:
        payload["style"] = source_style
    return payload


def companion_frame_payload(
    source_frame: dict[str, Any], source_main: dict[str, Any], target_main: dict[str, Any]
) -> dict[str, Any]:
    source_position = source_frame.get("position") or {}
    source_main_position = source_main.get("position") or {}
    target_main_position = target_main.get("position") or {}
    source_geometry = source_frame.get("geometry") or {}
    dx = float(target_main_position["x"]) - float(source_main_position["x"])
    dy = float(target_main_position["y"]) - float(source_main_position["y"])
    payload: dict[str, Any] = {
        "data": {"title": str((source_frame.get("data") or {}).get("title") or "")},
        "geometry": {
            "width": float(source_geometry["width"]),
            "height": float(source_geometry["height"]),
        },
        "position": {
            "x": float(source_position["x"]) + dx,
            "y": float(source_position["y"]) + dy,
            "origin": "center",
        },
    }
    style = deepcopy(source_frame.get("style") or {})
    if style:
        payload["style"] = style
    return payload


def _same_frame(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    if str((remote.get("data") or {}).get("title") or "") != str((expected.get("data") or {}).get("title") or ""):
        return False
    for section in ("position", "geometry"):
        for key, value in (expected.get(section) or {}).items():
            if key != "origin" and not base._close((remote.get(section) or {}).get(key), value):
                return False
    return True


def _frame_children_text(client: Any, board: str, frame_id: str) -> str:
    return " ".join(
        base._visible((item.get("data") or {}).get("content"))
        for item in base._children(client, board, frame_id)
    )


def _find_recovered_frame01(
    client: Any, manifest: dict[str, Any], source_frame: dict[str, Any]
) -> dict[str, Any] | None:
    board = str(manifest["board_id"])
    source_geometry = source_frame.get("geometry") or {}
    title = str(manifest["source_frame_title"])
    candidates: list[dict[str, Any]] = []
    for frame in client.list_items(board, "frame"):
        if str((frame.get("data") or {}).get("title") or "") != title:
            continue
        geometry = frame.get("geometry") or {}
        if not (
            base._close(geometry.get("width"), source_geometry.get("width"))
            and base._close(geometry.get("height"), source_geometry.get("height"))
        ):
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
    source_frame = base._get_frame(
        client, str(manifest["source_board_id"]), str(manifest["source_frame_id"])
    )
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


def _source_image_download_url(client: Any, image: dict[str, Any]) -> str:
    image_url = str((image.get("data") or {}).get("imageUrl") or "")
    if not image_url:
        raise ValueError(f"source image {image.get('id')} has no imageUrl")
    parsed = urllib.parse.urlparse(image_url)
    marker = "/v2/"
    if marker not in parsed.path:
        raise ValueError(f"source image URL is not a Miro v2 resource URL: {image_url}")
    path = parsed.path.split(marker, 1)[1]
    resource = client._request("GET", path, query={"format": "original", "redirect": "false"})
    if isinstance(resource, dict):
        for key in ("url", "resourceUrl", "downloadUrl"):
            if resource.get(key):
                return str(resource[key])
        data = resource.get("data") or {}
        if isinstance(data, dict) and data.get("url"):
            return str(data["url"])
    raise ValueError(f"source image {image.get('id')} resource response has no download URL")


def _image_data_url(client: Any, image: dict[str, Any]) -> str:
    download_url = _source_image_download_url(client, image)
    with urllib.request.urlopen(download_url, timeout=45) as response:
        raw = response.read()
        content_type = str(response.headers.get_content_type() or "image/png")
    if not raw:
        raise ValueError(f"source image {image.get('id')} downloaded empty")
    if len(raw) > 4_000_000:
        raise ValueError(f"source image {image.get('id')} is too large for bounded data-URL copy")
    return f"data:{content_type};base64,{base64.b64encode(raw).decode('ascii')}"


def _image_expected_geometry(source: dict[str, Any]) -> tuple[float, float, float]:
    position = source.get("position") or {}
    geometry = source.get("geometry") or {}
    return float(position["x"]), float(position["y"]), float(geometry["width"])


def _same_image(remote: dict[str, Any], source: dict[str, Any], target_frame_id: str) -> bool:
    if str(remote.get("type") or "") != "image":
        return False
    if str((remote.get("parent") or {}).get("id") or "") != target_frame_id:
        return False
    sx, sy, sw = _image_expected_geometry(source)
    remote_position = remote.get("position") or {}
    remote_geometry = remote.get("geometry") or {}
    return (
        base._close(remote_position.get("x"), sx)
        and base._close(remote_position.get("y"), sy)
        and base._close(remote_geometry.get("width"), sw)
    )


def _create_image(client: Any, board: str, target_frame_id: str, source: dict[str, Any]) -> dict[str, Any]:
    position = source.get("position") or {}
    geometry = source.get("geometry") or {}
    data: dict[str, Any] = {"url": _image_data_url(client, source)}
    title = (source.get("data") or {}).get("title")
    if title:
        data["title"] = str(title)
    payload = {
        "data": data,
        "position": {
            "x": float(position["x"]),
            "y": float(position["y"]),
            "origin": "center",
        },
        "geometry": {"width": float(geometry["width"])},
        "parent": {"id": target_frame_id},
    }
    created = client._request("POST", f"boards/{base._seg(board)}/images", body=payload)
    if not _same_image(created, source, target_frame_id):
        raise ValueError(f"created image {created.get('id')} did not preserve reference geometry")
    return created


def _companion_source_connectors(client: Any, board: str, item_ids: set[str]) -> list[dict[str, Any]]:
    return [
        connector
        for connector in client.list_connectors(board)
        if str((connector.get("startItem") or {}).get("id") or "") in item_ids
        and str((connector.get("endItem") or {}).get("id") or "") in item_ids
    ]


def _find_target_companion(client: Any, board: str, title: str) -> dict[str, Any] | None:
    candidates = [
        frame
        for frame in client.list_items(board, "frame")
        if str((frame.get("data") or {}).get("title") or "") == title
    ]
    if len(candidates) > 1:
        raise ValueError(f"multiple target companion frames named {title!r}")
    return candidates[0] if candidates else None


def _reconcile_companion_children(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    min_images: int,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    source_items = base._children(client, source_board, source_frame_id)
    source_types = {str(item.get("type") or "") for item in source_items}
    unsupported = sorted(source_types - (NATIVE_TYPES | {"image"}))
    if unsupported:
        raise ValueError(f"source companion contains unsupported items: {unsupported}")
    source_images = [item for item in source_items if str(item.get("type") or "") == "image"]
    if len(source_images) < min_images:
        raise ValueError(
            f"source companion {source_frame_id} has {len(source_images)} images, expected at least {min_images}"
        )

    target_items = base._children(client, target_board, target_frame_id)
    used: set[str] = set()
    mapping: dict[str, str] = {}
    counts = {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0}

    for source in sorted(
        [item for item in source_items if str(item.get("type") or "") in NATIVE_TYPES],
        key=lambda item: (redline.identity(item), str(item.get("id") or "")),
    ):
        payload = _ORIGINAL_ITEM_PAYLOAD(source, target_frame_id)
        target = redline.match(source, target_items, used)
        if target is None:
            endpoint = redline.EP[str(source["type"])]
            target = client._request("POST", f"boards/{base._seg(target_board)}/{endpoint}", body=payload)
            target_items.append(target)
            counts["created"] += 1
        elif redline.same_item(target, payload):
            counts["unchanged"] += 1
        else:
            endpoint = redline.EP[str(source["type"])]
            target = client._request(
                "PATCH",
                f"boards/{base._seg(target_board)}/{endpoint}/{base._seg(str(target['id']))}",
                body=payload,
            )
            counts["updated"] += 1
            if not redline.same_item(target, payload):
                raise ValueError(f"companion item {target['id']} read-back mismatch")
        target_id = str(target["id"])
        mapping[str(source["id"])] = target_id
        used.add(target_id)

    for source in source_images:
        hits = [
            item
            for item in target_items
            if str(item.get("id") or "") not in used
            and _same_image(item, source, target_frame_id)
        ]
        if len(hits) > 1:
            raise ValueError(f"multiple matching target images for source {source['id']}")
        if hits:
            target = hits[0]
            counts["unchanged"] += 1
        else:
            target = _create_image(client, target_board, target_frame_id, source)
            target_items.append(target)
            counts["created"] += 1
        target_id = str(target["id"])
        mapping[str(source["id"])] = target_id
        used.add(target_id)

    source_ids = {str(item["id"]) for item in source_items}
    source_connectors = _companion_source_connectors(client, source_board, source_ids)
    target_connectors = _companion_source_connectors(
        client, target_board, {str(item["id"]) for item in target_items}
    )
    used_connectors: set[str] = set()
    connector_counts = {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0}
    for source in source_connectors:
        start = mapping[str((source.get("startItem") or {})["id"])]
        end = mapping[str((source.get("endItem") or {})["id"])]
        payload = readable_connector_payload(source, start, end, manifest)
        hits = [
            connector
            for connector in target_connectors
            if str(connector.get("id") or "") not in used_connectors
            and str((connector.get("startItem") or {}).get("id") or "") == start
            and str((connector.get("endItem") or {}).get("id") or "") == end
        ]
        target = hits[0] if hits else None
        if target is None:
            target = client.create_connector(target_board, payload)
            target_connectors.append(target)
            connector_counts["created"] += 1
        elif redline.same_connector(target, payload):
            connector_counts["unchanged"] += 1
        else:
            target = client.update_connector(target_board, str(target["id"]), payload)
            connector_counts["updated"] += 1
            if not redline.same_connector(target, payload):
                from .connector_readback_wirefix import connector_contract_error

                raise ValueError(connector_contract_error(str(target["id"]), target, payload))
        used_connectors.add(str(target["id"]))

    extras_connectors = [
        connector
        for connector in target_connectors
        if str(connector.get("id") or "") not in used_connectors
    ]
    extras_items = [
        item for item in target_items if str(item.get("id") or "") not in used
    ]
    for connector in extras_connectors:
        client.delete_connector(target_board, str(connector["id"]))
        connector_counts["deleted"] += 1
    for item in extras_items:
        client.delete_item(target_board, str(item["id"]))
        counts["deleted"] += 1

    return {
        "source_item_count": len(source_items),
        "source_image_count": len(source_images),
        "source_connector_count": len(source_connectors),
        "items": counts,
        "connectors": connector_counts,
    }


def reconcile_companion_frames(client: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    specs = list(manifest.get("source_companion_frames") or [])
    if len(specs) != 9:
        raise ValueError(f"REM-012.5 must declare exactly nine companion frames, got {len(specs)}")

    source_board = str(manifest["source_board_id"])
    target_board = str(manifest["board_id"])
    source_main = base._get_frame(client, source_board, str(manifest["source_frame_id"]))
    target_main = base._get_frame(client, target_board, str(manifest["frame_id"]))
    protected = [str(value) for value in manifest["protected_frames"]]
    before = base._protected_snapshot(client, target_board, protected)

    created_frames: list[str] = []
    frame_counts = {"created": 0, "updated": 0, "unchanged": 0}
    per_frame: list[dict[str, Any]] = []
    try:
        for spec in specs:
            companion_source_board = str(spec.get("source_board_id") or source_board)
            source_frame = base._get_frame(client, companion_source_board, str(spec["id"]))
            title = str(spec["title"])
            if str((source_frame.get("data") or {}).get("title") or "") != title:
                raise ValueError(f"source companion title mismatch for {spec['id']}: {title!r}")
            expected = companion_frame_payload(source_frame, source_main, target_main)
            target = _find_target_companion(client, target_board, title)
            if target is None:
                target = client.create_item(target_board, "frame", expected)
                created_frames.append(str(target["id"]))
                frame_counts["created"] += 1
            elif _same_frame(target, expected):
                frame_counts["unchanged"] += 1
            else:
                target = client.update_item(target_board, "frame", str(target["id"]), expected)
                frame_counts["updated"] += 1
                if not _same_frame(target, expected):
                    raise ValueError(f"target companion {title!r} did not converge to reference geometry")

            child_result = _reconcile_companion_children(
                client,
                companion_source_board,
                str(source_frame["id"]),
                target_board,
                str(target["id"]),
                int(spec.get("min_images") or 0),
                manifest,
            )
            per_frame.append(
                {
                    "title": title,
                    "source_frame_id": str(source_frame["id"]),
                    "target_frame_id": str(target["id"]),
                    **child_result,
                }
            )

        after = base._protected_snapshot(client, target_board, protected)
        if after["digest"] != before["digest"]:
            raise ValueError("protected frames changed while restoring Frame 01 visual companions")
        return {
            "expected_frame_count": 9,
            "frames": frame_counts,
            "details": per_frame,
            "protected_frames_unchanged": True,
        }
    except Exception:
        for frame_id in reversed(created_frames):
            _cleanup_frame(client, target_board, frame_id)
        raise


def _companion_zero_mutation(result: dict[str, Any]) -> bool:
    if result["frames"]["created"] or result["frames"]["updated"]:
        return False
    for frame in result["details"]:
        if any(frame["items"][key] for key in ("created", "updated", "deleted")):
            return False
        if any(frame["connectors"][key] for key in ("created", "updated", "deleted")):
            return False
    return True


def apply_with_visual_companions(client: Any, manifest: dict[str, Any], source_sha: str) -> dict[str, Any]:
    board = str(manifest["board_id"])
    original_static_frame01 = str(manifest["frame_id"])
    old_frame_id: str | None = None
    new_frame_id: str | None = None
    created = False
    try:
        old_frame_id, new_frame_id, created = _prepare_frame01_target(client, manifest)
        result = _ORIGINAL_APPLY(client, manifest, source_sha)

        companion_first = reconcile_companion_frames(client, manifest)
        companion_second = reconcile_companion_frames(client, manifest)
        if not _companion_zero_mutation(companion_second):
            raise ValueError("second companion-frame reconcile is not zero mutation")

        if created and old_frame_id and old_frame_id != new_frame_id:
            _delete_old_frame01(client, board, old_frame_id)

        frame00 = base._get_frame(client, board, str(manifest["frame00_id"]))
        accepted = base._frame00_contract(manifest)
        geometry = frame00.get("geometry") or {}
        if not (
            base._close(geometry.get("width"), accepted["frame"]["width"])
            and base._close(geometry.get("height"), accepted["frame"]["height"])
        ):
            raise ValueError("Frame 00 final geometry does not match accepted HVR contract")

        readability = manifest.get("readability") or {}
        result["frame00_container"] = {
            "frame_id": str(manifest["frame00_id"]),
            "geometry": dict(geometry),
            "position": dict(frame00.get("position") or {}),
            "geometry_status": "ACCEPTED_GEOMETRY_TOP_LEFT_PRESERVED_PENDING_HUMAN_EQUIVALENCE_CHECK",
        }
        result["frame01_container"] = {
            "old_frame_id": old_frame_id or original_static_frame01,
            "new_frame_id": str(manifest["frame_id"]),
            "replaced": bool(created),
        }
        result["frame_id"] = str(manifest["frame_id"])
        result["companion_frames"] = {
            "first_run": companion_first,
            "second_run": companion_second,
        }
        result["readability_contract"] = {
            "methodology_min_font_size": int(
                readability.get("methodology_min_font_size") or DEFAULT_METHODOLOGY_MIN_FONT
            ),
            "connector_caption_min_font_size": int(
                readability.get("connector_caption_min_font_size")
                or DEFAULT_CONNECTOR_CAPTION_MIN_FONT
            ),
        }
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
    original_item_payload = redline.item_payload
    original_connector_payload = redline.connector_payload

    base.frame00_payload = frame00_payload
    base.frame00_state = frame00_state_accepted_container
    base.restore_frame00 = restore_frame00_accepted_geometry_preserve_top_left
    redline.item_payload = lambda src, frame: readable_frame01_item_payload(src, frame, _ACTIVE_MANIFEST)
    redline.connector_payload = (
        lambda src, start, end: readable_connector_payload(src, start, end, _ACTIVE_MANIFEST)
    )
    base.apply = apply_with_visual_companions

    _ACTIVE_MANIFEST.clear()
    original_load_manifest = base.load_manifest

    def load_manifest_with_active(path: Any) -> dict[str, Any]:
        manifest = original_load_manifest(path)
        _ACTIVE_MANIFEST.clear()
        _ACTIVE_MANIFEST.update(manifest)
        return manifest

    base.load_manifest = load_manifest_with_active
    try:
        return base.main(argv)
    finally:
        base.load_manifest = original_load_manifest
        base.frame00_payload = original_payload
        base.frame00_state = original_state
        base.restore_frame00 = original_restore
        redline.item_payload = original_item_payload
        redline.connector_payload = original_connector_payload
        base.apply = original_apply
        _ACTIVE_MANIFEST.clear()


_ACTIVE_MANIFEST: dict[str, Any] = {}


if __name__ == "__main__":
    raise SystemExit(main())
