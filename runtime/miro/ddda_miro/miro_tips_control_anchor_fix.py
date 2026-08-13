from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import miro_tips_endpoint_wirefix as endpoint
from . import miro_tips_hvr_fix as tips
from . import review_board_recovery as base
from . import review_board_recovery_wirefix as visual

ANCHOR_MARKER_PREFIX = "ddda.hvr2.control-anchor:"
DEFAULT_ANCHOR_SIZE = 8.0

_ORIGINAL_BASE_RECONCILE = tips._ORIGINAL_RECONCILE_COMPANION_CHILDREN
_ORIGINAL_TUTORIAL_STATE = tips._tutorial_state
_ORIGINAL_ASSERT_TUTORIAL_STATE = tips._assert_tutorial_state
_ORIGINAL_RECONCILE_MIRO_TIPS = tips.reconcile_miro_tips_children
_ORIGINAL_ENDPOINT_CONTRACT_READBACK = tips._endpoint_contract_readback
_INSTALLED = False


def _anchor_size(manifest: dict[str, Any]) -> float:
    raw = (manifest.get("miro_tips") or {}).get("control_anchor_size")
    size = float(raw if raw is not None else DEFAULT_ANCHOR_SIZE)
    if not 4.0 <= size <= 24.0:
        raise ValueError("Miro Tips control-anchor size must be between 4 and 24")
    return size


def _is_miro_tips_source(source_frame_id: str, manifest: dict[str, Any]) -> bool:
    return str(source_frame_id) == str(tips._source_spec(manifest)["id"])


def _marker(source_connector_id: str) -> str:
    return f"{ANCHOR_MARKER_PREFIX}{source_connector_id}"


def _visible(item: dict[str, Any]) -> str:
    return base._visible((item.get("data") or {}).get("content")).strip()


def _is_control_anchor(item: dict[str, Any]) -> bool:
    return (
        str(item.get("type") or "") == "shape"
        and _visible(item).startswith(ANCHOR_MARKER_PREFIX)
    )


def _anchor_payload(
    target_frame_id: str,
    marker: str,
    x: float,
    y: float,
    size: float,
) -> dict[str, Any]:
    return {
        "data": {"shape": "circle", "content": f"<p>{marker}</p>"},
        "parent": {"id": target_frame_id},
        "position": {"x": float(x), "y": float(y), "origin": "center"},
        "geometry": {"width": float(size), "height": float(size)},
        "style": {
            "fillColor": "#ffffff",
            "fillOpacity": 0.0,
            "borderColor": "#ffffff",
            "borderOpacity": 0.0,
            "borderWidth": 1.0,
            "color": "#ffffff",
            "fontSize": 8,
        },
    }


def _close(left: Any, right: Any, tolerance: float = 1.0) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return False


def _target_frame_geometry(client: Any, board: str, frame_id: str) -> dict[str, float]:
    getter = getattr(client, "_frame_geometry", None)
    if not callable(getter):
        raise ValueError("Miro Tips control-anchor reconciliation requires parent frame geometry")
    raw = dict(getter(board, frame_id) or {})
    if "width" not in raw or "height" not in raw:
        raise ValueError("Miro Tips parent frame geometry requires width and height")
    width, height = float(raw["width"]), float(raw["height"])
    if width <= 0 or height <= 0:
        raise ValueError("Miro Tips parent frame geometry must be positive")
    return {"width": width, "height": height}


def _same_anchor(
    remote: dict[str, Any],
    expected: dict[str, Any],
    frame_geometry: dict[str, float],
) -> bool:
    if not _is_control_anchor(remote):
        return False
    if _visible(remote) != _visible(expected):
        return False
    if str((remote.get("parent") or {}).get("id") or "") != str(
        (expected.get("parent") or {}).get("id") or ""
    ):
        return False
    remote_pos, expected_pos = remote.get("position") or {}, expected.get("position") or {}
    remote_geo, expected_geo = remote.get("geometry") or {}, expected.get("geometry") or {}
    expected_remote_x = float(frame_geometry["width"]) / 2.0 + float(expected_pos.get("x") or 0.0)
    expected_remote_y = float(frame_geometry["height"]) / 2.0 + float(expected_pos.get("y") or 0.0)
    return (
        _close(remote_pos.get("x"), expected_remote_x)
        and _close(remote_pos.get("y"), expected_remote_y)
        and _close(remote_geo.get("width"), expected_geo.get("width"), 0.5)
        and _close(remote_geo.get("height"), expected_geo.get("height"), 0.5)
    )


def _normalized_endpoint_value(raw: Any) -> float:
    """Accept Miro endpoint coordinates as normalized numbers or percentage strings."""
    if isinstance(raw, str):
        text = raw.strip()
        if text.endswith("%"):
            return float(text[:-1].strip()) / 100.0
    return float(raw)


def _normalized_control_position(
    source_connector: dict[str, Any],
    target_image: dict[str, Any],
    target_frame_geometry: dict[str, float],
) -> tuple[float, float]:
    """Map a reference image endpoint into DDDA frame-center child coordinates.

    Miro read-back exposes child/image positions in parent-top-left coordinates,
    while MiroClient.create_item/update_item accept DDDA frame-center coordinates
    and convert them at the API boundary. Calculate the UI control point in the
    read-back coordinate system first, then translate it back to DDDA coordinates.
    """
    position = (source_connector.get("endItem") or {}).get("position")
    if not isinstance(position, dict):
        raise ValueError(
            f"Miro Tips source connector {source_connector.get('id')} has no authored end position"
        )
    px = _normalized_endpoint_value(position["x"])
    py = _normalized_endpoint_value(position["y"])
    if not (0.0 <= px <= 1.0 and 0.0 <= py <= 1.0):
        raise ValueError(
            f"Miro Tips source connector {source_connector.get('id')} endpoint is outside normalized image bounds"
        )
    image_position = target_image.get("position") or {}
    image_geometry = target_image.get("geometry") or {}
    width, height = float(image_geometry["width"]), float(image_geometry["height"])
    parent_x = float(image_position["x"]) - width / 2.0 + px * width
    parent_y = float(image_position["y"]) - height / 2.0 + py * height
    return (
        parent_x - float(target_frame_geometry["width"]) / 2.0,
        parent_y - float(target_frame_geometry["height"]) / 2.0,
    )


def _target_native(
    source: dict[str, Any],
    target_items: list[dict[str, Any]],
) -> dict[str, Any]:
    source_text = visual.redline.canonical_miro_text((source.get("data") or {}).get("content"))
    hits = [
        item
        for item in target_items
        if not _is_control_anchor(item)
        and str(item.get("type") or "") == str(source.get("type") or "")
        and visual.redline.canonical_miro_text((item.get("data") or {}).get("content"))
        == source_text
    ]
    if len(hits) != 1:
        raise ValueError(
            f"Miro Tips target mapping for source item {source.get('id')} expected one semantic match, got {len(hits)}"
        )
    return hits[0]


def _target_image(
    source_image: dict[str, Any],
    target_items: list[dict[str, Any]],
    target_frame_id: str,
) -> dict[str, Any]:
    hits = [
        item
        for item in target_items
        if visual._same_image(item, source_image, target_frame_id)
    ]
    if len(hits) != 1:
        raise ValueError(
            f"Miro Tips target image mapping for source {source_image.get('id')} expected one match, got {len(hits)}"
        )
    return hits[0]


def _black_captionless(connector: dict[str, Any]) -> bool:
    style = connector.get("style") or {}
    stroke = str(style.get("strokeColor") or "").casefold()
    return stroke in {"#000", "#000000"} and not (connector.get("captions") or [])


def _control_connector_payload(
    source: dict[str, Any],
    target_start_id: str,
    target_anchor_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    payload = endpoint._ORIGINAL_READABLE_CONNECTOR_PAYLOAD(
        source, target_start_id, target_anchor_id, manifest
    )
    end_item = dict(payload.get("endItem") or {})
    end_item["id"] = target_anchor_id
    end_item.pop("position", None)
    end_item.pop("snapTo", None)
    payload["endItem"] = end_item
    return payload


def _reconcile_control_anchors_and_connectors(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    source_items = base._children(client, source_board, source_frame_id)
    target_items = base._children(client, target_board, target_frame_id)
    source_ids = {str(item["id"]) for item in source_items}
    source_connectors = [
        connector
        for connector in visual._companion_source_connectors(client, source_board, source_ids)
        if _black_captionless(connector)
    ]
    expected_count = int((manifest.get("miro_tips") or {}).get("min_connectors") or 8)
    if len(source_connectors) != expected_count:
        raise ValueError(
            f"Miro Tips expected {expected_count} black captionless source callouts, got {len(source_connectors)}"
        )
    source_images = [item for item in source_items if str(item.get("type") or "") == "image"]
    if len(source_images) != 1:
        raise ValueError(f"Miro Tips control anchors require exactly one reference image, got {len(source_images)}")
    target_image = _target_image(source_images[0], target_items, target_frame_id)
    frame_geometry = _target_frame_geometry(client, target_board, target_frame_id)

    size = _anchor_size(manifest)
    anchor_counts = {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0}
    connector_counts = {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0}
    target_anchors = [item for item in target_items if _is_control_anchor(item)]
    used_anchor_ids: set[str] = set()
    desired: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []

    for source_connector in sorted(source_connectors, key=lambda item: str(item.get("id") or "")):
        source_start_id = str((source_connector.get("startItem") or {}).get("id") or "")
        source_start = next(
            (item for item in source_items if str(item.get("id") or "") == source_start_id),
            None,
        )
        if source_start is None:
            raise ValueError(f"Miro Tips source connector {source_connector.get('id')} start item is missing")
        target_start = _target_native(source_start, target_items)
        x, y = _normalized_control_position(source_connector, target_image, frame_geometry)
        marker = _marker(str(source_connector["id"]))
        payload = _anchor_payload(target_frame_id, marker, x, y, size)
        hits = [
            item
            for item in target_anchors
            if str(item.get("id") or "") not in used_anchor_ids and _visible(item) == marker
        ]
        if len(hits) > 1:
            raise ValueError(f"Miro Tips duplicate control anchors for {source_connector['id']}")
        if not hits:
            anchor = client.create_item(target_board, "shape", payload)
            target_anchors.append(anchor)
            target_items.append(anchor)
            anchor_counts["created"] += 1
        else:
            anchor = hits[0]
            if _same_anchor(anchor, payload, frame_geometry):
                anchor_counts["unchanged"] += 1
            else:
                anchor = client.update_item(target_board, "shape", str(anchor["id"]), payload)
                if not _same_anchor(anchor, payload, frame_geometry):
                    raise ValueError(f"Miro Tips control anchor {anchor.get('id')} read-back mismatch")
                anchor_counts["updated"] += 1
        used_anchor_ids.add(str(anchor["id"]))
        desired.append((source_connector, target_start, anchor))

    all_connectors = client.list_connectors(target_board)
    desired_connector_ids: set[str] = set()
    mapped_start_ids = {str(target_start["id"]) for _, target_start, _ in desired}
    anchor_ids = {str(anchor["id"]) for _, _, anchor in desired}
    image_id = str(target_image["id"])

    for source_connector, target_start, anchor in desired:
        start_id, anchor_id = str(target_start["id"]), str(anchor["id"])
        payload = _control_connector_payload(source_connector, start_id, anchor_id, manifest)
        hits = [
            connector
            for connector in all_connectors
            if str((connector.get("startItem") or {}).get("id") or "") == start_id
            and str((connector.get("endItem") or {}).get("id") or "") == anchor_id
            and _black_captionless(connector)
        ]
        if len(hits) > 1:
            raise ValueError(f"Miro Tips duplicate control-anchor connectors for {source_connector['id']}")
        if not hits:
            remote = client.create_connector(target_board, payload)
            all_connectors.append(remote)
            connector_counts["created"] += 1
        elif visual.redline.same_connector(hits[0], payload):
            remote = hits[0]
            connector_counts["unchanged"] += 1
        else:
            remote = client.update_connector(target_board, str(hits[0]["id"]), payload)
            if not visual.redline.same_connector(remote, payload):
                raise ValueError(f"Miro Tips control connector {remote.get('id')} read-back mismatch")
            connector_counts["updated"] += 1
        desired_connector_ids.add(str(remote["id"]))

    stale_connectors = [
        connector
        for connector in all_connectors
        if str(connector.get("id") or "") not in desired_connector_ids
        and _black_captionless(connector)
        and (
            str((connector.get("startItem") or {}).get("id") or "") in mapped_start_ids
            or str((connector.get("endItem") or {}).get("id") or "") == image_id
            or str((connector.get("endItem") or {}).get("id") or "") in anchor_ids
        )
    ]
    for connector in stale_connectors:
        client.delete_connector(target_board, str(connector["id"]))
        connector_counts["deleted"] += 1

    stale_anchors = [
        anchor
        for anchor in target_anchors
        if str(anchor.get("id") or "") not in used_anchor_ids
    ]
    for anchor in stale_anchors:
        client.delete_item(target_board, str(anchor["id"]))
        anchor_counts["deleted"] += 1

    return {
        "anchor_items": anchor_counts,
        "connectors": connector_counts,
        "source_connector_count": len(source_connectors),
        "control_anchor_count": len(desired),
        "control_anchor_connector_count": len(desired_connector_ids),
    }


def reconcile_children_with_control_anchors(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    min_images: int,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    if not _is_miro_tips_source(source_frame_id, manifest):
        return _ORIGINAL_BASE_RECONCILE(
            client,
            source_board,
            source_frame_id,
            target_board,
            target_frame_id,
            min_images,
            manifest,
        )

    original_children = base._children
    original_connectors = visual._companion_source_connectors

    def children_without_control_anchors(c: Any, board: str, frame_id: str) -> list[dict[str, Any]]:
        items = original_children(c, board, frame_id)
        if str(board) == str(target_board) and str(frame_id) == str(target_frame_id):
            return [item for item in items if not _is_control_anchor(item)]
        return items

    base._children = children_without_control_anchors
    visual._companion_source_connectors = lambda *_args, **_kwargs: []
    try:
        base_result = _ORIGINAL_BASE_RECONCILE(
            client,
            source_board,
            source_frame_id,
            target_board,
            target_frame_id,
            min_images,
            manifest,
        )
    finally:
        visual._companion_source_connectors = original_connectors
        base._children = original_children

    anchored = _reconcile_control_anchors_and_connectors(
        client,
        source_board,
        source_frame_id,
        target_board,
        target_frame_id,
        manifest,
    )
    item_counts = dict(base_result["items"])
    for key in ("created", "updated", "unchanged", "deleted"):
        item_counts[key] = int(item_counts.get(key) or 0) + int(anchored["anchor_items"][key])
    base_result["items"] = item_counts
    base_result["connectors"] = anchored["connectors"]
    base_result["source_connector_count"] = anchored["source_connector_count"]
    base_result["target_control_anchor_count"] = anchored["control_anchor_count"]
    base_result["target_control_anchor_connector_count"] = anchored["control_anchor_connector_count"]
    return base_result


def tutorial_state_with_control_anchors(
    client: Any,
    board: str,
    frame_id: str,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    items = base._children(client, board, frame_id)
    images = [item for item in items if str(item.get("type") or "") == "image"]
    anchors = [item for item in items if _is_control_anchor(item)]
    ids = {str(item["id"]) for item in items}
    connectors = visual._companion_source_connectors(client, board, ids)
    text = " ".join(
        base._visible((item.get("data") or {}).get("content")).casefold()
        for item in items
        if not _is_control_anchor(item)
    )
    missing = [marker for marker in cfg["required_markers"] if marker not in text]
    image_ids = {str(item["id"]) for item in images}
    anchor_ids = {str(item["id"]) for item in anchors}
    image_anchor_count = tips._image_anchor_connector_count(connectors, image_ids)
    control_connector_count = sum(
        1
        for connector in connectors
        if str((connector.get("endItem") or {}).get("id") or "") in anchor_ids
        and _black_captionless(connector)
    )
    return {
        "items": items,
        "images": images,
        "connectors": connectors,
        "missing_markers": missing,
        "image_anchor_connector_count": image_anchor_count,
        "control_anchors": anchors,
        "control_anchor_count": len(anchors),
        "control_anchor_connector_count": control_connector_count,
    }


def assert_tutorial_state_with_control_anchors(
    state: dict[str, Any],
    cfg: dict[str, Any],
    label: str,
) -> None:
    if len(state["images"]) < cfg["min_images"]:
        raise ValueError(f"{label} is missing the Miro UI tutorial image")
    if len(state["connectors"]) < cfg["min_connectors"]:
        raise ValueError(f"{label} is missing callout connectors")
    anchored = max(
        int(state.get("image_anchor_connector_count") or 0),
        int(state.get("control_anchor_connector_count") or 0),
    )
    if anchored < cfg["min_connectors"]:
        raise ValueError(f"{label} callouts are not anchored to concrete Miro UI controls")
    if state.get("control_anchors") and int(state.get("control_anchor_count") or 0) < cfg["min_connectors"]:
        raise ValueError(f"{label} has incomplete explicit control-anchor coverage")
    if state["missing_markers"]:
        raise ValueError(f"{label} is missing required tutorial markers: {state['missing_markers']}")


def endpoint_contract_readback_with_control_anchors(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Read back the rendered control topology instead of a generic image endpoint.

    Miro can route a connector attached directly to an image differently from the
    reference even when the REST endpoint percentages compare equal.  An 8px
    transparent child anchor fixes the arrowhead at the intended UI control.
    This read-back proves the source control coordinate, target anchor geometry
    and connector attachment together for every black tutorial callout.
    """
    tips.assert_reference_identity(client, source_board, source_frame_id, manifest)
    cfg = tips._config(manifest)
    source_items = base._children(client, source_board, source_frame_id)
    target_items = base._children(client, target_board, target_frame_id)
    source_ids = {str(item["id"]) for item in source_items}
    source_connectors = sorted(
        [
            connector
            for connector in visual._companion_source_connectors(client, source_board, source_ids)
            if _black_captionless(connector)
        ],
        key=lambda item: str(item.get("id") or ""),
    )
    if len(source_connectors) != cfg["min_connectors"]:
        raise ValueError("Miro Tips control-anchor read-back has an incomplete source callout set")
    source_images = [item for item in source_items if str(item.get("type") or "") == "image"]
    if len(source_images) != 1:
        raise ValueError("Miro Tips control-anchor read-back requires exactly one source screenshot")
    target_image = _target_image(source_images[0], target_items, target_frame_id)
    target_anchors = [item for item in target_items if _is_control_anchor(item)]
    frame_geometry = _target_frame_geometry(client, target_board, target_frame_id)
    target_connectors = client.list_connectors(target_board)
    entries: list[dict[str, Any]] = []

    for source_connector in source_connectors:
        source_start_id = str((source_connector.get("startItem") or {}).get("id") or "")
        source_start = next(
            (item for item in source_items if str(item.get("id") or "") == source_start_id),
            None,
        )
        if source_start is None:
            raise ValueError(f"Miro Tips source callout {source_connector.get('id')} has no source text region")
        if str((source_connector.get("endItem") or {}).get("id") or "") != str(source_images[0]["id"]):
            raise ValueError(f"Miro Tips source callout {source_connector.get('id')} does not target the reference UI")
        target_start = _target_native(source_start, target_items)
        marker = _marker(str(source_connector["id"]))
        anchors = [anchor for anchor in target_anchors if _visible(anchor) == marker]
        if len(anchors) != 1:
            raise ValueError(f"Miro Tips requires exactly one target control anchor for {source_connector.get('id')}")
        anchor = anchors[0]
        x, y = _normalized_control_position(source_connector, target_image, frame_geometry)
        expected_anchor = _anchor_payload(
            target_frame_id, marker, x, y, _anchor_size(manifest)
        )
        anchor_passed = _same_anchor(anchor, expected_anchor, frame_geometry)
        expected_connector = _control_connector_payload(
            source_connector, str(target_start["id"]), str(anchor["id"]), manifest
        )
        candidates = [
            connector
            for connector in target_connectors
            if _black_captionless(connector)
            and str((connector.get("startItem") or {}).get("id") or "") == str(target_start["id"])
            and str((connector.get("endItem") or {}).get("id") or "") == str(anchor["id"])
        ]
        if len(candidates) != 1:
            raise ValueError(f"Miro Tips requires exactly one control-anchor connector for {source_connector.get('id')}")
        target_connector = candidates[0]
        connector_passed = visual.redline.same_connector(target_connector, expected_connector)
        entry = {
            "source_connector_id": str(source_connector.get("id") or ""),
            "source_text_item_id": source_start_id,
            "reference_ui_position": dict((source_connector.get("endItem") or {}).get("position") or {}),
            "target_anchor_id": str(anchor.get("id") or ""),
            "target_anchor_marker": marker,
            "target_anchor_position": dict(anchor.get("position") or {}),
            "target_connector_id": str(target_connector.get("id") or ""),
            "anchor_passed": bool(anchor_passed),
            "connector_passed": bool(connector_passed),
            "passed": bool(anchor_passed and connector_passed),
        }
        entries.append(entry)
        if not entry["passed"]:
            raise ValueError(f"Miro Tips control-anchor read-back did not converge for {source_connector.get('id')}")

    anchor_ids = {str(anchor.get("id") or "") for anchor in target_anchors}
    target_image_id = str(target_image.get("id") or "")
    anchored_callouts = [
        connector
        for connector in target_connectors
        if _black_captionless(connector)
        and str((connector.get("endItem") or {}).get("id") or "") in anchor_ids
    ]
    direct_image_callouts = [
        connector
        for connector in target_connectors
        if _black_captionless(connector)
        and str((connector.get("endItem") or {}).get("id") or "") == target_image_id
    ]
    if len(target_anchors) != cfg["min_connectors"]:
        raise ValueError("Miro Tips target has missing or duplicate control anchors")
    if len(anchored_callouts) != cfg["min_connectors"]:
        raise ValueError("Miro Tips target has missing or duplicate control-anchor callouts")
    if direct_image_callouts:
        raise ValueError("Miro Tips target still contains callouts attached directly to the screenshot")
    return {
        "policy": "explicit_transparent_control_anchor_readback",
        "reference_source_board_id": cfg["reference_source_board_id"],
        "reference_source_frame_id": cfg["reference_source_frame_id"],
        "reference_source_image_id": cfg["reference_source_image_id"],
        "count": len(entries),
        "passed_count": sum(1 for entry in entries if entry["passed"]),
        "target_control_anchor_count": len(target_anchors),
        "target_control_anchor_connector_count": len(anchored_callouts),
        "target_direct_image_callout_count": len(direct_image_callouts),
        "entries": entries,
    }


def reconcile_miro_tips_with_control_anchor_evidence(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    result = _ORIGINAL_RECONCILE_MIRO_TIPS(
        client,
        source_board,
        source_frame_id,
        target_board,
        target_frame_id,
        manifest,
    )
    cfg = tips._config(manifest)
    target_state = tutorial_state_with_control_anchors(
        client, target_board, str(result["replacement_frame_id"]), cfg
    )
    if target_state["control_anchor_count"] < cfg["min_connectors"]:
        raise ValueError("Miro Tips target does not contain the required explicit control anchors")
    if target_state["control_anchor_connector_count"] < cfg["min_connectors"]:
        raise ValueError("Miro Tips target connectors do not terminate on explicit control anchors")
    if target_state["image_anchor_connector_count"] != 0:
        raise ValueError("Miro Tips target still contains tutorial connectors terminating on the screenshot image")
    result["target_control_anchor_count"] = target_state["control_anchor_count"]
    result["target_control_anchor_connector_count"] = target_state["control_anchor_connector_count"]
    result["target_raw_image_anchor_connector_count"] = target_state["image_anchor_connector_count"]
    result["control_anchor_policy"] = "explicit_transparent_child_anchor_per_reference_ui_control"
    return result


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    tips._ORIGINAL_RECONCILE_COMPANION_CHILDREN = reconcile_children_with_control_anchors
    tips._tutorial_state = tutorial_state_with_control_anchors
    tips._assert_tutorial_state = assert_tutorial_state_with_control_anchors
    tips._endpoint_contract_readback = endpoint_contract_readback_with_control_anchors
    tips.reconcile_miro_tips_children = reconcile_miro_tips_with_control_anchor_evidence
    _INSTALLED = True


def uninstall() -> None:
    global _INSTALLED
    if not _INSTALLED:
        return
    tips._ORIGINAL_RECONCILE_COMPANION_CHILDREN = _ORIGINAL_BASE_RECONCILE
    tips._tutorial_state = _ORIGINAL_TUTORIAL_STATE
    tips._assert_tutorial_state = _ORIGINAL_ASSERT_TUTORIAL_STATE
    tips._endpoint_contract_readback = _ORIGINAL_ENDPOINT_CONTRACT_READBACK
    tips.reconcile_miro_tips_children = _ORIGINAL_RECONCILE_MIRO_TIPS
    _INSTALLED = False
