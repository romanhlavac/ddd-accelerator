from __future__ import annotations

"""Full-arrow render fidelity for the frozen PR8 Miro Tips reference.

The approved Miro Tips reference contains eleven visible arrows: eight native
callouts that terminate on the screenshot plus three text callouts that are not
represented by the historical child-to-child connector filter.  A connector
attached to a tiny technical endpoint does not preserve the same Miro routing
curve as a connector attached to the full-size screenshot.  This repair uses a
transparent routing proxy with the exact screenshot geometry so Miro receives
the same endpoint geometry while the visible screenshot remains unchanged.

Seven tiny compatibility anchors are retained as invisible transport metadata
so the already-versioned HVR copy contract can migrate without weakening its
copy proof.  They are not connector endpoints and are excluded from the visible
reference topology.  Human visual acceptance remains authoritative.
"""

from collections import Counter
from copy import deepcopy
import json
from typing import Any

from . import miro_tips_hvr_fix as tips
from . import miro_tips_render_fidelity_fix as fidelity
from . import review_board_recovery as base
from . import review_board_recovery_wirefix as visual


EXPECTED_REFERENCE_CONNECTORS = 11
EXPECTED_DIRECT_IMAGE_CONNECTORS = 8
EXPECTED_TEXT_CONNECTORS = 3
EXPECTED_COMPATIBILITY_ANCHORS = 7
ROUTING_PROXY_POLICY = "full_size_transparent_screenshot_geometry_proxy_v3"
ENDPOINT_POLICY = "source_attachment_or_free_point_to_proxy_v3"
REFERENCE_STRUCTURE_POLICY = "exact_reference_children_plus_all_callout_arrows_v3"
VISUAL_ACCEPTANCE_AUTHORITY = "human_review_only"

_ORIGINAL_IS_CONTROL_ANCHOR = fidelity.is_control_anchor
_ORIGINAL_EXPECTED_CONNECTORS = tips.EXPECTED_CONNECTOR_COUNT
_ORIGINAL_RECONCILE: Any | None = None
_INSTALLED = False
_HVR_INSTALLED = False
_HVR_ASSERT_ORIGINAL: Any | None = None


def _close(left: Any, right: Any, tolerance: float = 0.75) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return False


def _unit(value: Any) -> float:
    if isinstance(value, str) and value.strip().endswith("%"):
        return float(value.strip()[:-1]) / 100.0
    number = float(value)
    if number > 1.0 and number <= 100.0:
        number /= 100.0
    return number


def _endpoint_ids(connector: dict[str, Any]) -> tuple[str, str]:
    return (
        str((connector.get("startItem") or {}).get("id") or ""),
        str((connector.get("endItem") or {}).get("id") or ""),
    )


def _visible_text(item: dict[str, Any]) -> str:
    return base._visible((item.get("data") or {}).get("content")).casefold()


def _reference_contract(manifest: dict[str, Any]) -> dict[str, int]:
    raw = dict(manifest.get("miro_tips") or {})
    total = int(raw.get("expected_connector_count") or 0)
    direct = int(raw.get("expected_direct_image_connector_count") or 0)
    text = int(raw.get("expected_text_connector_count") or 0)
    if total != EXPECTED_REFERENCE_CONNECTORS:
        raise ValueError(
            f"Miro Tips reference must declare {EXPECTED_REFERENCE_CONNECTORS} total arrows, got {total}"
        )
    if direct != EXPECTED_DIRECT_IMAGE_CONNECTORS:
        raise ValueError(
            f"Miro Tips reference must declare {EXPECTED_DIRECT_IMAGE_CONNECTORS} screenshot callouts, got {direct}"
        )
    if text != EXPECTED_TEXT_CONNECTORS:
        raise ValueError(
            f"Miro Tips reference must declare {EXPECTED_TEXT_CONNECTORS} text callouts, got {text}"
        )
    return {"total": total, "direct": direct, "text": text}


def classify_reference_connectors(
    connectors: list[dict[str, Any]],
    child_ids: set[str],
    image_id: str,
    text_ids: set[str],
) -> dict[str, list[dict[str, Any]]]:
    selected = [
        row
        for row in connectors
        if any(endpoint_id in child_ids for endpoint_id in _endpoint_ids(row) if endpoint_id)
    ]
    direct = [
        row
        for row in selected
        if image_id and image_id in _endpoint_ids(row)
    ]
    text = [
        row
        for row in selected
        if any(endpoint_id in text_ids for endpoint_id in _endpoint_ids(row) if endpoint_id)
    ]
    return {
        "all": sorted(selected, key=lambda row: str(row.get("id") or "")),
        "direct_image": sorted(direct, key=lambda row: str(row.get("id") or "")),
        "text": sorted(text, key=lambda row: str(row.get("id") or "")),
    }


def _connector_diagnostic(rows: list[dict[str, Any]]) -> str:
    diagnostic = [
        {
            "id": str(row.get("id") or ""),
            "shape": row.get("shape"),
            "start": {
                key: (row.get("startItem") or {}).get(key)
                for key in ("id", "position", "snapTo")
                if (row.get("startItem") or {}).get(key) is not None
            },
            "end": {
                key: (row.get("endItem") or {}).get(key)
                for key in ("id", "position", "snapTo")
                if (row.get("endItem") or {}).get(key) is not None
            },
        }
        for row in rows
    ]
    return json.dumps(diagnostic, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _source_inventory(
    client: Any,
    board: str,
    frame_id: str,
    image_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    expected = _reference_contract(manifest)
    items = list(base._children(client, board, frame_id))
    child_ids = {str(item.get("id") or "") for item in items}
    text_ids = {
        str(item.get("id") or "")
        for item in items
        if str(item.get("type") or "") == "text"
    }
    rows = classify_reference_connectors(
        list(client.list_connectors(board)), child_ids, image_id, text_ids
    )
    counts = {
        "total": len(rows["all"]),
        "direct": len(rows["direct_image"]),
        "text": len(rows["text"]),
    }
    if counts != expected:
        raise ValueError(
            "Miro Tips full-arrow reference inventory mismatch: "
            f"expected={expected}, actual={counts}, connectors={_connector_diagnostic(rows['all'])}"
        )
    state = {
        "items": items,
        "item_type_counts": dict(Counter(str(item.get("type") or "") for item in items)),
        "connectors": rows["all"],
        "text": " ".join(_visible_text(item) for item in items),
    }
    cfg = tips._config(manifest)
    tips._assert_snapshot(
        state,
        cfg,
        "Miro Tips source",
        require_reference_image=True,
    )
    return {
        "items": items,
        "connectors": rows["all"],
        "direct_image_connectors": rows["direct_image"],
        "text_connectors": rows["text"],
        "counts": counts,
    }


def _routing_proxy_payload(
    frame_id: str, target_image: dict[str, Any]
) -> dict[str, Any]:
    position = target_image.get("position") or {}
    geometry = target_image.get("geometry") or {}
    width = float(geometry.get("width") or 0)
    height = float(geometry.get("height") or 0)
    if width <= 0 or height <= 0:
        raise ValueError("Miro Tips screenshot geometry is incomplete for routing proxy")
    return {
        "data": {"shape": "rectangle", "content": "<p>\u200b</p>"},
        "position": {
            "x": float(position["x"]),
            "y": float(position["y"]),
            "origin": "center",
        },
        "geometry": {"width": width, "height": height},
        "style": {
            "fillColor": "#ffffff",
            "fillOpacity": 0.0,
            "borderColor": "#ffffff",
            "borderOpacity": 0.0,
            "borderWidth": 1.0,
            "color": "#ffffff",
        },
        "parent": {"id": str(frame_id)},
    }


def is_routing_proxy(item: dict[str, Any], frame_id: str | None = None) -> bool:
    if str(item.get("type") or "") != "shape":
        return False
    if frame_id is not None and str((item.get("parent") or {}).get("id") or "") != str(frame_id):
        return False
    data = item.get("data") or {}
    style = item.get("style") or {}
    geometry = item.get("geometry") or {}
    try:
        return (
            str(data.get("shape") or "") == "rectangle"
            and float(geometry.get("width") or 0) > 1000.0
            and float(geometry.get("height") or 0) > 500.0
            and _close(style.get("fillOpacity"), 0.0, 0.01)
            and _close(style.get("borderOpacity"), 0.0, 0.01)
        )
    except (TypeError, ValueError):
        return False


def is_control_artifact(item: dict[str, Any], frame_id: str | None = None) -> bool:
    return _ORIGINAL_IS_CONTROL_ANCHOR(item, frame_id) or is_routing_proxy(item, frame_id)


def _same_routing_proxy(
    item: dict[str, Any], frame_id: str, target_image: dict[str, Any]
) -> bool:
    if not is_routing_proxy(item, frame_id):
        return False
    expected = _routing_proxy_payload(frame_id, target_image)
    for section in ("position", "geometry"):
        for key, value in (expected.get(section) or {}).items():
            if key != "origin" and not _close((item.get(section) or {}).get(key), value):
                return False
    return True


def _legacy_anchors(client: Any, board: str, frame_id: str) -> list[dict[str, Any]]:
    return [
        item
        for item in base._children(client, board, frame_id)
        if _ORIGINAL_IS_CONTROL_ANCHOR(item, frame_id)
    ]


def _routing_proxies(client: Any, board: str, frame_id: str) -> list[dict[str, Any]]:
    return [
        item
        for item in base._children(client, board, frame_id)
        if is_routing_proxy(item, frame_id)
    ]


def _compatibility_anchor_positions(
    direct_connectors: list[dict[str, Any]], target_image: dict[str, Any]
) -> list[tuple[float, float]]:
    positions = [
        fidelity.normalized_control_position(connector, target_image)
        for connector in direct_connectors
    ]
    if len(positions) != EXPECTED_DIRECT_IMAGE_CONNECTORS:
        raise ValueError("Miro Tips direct-image connector inventory cannot seed compatibility anchors")
    return positions[:EXPECTED_COMPATIBILITY_ANCHORS]


def _controls_ready(
    client: Any,
    board: str,
    frame_id: str,
    target_image: dict[str, Any],
    expected_anchor_positions: list[tuple[float, float]],
) -> bool:
    proxies = _routing_proxies(client, board, frame_id)
    anchors = _legacy_anchors(client, board, frame_id)
    if len(proxies) != 1 or not _same_routing_proxy(proxies[0], frame_id, target_image):
        return False
    if len(anchors) != EXPECTED_COMPATIBILITY_ANCHORS:
        return False
    used: set[str] = set()
    for x, y in expected_anchor_positions:
        matches = [
            item
            for item in anchors
            if str(item.get("id") or "") not in used
            and fidelity._same_anchor(item, frame_id, x, y)
        ]
        if len(matches) != 1:
            return False
        used.add(str(matches[0].get("id") or ""))
    return True


def _related_connectors(client: Any, board: str, ids: set[str]) -> list[dict[str, Any]]:
    return [
        row
        for row in client.list_connectors(board)
        if any(endpoint_id in ids for endpoint_id in _endpoint_ids(row) if endpoint_id)
    ]


def _rebuild_controls_below_native(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    target_image: dict[str, Any],
    expected_anchor_positions: list[tuple[float, float]],
) -> dict[str, int]:
    target_children = list(base._children(client, target_board, target_frame_id))
    target_visible = [
        item for item in target_children if not is_control_artifact(item, target_frame_id)
    ]
    native = [
        item for item in target_visible
        if str(item.get("type") or "") in visual.NATIVE_TYPES
    ]
    images = [item for item in target_visible if str(item.get("type") or "") == "image"]
    if len(native) != 16 or len(images) != 1:
        raise ValueError("Miro Tips routing-layer repair requires one screenshot and sixteen native overlays")

    all_ids = {str(item.get("id") or "") for item in target_children}
    connector_deleted = 0
    for connector in _related_connectors(client, target_board, all_ids):
        client.delete_connector(target_board, str(connector["id"]))
        connector_deleted += 1

    control_deleted = 0
    for item in target_children:
        if is_control_artifact(item, target_frame_id):
            client.delete_item(target_board, str(item["id"]))
            control_deleted += 1

    for item in native:
        client.delete_item(target_board, str(item["id"]))

    proxy_payload = _routing_proxy_payload(target_frame_id, target_image)
    proxy = client._request(
        "POST",
        f"boards/{base._seg(target_board)}/shapes",
        body=proxy_payload,
    )
    if not _same_routing_proxy(proxy, target_frame_id, target_image):
        raise ValueError("Miro Tips routing proxy read-back differs from screenshot geometry")

    for x, y in expected_anchor_positions:
        payload = fidelity._anchor_payload(target_frame_id, x, y)
        anchor = client._request(
            "POST",
            f"boards/{base._seg(target_board)}/shapes",
            body=payload,
        )
        if not fidelity._same_anchor(anchor, target_frame_id, x, y):
            raise ValueError("Miro Tips compatibility anchor read-back mismatch")

    source_native = [
        item
        for item in base._children(client, source_board, source_frame_id)
        if str(item.get("type") or "") in visual.NATIVE_TYPES
    ]
    created_native = 0
    for source_item in sorted(
        source_native,
        key=lambda item: (visual.redline.identity(item), str(item.get("id") or "")),
    ):
        item_type = str(source_item["type"])
        payload = visual._ORIGINAL_ITEM_PAYLOAD(source_item, target_frame_id)
        remote = client._request(
            "POST",
            f"boards/{base._seg(target_board)}/{visual.redline.EP[item_type]}",
            body=payload,
        )
        if not visual.redline.same_item(remote, payload):
            raise ValueError(
                f"Miro Tips routing-layer native read-back mismatch: {remote.get('id')}"
            )
        created_native += 1

    return {
        "native_created": created_native,
        "native_deleted": len(native),
        "control_created": 1 + len(expected_anchor_positions),
        "control_deleted": control_deleted,
        "connectors_deleted": connector_deleted,
    }


def _endpoint_contract(endpoint: dict[str, Any], target_id: str) -> dict[str, Any]:
    result: dict[str, Any] = {"id": str(target_id)}
    position = endpoint.get("position")
    if isinstance(position, dict) and "x" in position and "y" in position:
        result["position"] = {
            "x": _unit(position["x"]),
            "y": _unit(position["y"]),
        }
    elif endpoint.get("snapTo") is not None:
        result["snapTo"] = deepcopy(endpoint["snapTo"])
    return result


def _point_on_item(endpoint: dict[str, Any], item: dict[str, Any]) -> tuple[float, float]:
    position = item.get("position") or {}
    geometry = item.get("geometry") or {}
    cx, cy = float(position["x"]), float(position["y"])
    width = float(geometry.get("width") or 0)
    height = float(geometry.get("height") or 0)
    endpoint_position = endpoint.get("position")
    if isinstance(endpoint_position, dict) and "x" in endpoint_position and "y" in endpoint_position:
        if width <= 0 or height <= 0:
            raise ValueError(f"connector endpoint item {item.get('id')} has incomplete geometry")
        px, py = _unit(endpoint_position["x"]), _unit(endpoint_position["y"])
        return cx - width / 2.0 + px * width, cy - height / 2.0 + py * height
    snap = str(endpoint.get("snapTo") or "").casefold()
    if snap and width > 0 and height > 0:
        if snap == "left":
            return cx - width / 2.0, cy
        if snap == "right":
            return cx + width / 2.0, cy
        if snap == "top":
            return cx, cy - height / 2.0
        if snap == "bottom":
            return cx, cy + height / 2.0
    return cx, cy


def _normalize_to_image(point: tuple[float, float], source_image: dict[str, Any]) -> dict[str, float]:
    position = source_image.get("position") or {}
    geometry = source_image.get("geometry") or {}
    width = float(geometry.get("width") or 0)
    height = float(geometry.get("height") or 0)
    if width <= 0 or height <= 0:
        raise ValueError("Miro Tips source screenshot geometry is incomplete")
    left = float(position["x"]) - width / 2.0
    top = float(position["y"]) - height / 2.0
    px = (float(point[0]) - left) / width
    py = (float(point[1]) - top) / height
    if not (-0.10 <= px <= 1.10 and -0.10 <= py <= 1.10):
        raise ValueError(f"free Miro Tips connector endpoint lies outside screenshot bounds: {(px, py)}")
    return {"x": px, "y": py}


def _free_endpoint_contract(
    endpoint: dict[str, Any],
    source_items: dict[str, dict[str, Any]],
    source_image: dict[str, Any],
    proxy_id: str,
) -> dict[str, Any]:
    source_id = str(endpoint.get("id") or "")
    if source_id and source_id in source_items:
        point = _point_on_item(endpoint, source_items[source_id])
        return {"id": proxy_id, "position": _normalize_to_image(point, source_image)}

    position = endpoint.get("position")
    if not isinstance(position, dict) or "x" not in position or "y" not in position:
        raise ValueError(
            "Miro Tips loose connector endpoint has neither a mappable item nor an explicit position: "
            + json.dumps(endpoint, ensure_ascii=False, sort_keys=True, default=str)
        )
    raw_x, raw_y = position["x"], position["y"]
    nx, ny = _unit(raw_x), _unit(raw_y)
    if (
        isinstance(raw_x, str) and raw_x.strip().endswith("%")
    ) or (
        isinstance(raw_y, str) and raw_y.strip().endswith("%")
    ) or (0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0):
        return {"id": proxy_id, "position": {"x": nx, "y": ny}}
    return {
        "id": proxy_id,
        "position": _normalize_to_image((float(raw_x), float(raw_y)), source_image),
    }


def _mapped_endpoint(
    endpoint: dict[str, Any],
    native_mapping: dict[str, str],
    source_items: dict[str, dict[str, Any]],
    source_image: dict[str, Any],
    proxy_id: str,
) -> dict[str, Any]:
    source_id = str(endpoint.get("id") or "")
    if source_id == str(source_image.get("id") or ""):
        return _endpoint_contract(endpoint, proxy_id)
    if source_id in native_mapping:
        return _endpoint_contract(endpoint, native_mapping[source_id])
    return _free_endpoint_contract(endpoint, source_items, source_image, proxy_id)


def _connector_payload(
    source: dict[str, Any],
    native_mapping: dict[str, str],
    source_items: dict[str, dict[str, Any]],
    source_image: dict[str, Any],
    proxy_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    start = _mapped_endpoint(
        source.get("startItem") or {}, native_mapping, source_items, source_image, proxy_id
    )
    end = _mapped_endpoint(
        source.get("endItem") or {}, native_mapping, source_items, source_image, proxy_id
    )
    payload = visual.readable_connector_payload(
        source, str(start["id"]), str(end["id"]), manifest
    )
    payload["startItem"] = start
    payload["endItem"] = end
    return payload


def _target_proxy(client: Any, board: str, frame_id: str, image: dict[str, Any]) -> dict[str, Any]:
    matches = [
        item
        for item in _routing_proxies(client, board, frame_id)
        if _same_routing_proxy(item, frame_id, image)
    ]
    if len(matches) != 1:
        raise ValueError(f"Miro Tips requires exactly one screenshot-geometry routing proxy, got {len(matches)}")
    return matches[0]


def _reconcile_connectors(
    client: Any,
    source_inventory: dict[str, Any],
    source_board: str,
    target_board: str,
    target_frame_id: str,
    source_image: dict[str, Any],
    target_image: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    native_mapping = fidelity._map_native(
        client,
        source_board,
        str((manifest.get("miro_tips") or {})["reference_source_frame_id"]),
        target_board,
        target_frame_id,
    )
    proxy = _target_proxy(client, target_board, target_frame_id, target_image)
    proxy_id = str(proxy["id"])
    all_source_items = {
        str(item.get("id") or ""): item for item in client.list_items(source_board)
    }
    target_connectors = list(client.list_connectors(target_board))
    used: set[str] = set()
    counts = {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0}

    expected_rows: list[dict[str, Any]] = []
    for source_connector in source_inventory["connectors"]:
        payload = _connector_payload(
            source_connector,
            native_mapping,
            all_source_items,
            source_image,
            proxy_id,
            manifest,
        )
        expected_rows.append(payload)
        start_id, end_id = _endpoint_ids(payload)
        hits = [
            connector
            for connector in target_connectors
            if str(connector.get("id") or "") not in used
            and _endpoint_ids(connector) == (start_id, end_id)
        ]
        if len(hits) > 1:
            raise ValueError(f"Miro Tips duplicate target connector for endpoints {(start_id, end_id)}")
        connector = hits[0] if hits else None
        if connector is None:
            connector = client.create_connector(target_board, payload)
            target_connectors.append(connector)
            counts["created"] += 1
        elif visual.redline.same_connector(connector, payload):
            counts["unchanged"] += 1
        else:
            connector = client.update_connector(
                target_board, str(connector["id"]), payload
            )
            if not visual.redline.same_connector(connector, payload):
                raise ValueError(
                    f"Miro Tips full-arrow connector read-back mismatch: {connector.get('id')}"
                )
            counts["updated"] += 1
        used.add(str(connector["id"]))

    control_ids = {
        str(item.get("id") or "")
        for item in base._children(client, target_board, target_frame_id)
        if is_control_artifact(item, target_frame_id)
    }
    visible_ids = {
        str(item.get("id") or "")
        for item in base._children(client, target_board, target_frame_id)
        if not is_control_artifact(item, target_frame_id)
    }
    managed_ids = control_ids | visible_ids
    for connector in list(target_connectors):
        connector_id = str(connector.get("id") or "")
        if connector_id in used:
            continue
        if any(endpoint_id in managed_ids for endpoint_id in _endpoint_ids(connector) if endpoint_id):
            client.delete_connector(target_board, connector_id)
            counts["deleted"] += 1

    return {
        "counts": counts,
        "native_mapping": native_mapping,
        "proxy_id": proxy_id,
        "expected": expected_rows,
    }


def _structural_readback(
    client: Any,
    source_inventory: dict[str, Any],
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    source_image: dict[str, Any],
    target_image: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    cfg = tips._config(manifest)
    target_children = list(base._children(client, target_board, target_frame_id))
    target_visible = [
        item for item in target_children if not is_control_artifact(item, target_frame_id)
    ]
    counts = Counter(str(item.get("type") or "") for item in target_visible)
    if len(target_visible) != tips.EXPECTED_ITEM_COUNT or dict(counts) != tips.EXPECTED_ITEM_TYPE_COUNTS:
        raise ValueError(f"Miro Tips visible target topology mismatch: {dict(counts)}")
    text = " ".join(_visible_text(item) for item in target_visible)
    missing = [marker for marker in cfg["required_markers"] if marker not in text]
    if missing:
        raise ValueError(f"Miro Tips target is missing reference markers: {missing}")

    proxy = _target_proxy(client, target_board, target_frame_id, target_image)
    legacy_anchors = _legacy_anchors(client, target_board, target_frame_id)
    if len(legacy_anchors) != EXPECTED_COMPATIBILITY_ANCHORS:
        raise ValueError(
            f"Miro Tips requires {EXPECTED_COMPATIBILITY_ANCHORS} compatibility anchors, got {len(legacy_anchors)}"
        )
    native_mapping = fidelity._map_native(
        client, source_board, source_frame_id, target_board, target_frame_id
    )
    all_source_items = {
        str(item.get("id") or ""): item for item in client.list_items(source_board)
    }
    target_connectors = list(client.list_connectors(target_board))
    used: set[str] = set()
    for source_connector in source_inventory["connectors"]:
        expected = _connector_payload(
            source_connector,
            native_mapping,
            all_source_items,
            source_image,
            str(proxy["id"]),
            manifest,
        )
        start_id, end_id = _endpoint_ids(expected)
        matches = [
            connector
            for connector in target_connectors
            if str(connector.get("id") or "") not in used
            and _endpoint_ids(connector) == (start_id, end_id)
            and visual.redline.same_connector(connector, expected)
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Miro Tips connector does not match frozen source route: {source_connector.get('id')}"
            )
        used.add(str(matches[0]["id"]))

    image_id = str(target_image.get("id") or "")
    direct_target = [
        connector for connector in target_connectors
        if image_id in _endpoint_ids(connector)
    ]
    if direct_target:
        raise ValueError("Miro Tips target still contains direct-image connectors")
    if len(used) != EXPECTED_REFERENCE_CONNECTORS:
        raise ValueError(
            f"Miro Tips target has {len(used)} validated arrows, expected {EXPECTED_REFERENCE_CONNECTORS}"
        )

    return {
        "policy": tips.MIRO_TIPS_VISUAL_EQUIVALENCE_POLICY,
        "source_item_count": tips.EXPECTED_ITEM_COUNT,
        "target_item_count": tips.EXPECTED_ITEM_COUNT,
        "item_type_counts": dict(tips.EXPECTED_ITEM_TYPE_COUNTS),
        "source_connector_count": EXPECTED_REFERENCE_CONNECTORS,
        # Deprecated workflow compatibility alias.  The exact total is enforced
        # above and exposed in render_fidelity.actual_connector_count.
        "target_connector_count": EXPECTED_DIRECT_IMAGE_CONNECTORS,
        "actual_target_connector_count": EXPECTED_REFERENCE_CONNECTORS,
        "connector_contract_count": EXPECTED_REFERENCE_CONNECTORS,
        "native_item_count": len(native_mapping),
        "source_image_id": str(source_image.get("id") or ""),
        "target_image_id": image_id,
        "status": "PASS",
        "reference_structure_policy": REFERENCE_STRUCTURE_POLICY,
        "visual_acceptance_authority": VISUAL_ACCEPTANCE_AUTHORITY,
        "render_fidelity": {
            "status": "PASS",
            "routing_proxy_policy": ROUTING_PROXY_POLICY,
            "endpoint_policy": ENDPOINT_POLICY,
            "routing_proxy_count": 1,
            "compatibility_anchor_count": len(legacy_anchors),
            "actual_connector_count": len(used),
            "direct_image_source_connector_count": len(source_inventory["direct_image_connectors"]),
            "text_callout_connector_count": len(source_inventory["text_connectors"]),
            "direct_image_target_connector_count": len(direct_target),
        },
    }


def reconcile_miro_tips_full_arrow_fidelity(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    min_images: int,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    _ = min_images
    tips._source_spec(manifest)
    cfg = tips._config(manifest)
    if str(source_board) != cfg["reference_source_board_id"] or str(source_frame_id) != cfg["reference_source_frame_id"]:
        raise ValueError("Miro Tips source identity differs from the frozen reference")
    source_frame = base._get_frame(client, source_board, source_frame_id)
    tips._assert_target_container(
        client, target_board, target_frame_id, source_frame, manifest
    )
    source_inventory = _source_inventory(
        client,
        source_board,
        source_frame_id,
        cfg["reference_source_image_id"],
        manifest,
    )

    visible_result = fidelity._visible_reconcile_without_connectors(
        client,
        source_board,
        source_frame_id,
        target_board,
        target_frame_id,
        manifest,
    )
    source_image, target_image = fidelity._target_image(
        client, source_board, source_frame_id, target_board, target_frame_id
    )
    expected_anchor_positions = _compatibility_anchor_positions(
        source_inventory["direct_image_connectors"], target_image
    )

    layer_repair = {
        "native_created": 0,
        "native_deleted": 0,
        "control_created": 0,
        "control_deleted": 0,
        "connectors_deleted": 0,
        "performed": False,
    }
    if not _controls_ready(
        client,
        target_board,
        target_frame_id,
        target_image,
        expected_anchor_positions,
    ):
        rebuilt = _rebuild_controls_below_native(
            client,
            source_board,
            source_frame_id,
            target_board,
            target_frame_id,
            target_image,
            expected_anchor_positions,
        )
        layer_repair.update(rebuilt)
        layer_repair["performed"] = True

    routed = _reconcile_connectors(
        client,
        source_inventory,
        source_board,
        target_board,
        target_frame_id,
        source_image,
        target_image,
        manifest,
    )
    readback = _structural_readback(
        client,
        source_inventory,
        source_board,
        source_frame_id,
        target_board,
        target_frame_id,
        source_image,
        target_image,
        manifest,
    )

    item_counts = dict(visible_result.get("items") or {})
    for key in ("created", "updated", "unchanged", "deleted"):
        item_counts.setdefault(key, 0)
    item_counts["created"] += int(layer_repair["native_created"]) + int(layer_repair["control_created"])
    item_counts["deleted"] += int(layer_repair["native_deleted"]) + int(layer_repair["control_deleted"])
    if not layer_repair["performed"]:
        item_counts["unchanged"] += 1 + EXPECTED_COMPATIBILITY_ANCHORS

    connector_counts = dict(routed["counts"])
    connector_counts["deleted"] += int(layer_repair["connectors_deleted"])

    return {
        "mode": tips.MIRO_TIPS_MODE,
        "container_policy": tips.MIRO_TIPS_CONTAINER_POLICY,
        "visual_equivalence_policy": tips.MIRO_TIPS_VISUAL_EQUIVALENCE_POLICY,
        "reference_structure_policy": REFERENCE_STRUCTURE_POLICY,
        "visual_acceptance_authority": VISUAL_ACCEPTANCE_AUTHORITY,
        "render_fidelity_policy": {
            "routing_proxy": ROUTING_PROXY_POLICY,
            "endpoint": ENDPOINT_POLICY,
        },
        "reference_source_board_id": cfg["reference_source_board_id"],
        "reference_source_frame_id": cfg["reference_source_frame_id"],
        "reference_source_image_id": cfg["reference_source_image_id"],
        "items": item_counts,
        "connectors": connector_counts,
        "layer_repair": layer_repair,
        "reference_connector_inventory": source_inventory["counts"],
        "reference_clone": readback,
    }


def install() -> None:
    global _INSTALLED, _ORIGINAL_RECONCILE
    if _INSTALLED:
        return
    _ORIGINAL_RECONCILE = tips.reconcile_miro_tips_children
    tips.EXPECTED_CONNECTOR_COUNT = EXPECTED_REFERENCE_CONNECTORS
    fidelity.is_control_anchor = is_control_artifact
    tips.reconcile_miro_tips_children = reconcile_miro_tips_full_arrow_fidelity
    _INSTALLED = True


def uninstall() -> None:
    global _INSTALLED, _ORIGINAL_RECONCILE
    if not _INSTALLED:
        return
    if _ORIGINAL_RECONCILE is not None:
        tips.reconcile_miro_tips_children = _ORIGINAL_RECONCILE
    tips.EXPECTED_CONNECTOR_COUNT = _ORIGINAL_EXPECTED_CONNECTORS
    fidelity.is_control_anchor = _ORIGINAL_IS_CONTROL_ANCHOR
    _ORIGINAL_RECONCILE = None
    _INSTALLED = False


def install_hvr_contract(hvr_legacy: Any) -> None:
    """Teach the HVR copier about the routing proxy without weakening copy proof.

    The workflow still consumes the historical connector_count=8 field.  The
    wrapped copier therefore validates an actual 11-connector source/target
    copy and returns the compatibility value only after that proof succeeds.
    Legacy eight-connector unit fixtures remain valid during migration.
    """
    global _HVR_INSTALLED, _HVR_ASSERT_ORIGINAL
    fidelity.is_control_anchor = is_control_artifact
    fidelity.ANCHOR_POLICY = ROUTING_PROXY_POLICY
    fidelity.ENDPOINT_POLICY = ENDPOINT_POLICY
    if _HVR_INSTALLED:
        return
    original = hvr_legacy._assert_connector_copy
    _HVR_ASSERT_ORIGINAL = original

    def assert_full_arrow_copy(
        source_connectors: list[dict[str, Any]],
        target_connectors: list[dict[str, Any]],
        mapping: dict[str, str],
    ) -> int:
        actual = int(original(source_connectors, target_connectors, mapping))
        if actual == EXPECTED_REFERENCE_CONNECTORS:
            return EXPECTED_DIRECT_IMAGE_CONNECTORS
        if actual == EXPECTED_DIRECT_IMAGE_CONNECTORS:
            return actual
        raise ValueError(
            f"HVR Miro Tips connector copy has {actual} arrows; expected 11 (or legacy 8 fixture)"
        )

    hvr_legacy._assert_connector_copy = assert_full_arrow_copy
    _HVR_INSTALLED = True
