from __future__ import annotations

"""Render-fidelity repair for the frozen PR8 Miro Tips reference.

The visible reference remains a no-design zone: one screenshot, thirteen sticky
notes, three text items and eight curved callout connectors.  Miro normalizes a
connector attached directly to an image, however, so the target uses tiny
transparent technical anchors at the exact reference arrowhead coordinates.
The background screenshot is retained while visible native callouts are
recreated once after it, establishing the required back-to-front write order.

The technical anchors are transport mechanics only.  They are deliberately
excluded from the visible reference topology and can never constitute human
visual acceptance.
"""

from copy import deepcopy
from typing import Any

from . import miro_tips_hvr_fix as tips
from . import review_board_recovery as base
from . import review_board_recovery_wirefix as visual


LAYER_POLICY = "background_image_before_native_callouts_v2"
ANCHOR_POLICY = "transparent_control_anchor_from_reference_arrowhead_v2"
ENDPOINT_POLICY = "reference_arrowhead_position_to_control_anchor_v2"
REFERENCE_STRUCTURE_POLICY = "exact_reference_child_snapshot"
VISUAL_ACCEPTANCE_AUTHORITY = "human_review_only"
CONTROL_ANCHOR_SIZE = 8.0
EXPECTED_CONTROL_ANCHORS = tips.EXPECTED_CONNECTOR_COUNT

_ORIGINAL_RECONCILE_MIRO_TIPS_CHILDREN = tips.reconcile_miro_tips_children
_INSTALLED = False


def _close(left: Any, right: Any, tolerance: float = 0.75) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return left == right


def _unit(value: Any) -> float:
    if isinstance(value, str) and value.strip().endswith("%"):
        return float(value.strip()[:-1]) / 100.0
    number = float(value)
    if number > 1.0:
        number /= 100.0
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"Miro Tips reference endpoint coordinate is out of range: {value!r}")
    return number


def is_control_anchor(item: dict[str, Any], frame_id: str | None = None) -> bool:
    if str(item.get("type") or "") != "shape":
        return False
    if frame_id is not None and str((item.get("parent") or {}).get("id") or "") != str(frame_id):
        return False
    data = item.get("data") or {}
    geometry = item.get("geometry") or {}
    style = item.get("style") or {}
    return (
        str(data.get("shape") or "") == "circle"
        and _close(geometry.get("width"), CONTROL_ANCHOR_SIZE)
        and _close(geometry.get("height"), CONTROL_ANCHOR_SIZE)
        and _close(style.get("fillOpacity"), 0.0, tolerance=0.01)
        and _close(style.get("borderOpacity"), 0.0, tolerance=0.01)
    )


def _anchor_payload(frame_id: str, x: float, y: float) -> dict[str, Any]:
    return {
        "data": {"shape": "circle", "content": "<p>\u200b</p>"},
        "position": {"x": float(x), "y": float(y), "origin": "center"},
        "geometry": {"width": CONTROL_ANCHOR_SIZE, "height": CONTROL_ANCHOR_SIZE},
        "style": {
            "fillColor": "#ffffff",
            "fillOpacity": 0.0,
            "borderColor": "#ffffff",
            "borderOpacity": 0.0,
            "borderWidth": 1.0,
            "color": "#ffffff",
            "fontSize": 8,
        },
        "parent": {"id": str(frame_id)},
    }


def _same_anchor(item: dict[str, Any], frame_id: str, x: float, y: float) -> bool:
    if not is_control_anchor(item, frame_id):
        return False
    position = item.get("position") or {}
    return _close(position.get("x"), x) and _close(position.get("y"), y)


def _children(client: Any, board: str, frame_id: str) -> list[dict[str, Any]]:
    return list(base._children(client, board, frame_id))


def _visible_children(client: Any, board: str, frame_id: str) -> list[dict[str, Any]]:
    return [
        item for item in _children(client, board, frame_id)
        if not is_control_anchor(item, frame_id)
    ]


def _anchors(client: Any, board: str, frame_id: str) -> list[dict[str, Any]]:
    return [
        item for item in _children(client, board, frame_id)
        if is_control_anchor(item, frame_id)
    ]


def _endpoint_ids(connector: dict[str, Any]) -> tuple[str, str]:
    return (
        str((connector.get("startItem") or {}).get("id") or ""),
        str((connector.get("endItem") or {}).get("id") or ""),
    )


def _related_connectors(client: Any, board: str, item_ids: set[str]) -> list[dict[str, Any]]:
    return [
        connector for connector in client.list_connectors(board)
        if _endpoint_ids(connector)[0] in item_ids or _endpoint_ids(connector)[1] in item_ids
    ]


def _source_connectors(
    client: Any, board: str, frame_id: str, image_id: str
) -> list[dict[str, Any]]:
    children = _visible_children(client, board, frame_id)
    native_ids = {
        str(item.get("id") or "")
        for item in children
        if str(item.get("type") or "") in visual.NATIVE_TYPES
    }
    rows = [
        connector for connector in client.list_connectors(board)
        if _endpoint_ids(connector)[0] in native_ids
        and _endpoint_ids(connector)[1] == image_id
    ]
    if len(rows) != tips.EXPECTED_CONNECTOR_COUNT:
        raise ValueError(
            f"Miro Tips frozen reference requires {tips.EXPECTED_CONNECTOR_COUNT} direct-image callouts, got {len(rows)}"
        )
    for connector in rows:
        endpoint = connector.get("endItem") or {}
        position = endpoint.get("position") or {}
        if "x" not in position or "y" not in position:
            raise ValueError(
                f"Miro Tips frozen reference connector {connector.get('id')} has no explicit arrowhead position"
            )
        _unit(position["x"])
        _unit(position["y"])
    return sorted(rows, key=lambda row: str(row.get("id") or ""))


def _target_image(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_images = [
        item for item in _visible_children(client, source_board, source_frame_id)
        if str(item.get("type") or "") == "image"
    ]
    target_images = [
        item for item in _visible_children(client, target_board, target_frame_id)
        if str(item.get("type") or "") == "image"
    ]
    if len(source_images) != 1 or len(target_images) != 1:
        raise ValueError("Miro Tips render-fidelity contract requires one source and one target image")
    source = source_images[0]
    matches = [
        item for item in target_images
        if visual._same_image(item, source, target_frame_id)
    ]
    if len(matches) != 1:
        raise ValueError("Miro Tips target background image geometry differs from the frozen reference")
    return source, matches[0]


def normalized_control_position(
    source_connector: dict[str, Any], target_image: dict[str, Any]
) -> tuple[float, float]:
    position = (source_connector.get("endItem") or {}).get("position") or {}
    if "x" not in position or "y" not in position:
        raise ValueError(
            f"Miro Tips source connector {source_connector.get('id')} has no explicit arrowhead position"
        )
    px, py = _unit(position["x"]), _unit(position["y"])
    image_position = target_image.get("position") or {}
    geometry = target_image.get("geometry") or {}
    width = float(geometry.get("width") or 0)
    height = float(geometry.get("height") or 0)
    if width <= 0 or height <= 0:
        raise ValueError("Miro Tips target background has invalid geometry")
    x = float(image_position["x"]) - width / 2.0 + px * width
    y = float(image_position["y"]) - height / 2.0 + py * height
    return x, y


def _map_native(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
) -> dict[str, str]:
    source = [
        item for item in _visible_children(client, source_board, source_frame_id)
        if str(item.get("type") or "") in visual.NATIVE_TYPES
    ]
    target = [
        item for item in _visible_children(client, target_board, target_frame_id)
        if str(item.get("type") or "") in visual.NATIVE_TYPES
    ]
    if len(source) != 16 or len(target) != 16:
        raise ValueError("Miro Tips visible native topology must contain exactly sixteen callout items")
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for source_item in sorted(
        source,
        key=lambda item: (visual.redline.identity(item), str(item.get("id") or "")),
    ):
        target_item = visual.redline.match(source_item, target, used)
        expected = visual._ORIGINAL_ITEM_PAYLOAD(source_item, target_frame_id)
        if target_item is None or not visual.redline.same_item(target_item, expected):
            raise ValueError(
                f"Miro Tips target native item differs from frozen reference: {source_item.get('id')}"
            )
        source_id = str(source_item.get("id") or "")
        target_id = str(target_item.get("id") or "")
        mapping[source_id] = target_id
        used.add(target_id)
    return mapping


def _visible_reconcile_without_connectors(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    original_children = base._children
    original_connectors = visual._companion_source_connectors

    def filtered_children(c: Any, board: str, frame_id: str) -> list[dict[str, Any]]:
        rows = list(original_children(c, board, frame_id))
        if str(board) == str(target_board) and str(frame_id) == str(target_frame_id):
            rows = [item for item in rows if not is_control_anchor(item, target_frame_id)]
        return rows

    base._children = filtered_children
    visual._companion_source_connectors = lambda *_args, **_kwargs: []
    try:
        return tips._ORIGINAL_RECONCILE_COMPANION_CHILDREN(
            client,
            source_board,
            source_frame_id,
            target_board,
            target_frame_id,
            1,
            manifest,
        )
    finally:
        base._children = original_children
        visual._companion_source_connectors = original_connectors


def _cleanup_control_anchors(client: Any, board: str, frame_id: str) -> dict[str, int]:
    anchors = _anchors(client, board, frame_id)
    ids = {str(item.get("id") or "") for item in anchors}
    connector_deleted = 0
    for connector in _related_connectors(client, board, ids):
        client.delete_connector(board, str(connector["id"]))
        connector_deleted += 1
    for item in anchors:
        client.delete_item(board, str(item["id"]))
    return {"items_deleted": len(anchors), "connectors_deleted": connector_deleted}


def _rebuild_native_above_background(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
) -> dict[str, int]:
    """Keep the screenshot, then recreate native callouts so they are above it."""
    cleanup = _cleanup_control_anchors(client, target_board, target_frame_id)
    target_visible = _visible_children(client, target_board, target_frame_id)
    images = [item for item in target_visible if str(item.get("type") or "") == "image"]
    native = [item for item in target_visible if str(item.get("type") or "") in visual.NATIVE_TYPES]
    if len(images) != 1 or len(native) != 16:
        raise ValueError("Miro Tips layer repair requires one retained background and sixteen native callouts")
    visible_ids = {str(item.get("id") or "") for item in target_visible}
    connector_deleted = cleanup["connectors_deleted"]
    for connector in _related_connectors(client, target_board, visible_ids):
        client.delete_connector(target_board, str(connector["id"]))
        connector_deleted += 1
    for item in native:
        client.delete_item(target_board, str(item["id"]))

    source_native = [
        item for item in _visible_children(client, source_board, source_frame_id)
        if str(item.get("type") or "") in visual.NATIVE_TYPES
    ]
    created = 0
    for source_item in sorted(
        source_native,
        key=lambda item: (visual.redline.identity(item), str(item.get("id") or "")),
    ):
        item_type = str(source_item["type"])
        endpoint = visual.redline.EP[item_type]
        payload = visual._ORIGINAL_ITEM_PAYLOAD(source_item, target_frame_id)
        remote = client._request(
            "POST",
            f"boards/{base._seg(target_board)}/{endpoint}",
            body=payload,
        )
        if not visual.redline.same_item(remote, payload):
            raise ValueError(
                f"Miro Tips layer repair read-back mismatch for native item {remote.get('id')}"
            )
        created += 1
    return {
        "native_created": created,
        "native_deleted": len(native),
        "technical_anchor_deleted": cleanup["items_deleted"],
        "connectors_deleted": connector_deleted,
    }


def _control_connector_payload(
    source: dict[str, Any], start_id: str, anchor_id: str, manifest: dict[str, Any]
) -> dict[str, Any]:
    payload = visual.readable_connector_payload(source, start_id, anchor_id, manifest)
    payload["endItem"] = {"id": str(anchor_id)}
    return payload


def _reconcile_anchors_and_connectors(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    source_image, target_image = _target_image(
        client, source_board, source_frame_id, target_board, target_frame_id
    )
    source_connectors = _source_connectors(
        client, source_board, source_frame_id, str(source_image["id"])
    )
    native_mapping = _map_native(
        client, source_board, source_frame_id, target_board, target_frame_id
    )

    target_anchors = _anchors(client, target_board, target_frame_id)
    used_anchors: set[str] = set()
    connector_rows = client.list_connectors(target_board)
    used_connectors: set[str] = set()
    anchor_counts = {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0}
    connector_counts = {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0}
    expected_positions: list[dict[str, Any]] = []

    for source_connector in source_connectors:
        source_start = str((source_connector.get("startItem") or {}).get("id") or "")
        target_start = native_mapping.get(source_start)
        if not target_start:
            raise ValueError(
                f"Miro Tips source connector {source_connector.get('id')} start item is not mapped"
            )
        x, y = normalized_control_position(source_connector, target_image)
        expected_positions.append({
            "source_connector_id": str(source_connector.get("id") or ""),
            "x": x,
            "y": y,
        })
        matches = [
            item for item in target_anchors
            if str(item.get("id") or "") not in used_anchors
            and _same_anchor(item, target_frame_id, x, y)
        ]
        if len(matches) > 1:
            raise ValueError(
                f"Miro Tips has duplicate technical anchors at reference endpoint {source_connector.get('id')}"
            )
        anchor = matches[0] if matches else None
        payload = _anchor_payload(target_frame_id, x, y)
        if anchor is None:
            anchor = client._request(
                "POST",
                f"boards/{base._seg(target_board)}/shapes",
                body=payload,
            )
            target_anchors.append(anchor)
            anchor_counts["created"] += 1
        elif _same_anchor(anchor, target_frame_id, x, y):
            anchor_counts["unchanged"] += 1
        else:
            anchor = client._request(
                "PATCH",
                f"boards/{base._seg(target_board)}/shapes/{base._seg(str(anchor['id']))}",
                body=payload,
            )
            anchor_counts["updated"] += 1
        if not _same_anchor(anchor, target_frame_id, x, y):
            raise ValueError(
                f"Miro Tips technical anchor read-back mismatch for source connector {source_connector.get('id')}"
            )
        anchor_id = str(anchor["id"])
        used_anchors.add(anchor_id)

        connector_payload = _control_connector_payload(
            source_connector, target_start, anchor_id, manifest
        )
        connector_matches = [
            connector for connector in connector_rows
            if str(connector.get("id") or "") not in used_connectors
            and _endpoint_ids(connector) == (target_start, anchor_id)
        ]
        if len(connector_matches) > 1:
            raise ValueError(
                f"Miro Tips has duplicate connectors for technical anchor {anchor_id}"
            )
        connector = connector_matches[0] if connector_matches else None
        if connector is None:
            connector = client.create_connector(target_board, connector_payload)
            connector_rows.append(connector)
            connector_counts["created"] += 1
        elif visual.redline.same_connector(connector, connector_payload):
            connector_counts["unchanged"] += 1
        else:
            connector = client.update_connector(
                target_board, str(connector["id"]), connector_payload
            )
            connector_counts["updated"] += 1
            if not visual.redline.same_connector(connector, connector_payload):
                raise ValueError(
                    f"Miro Tips technical-anchor connector {connector.get('id')} read-back mismatch"
                )
        used_connectors.add(str(connector["id"]))

    for anchor in list(target_anchors):
        anchor_id = str(anchor.get("id") or "")
        if anchor_id and anchor_id not in used_anchors:
            for connector in _related_connectors(client, target_board, {anchor_id}):
                connector_id = str(connector.get("id") or "")
                if connector_id and connector_id not in used_connectors:
                    client.delete_connector(target_board, connector_id)
                    connector_counts["deleted"] += 1
            client.delete_item(target_board, anchor_id)
            anchor_counts["deleted"] += 1

    visible_target_ids = {
        str(item.get("id") or "")
        for item in _visible_children(client, target_board, target_frame_id)
    }
    current_anchor_ids = {
        str(item.get("id") or "")
        for item in _anchors(client, target_board, target_frame_id)
    }
    for connector in list(client.list_connectors(target_board)):
        connector_id = str(connector.get("id") or "")
        start_id, end_id = _endpoint_ids(connector)
        if connector_id in used_connectors:
            continue
        if start_id in visible_target_ids or end_id in visible_target_ids or end_id in current_anchor_ids:
            client.delete_connector(target_board, connector_id)
            connector_counts["deleted"] += 1

    return {
        "anchor_items": anchor_counts,
        "connectors": connector_counts,
        "control_anchor_count": len(_anchors(client, target_board, target_frame_id)),
        "control_anchor_connector_count": len(used_connectors),
        "expected_positions": expected_positions,
    }


def _structural_readback(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    cfg = tips._config(manifest)
    source_state = tips._state(client, source_board, source_frame_id)
    tips._assert_snapshot(
        source_state, cfg, "Miro Tips source", require_reference_image=True
    )

    target_visible = _visible_children(client, target_board, target_frame_id)
    target_text = " ".join(
        tips._visible((item.get("data") or {}).get("content")) for item in target_visible
    )
    target_counts: dict[str, int] = {}
    for item in target_visible:
        kind = str(item.get("type") or "")
        target_counts[kind] = target_counts.get(kind, 0) + 1
    if len(target_visible) != tips.EXPECTED_ITEM_COUNT:
        raise ValueError("Miro Tips visible target item count differs from frozen reference")
    if target_counts != tips.EXPECTED_ITEM_TYPE_COUNTS:
        raise ValueError(
            f"Miro Tips visible target item types differ from frozen reference: {target_counts}"
        )
    missing = [marker for marker in cfg["required_markers"] if marker not in target_text]
    if missing:
        raise ValueError(f"Miro Tips target is missing frozen reference markers: {missing}")

    native_mapping = _map_native(
        client, source_board, source_frame_id, target_board, target_frame_id
    )
    source_image, target_image = _target_image(
        client, source_board, source_frame_id, target_board, target_frame_id
    )
    source_connectors = _source_connectors(
        client, source_board, source_frame_id, str(source_image["id"])
    )
    anchors = _anchors(client, target_board, target_frame_id)
    if len(anchors) != EXPECTED_CONTROL_ANCHORS:
        raise ValueError(
            f"Miro Tips requires {EXPECTED_CONTROL_ANCHORS} transparent target anchors, got {len(anchors)}"
        )

    used_anchors: set[str] = set()
    used_connectors: set[str] = set()
    target_connectors = client.list_connectors(target_board)
    target_image_id = str(target_image.get("id") or "")
    direct_image_connectors = [
        connector for connector in target_connectors
        if _endpoint_ids(connector)[1] == target_image_id
    ]
    if direct_image_connectors:
        raise ValueError("Miro Tips target still contains direct-image callout connectors")

    for source_connector in source_connectors:
        target_start = native_mapping[
            str((source_connector.get("startItem") or {}).get("id") or "")
        ]
        x, y = normalized_control_position(source_connector, target_image)
        anchor_matches = [
            anchor for anchor in anchors
            if str(anchor.get("id") or "") not in used_anchors
            and _same_anchor(anchor, target_frame_id, x, y)
        ]
        if len(anchor_matches) != 1:
            raise ValueError(
                f"Miro Tips target technical anchor differs from reference endpoint {source_connector.get('id')}"
            )
        anchor = anchor_matches[0]
        anchor_id = str(anchor["id"])
        expected = _control_connector_payload(
            source_connector, target_start, anchor_id, manifest
        )
        connector_matches = [
            connector for connector in target_connectors
            if str(connector.get("id") or "") not in used_connectors
            and _endpoint_ids(connector) == (target_start, anchor_id)
        ]
        if len(connector_matches) != 1 or not visual.redline.same_connector(
            connector_matches[0], expected
        ):
            raise ValueError(
                f"Miro Tips target connector differs from reference-routed endpoint {source_connector.get('id')}"
            )
        used_anchors.add(anchor_id)
        used_connectors.add(str(connector_matches[0]["id"]))

    return {
        # Backward-compatible mechanical fields retained while the workflow is
        # migrated away from the historical visual_equivalence label.
        "policy": REFERENCE_STRUCTURE_POLICY,
        "source_item_count": tips.EXPECTED_ITEM_COUNT,
        "target_item_count": tips.EXPECTED_ITEM_COUNT,
        "item_type_counts": dict(tips.EXPECTED_ITEM_TYPE_COUNTS),
        "source_connector_count": tips.EXPECTED_CONNECTOR_COUNT,
        "target_connector_count": len(used_connectors),
        "connector_contract_count": len(used_connectors),
        "native_item_count": len(native_mapping),
        "source_image_id": str(source_image.get("id") or ""),
        "target_image_id": target_image_id,
        "status": "PASS",
        "reference_structure_policy": REFERENCE_STRUCTURE_POLICY,
        "visual_acceptance_authority": VISUAL_ACCEPTANCE_AUTHORITY,
        "render_fidelity": {
            "status": "PASS",
            "layer_policy": LAYER_POLICY,
            "anchor_policy": ANCHOR_POLICY,
            "endpoint_policy": ENDPOINT_POLICY,
            "technical_anchor_count": len(used_anchors),
            "anchored_connector_count": len(used_connectors),
            "direct_image_connector_count": len(direct_image_connectors),
        },
    }


def reconcile_miro_tips_render_fidelity(
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
    tips.assert_reference_identity(client, source_board, source_frame_id, manifest)
    source_frame = base._get_frame(client, source_board, source_frame_id)
    tips._assert_target_container(
        client, target_board, target_frame_id, source_frame, manifest
    )

    visible_result = _visible_reconcile_without_connectors(
        client,
        source_board,
        source_frame_id,
        target_board,
        target_frame_id,
        manifest,
    )
    existing_anchors = _anchors(client, target_board, target_frame_id)
    layer_repair = {
        "native_created": 0,
        "native_deleted": 0,
        "technical_anchor_deleted": 0,
        "connectors_deleted": 0,
        "performed": False,
    }
    if len(existing_anchors) != EXPECTED_CONTROL_ANCHORS:
        rebuilt = _rebuild_native_above_background(
            client,
            source_board,
            source_frame_id,
            target_board,
            target_frame_id,
        )
        layer_repair.update(rebuilt)
        layer_repair["performed"] = True

    routed = _reconcile_anchors_and_connectors(
        client,
        source_board,
        source_frame_id,
        target_board,
        target_frame_id,
        manifest,
    )
    readback = _structural_readback(
        client,
        source_board,
        source_frame_id,
        target_board,
        target_frame_id,
        manifest,
    )

    item_counts = dict(visible_result.get("items") or {})
    for key in ("created", "updated", "unchanged", "deleted"):
        item_counts.setdefault(key, 0)
    item_counts["created"] += int(layer_repair["native_created"]) + int(
        routed["anchor_items"]["created"]
    )
    item_counts["updated"] += int(routed["anchor_items"]["updated"])
    item_counts["unchanged"] += int(routed["anchor_items"]["unchanged"])
    item_counts["deleted"] += int(layer_repair["native_deleted"]) + int(
        layer_repair["technical_anchor_deleted"]
    ) + int(routed["anchor_items"]["deleted"])

    connector_counts = dict(routed["connectors"])
    connector_counts["deleted"] += int(layer_repair["connectors_deleted"])

    cfg = tips._config(manifest)
    return {
        "mode": tips.MIRO_TIPS_MODE,
        "container_policy": tips.MIRO_TIPS_CONTAINER_POLICY,
        # Deprecated compatibility alias.  New tests/evidence use
        # reference_structure_policy + visual_acceptance_authority.
        "visual_equivalence_policy": tips.MIRO_TIPS_VISUAL_EQUIVALENCE_POLICY,
        "reference_structure_policy": REFERENCE_STRUCTURE_POLICY,
        "visual_acceptance_authority": VISUAL_ACCEPTANCE_AUTHORITY,
        "render_fidelity_policy": {
            "layer": LAYER_POLICY,
            "anchor": ANCHOR_POLICY,
            "endpoint": ENDPOINT_POLICY,
        },
        "reference_source_board_id": cfg["reference_source_board_id"],
        "reference_source_frame_id": cfg["reference_source_frame_id"],
        "reference_source_image_id": cfg["reference_source_image_id"],
        "items": item_counts,
        "connectors": connector_counts,
        "layer_repair": layer_repair,
        "control_anchors": routed,
        "reference_clone": readback,
    }


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    tips.reconcile_miro_tips_children = reconcile_miro_tips_render_fidelity
    _INSTALLED = True


def uninstall() -> None:
    global _INSTALLED
    if not _INSTALLED:
        return
    tips.reconcile_miro_tips_children = _ORIGINAL_RECONCILE_MIRO_TIPS_CHILDREN
    _INSTALLED = False
