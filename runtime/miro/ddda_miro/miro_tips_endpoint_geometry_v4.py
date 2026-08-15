from __future__ import annotations

"""Fail-closed endpoint/render geometry adapter for PR8 Miro Tips."""

from collections import Counter
from copy import deepcopy
from typing import Any

from . import miro_tips_full_arrow_fidelity_fix as full
from . import miro_tips_hvr_fix as tips
from . import miro_tips_render_fidelity_fix as fidelity
from . import review_board_recovery as base
from . import review_board_recovery_wirefix as visual

EXPECTED_REFERENCE_CONNECTORS = 11
EXPECTED_DIRECT_IMAGE_CONNECTORS = 8
EXPECTED_TEXT_CONNECTORS = 3
EXPECTED_COMPATIBILITY_ANCHORS = 6
ROUTING_PROXY_POLICY = "no_shared_routing_proxy_v4"
ENDPOINT_POLICY = "direct_reference_attachment_or_per_endpoint_control_anchor_v4"
REFERENCE_STRUCTURE_POLICY = "exact_reference_children_plus_endpoint_geometry_v4"
VISUAL_ACCEPTANCE_AUTHORITY = "human_review_only"
ENDPOINT_GEOMETRY_TOLERANCE = 2.0
NORMALIZED_ENDPOINT_TOLERANCE = 0.001

_ORIGINALS: dict[str, Any] = {}
_INSTALLED = False


def _unit(value: Any) -> float:
    if isinstance(value, str) and value.strip().endswith("%"):
        return float(value.strip()[:-1]) / 100.0
    value = float(value)
    return value / 100.0 if 1.0 < value <= 100.0 else value


def _endpoint_ids(row: dict[str, Any]) -> tuple[str, str]:
    return (
        str((row.get("startItem") or {}).get("id") or ""),
        str((row.get("endItem") or {}).get("id") or ""),
    )


def _expected_rest_connector_ids(manifest: dict[str, Any]) -> set[str]:
    values = [str(v) for v in (manifest.get("miro_tips") or {}).get("expected_rest_connector_ids", [])]
    if len(values) != 8 or len(set(values)) != 8:
        raise ValueError("Miro Tips endpoint contract must freeze exactly eight unique REST connector ids")
    return set(values)


def validate_rest_connector_identity(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    expected = _expected_rest_connector_ids(manifest)
    actual = {str(row.get("id") or "") for row in rows}
    if actual != expected:
        raise ValueError(f"Miro Tips REST connector identity drift: expected={sorted(expected)}, actual={sorted(actual)}")


def is_control_artifact(item: dict[str, Any], frame_id: str | None = None) -> bool:
    """Only canonical transparent endpoint circles count; never the v3 full-image proxy."""
    return bool(full._ORIGINAL_IS_CONTROL_ANCHOR(item, frame_id))


def _legacy_anchors(client: Any, board: str, frame_id: str) -> list[dict[str, Any]]:
    return [item for item in base._children(client, board, frame_id) if is_control_artifact(item, frame_id)]


def _routing_proxies(client: Any, board: str, frame_id: str) -> list[dict[str, Any]]:
    return [item for item in base._children(client, board, frame_id) if full.is_routing_proxy(item, frame_id)]


def controls_ready(client: Any, board: str, frame_id: str, target_image: dict[str, Any], expected: list[tuple[float, float]]) -> bool:
    _ = target_image
    if _routing_proxies(client, board, frame_id) or len(expected) != EXPECTED_COMPATIBILITY_ANCHORS:
        return False
    anchors = _legacy_anchors(client, board, frame_id)
    if len(anchors) != EXPECTED_COMPATIBILITY_ANCHORS:
        return False
    used: set[str] = set()
    for x, y in expected:
        matches = [a for a in anchors if str(a.get("id") or "") not in used and fidelity._same_anchor(a, frame_id, x, y)]
        if len(matches) != 1:
            return False
        used.add(str(matches[0].get("id") or ""))
    return True


def rebuild_controls_below_native(client: Any, source_board: str, source_frame_id: str, target_board: str, target_frame_id: str, target_image: dict[str, Any], expected: list[tuple[float, float]]) -> dict[str, int]:
    """Reuse the proven v3 layer rebuild, then remove its now-forbidden proxy."""
    old_control = full.is_control_artifact
    old_count = full.EXPECTED_COMPATIBILITY_ANCHORS
    try:
        full.is_control_artifact = _ORIGINALS.get("is_control_artifact", old_control)
        full.EXPECTED_COMPATIBILITY_ANCHORS = EXPECTED_COMPATIBILITY_ANCHORS
        result = _ORIGINALS["_rebuild_controls_below_native"](
            client, source_board, source_frame_id, target_board, target_frame_id, target_image, expected
        )
    finally:
        full.is_control_artifact = is_control_artifact
        full.EXPECTED_COMPATIBILITY_ANCHORS = EXPECTED_COMPATIBILITY_ANCHORS
    proxies = _routing_proxies(client, target_board, target_frame_id)
    if len(proxies) != 1:
        raise ValueError(f"Miro Tips layer repair expected one transient routing proxy, got {len(proxies)}")
    client.delete_item(target_board, str(proxies[0]["id"]))
    result["control_created"] = EXPECTED_COMPATIBILITY_ANCHORS
    result["control_deleted"] = int(result.get("control_deleted", 0)) + 1
    return result


def target_image_not_proxy(client: Any, board: str, frame_id: str, image: dict[str, Any]) -> dict[str, Any]:
    proxies = _routing_proxies(client, board, frame_id)
    if proxies:
        raise ValueError(f"Miro Tips shared routing proxy fallback is forbidden; found {len(proxies)}")
    return image


def free_endpoint_forbidden(endpoint: dict[str, Any], *_args: Any, **_kwargs: Any) -> dict[str, Any]:
    raise ValueError(f"Miro Tips generic/free endpoint fallback is forbidden by endpoint-geometry v4: {endpoint}")


def _point_on_item(endpoint: dict[str, Any], item: dict[str, Any]) -> tuple[float, float]:
    pos, geom = item.get("position") or {}, item.get("geometry") or {}
    cx, cy = float(pos["x"]), float(pos["y"])
    width, height = float(geom.get("width") or 0), float(geom.get("height") or 0)
    ep = endpoint.get("position")
    if isinstance(ep, dict) and "x" in ep and "y" in ep:
        if width <= 0 or height <= 0:
            raise ValueError(f"connector endpoint item {item.get('id')} has incomplete geometry")
        px, py = _unit(ep["x"]), _unit(ep["y"])
        return cx - width / 2 + px * width, cy - height / 2 + py * height
    snap = str(endpoint.get("snapTo") or "").casefold()
    if snap and width > 0 and height > 0:
        return {
            "left": (cx - width / 2, cy), "right": (cx + width / 2, cy),
            "top": (cx, cy - height / 2), "bottom": (cx, cy + height / 2),
        }.get(snap, (cx, cy))
    return cx, cy


def _has_explicit(endpoint: dict[str, Any]) -> bool:
    p = endpoint.get("position")
    return (isinstance(p, dict) and "x" in p and "y" in p) or endpoint.get("snapTo") is not None


def _endpoint_geometry_row(expected: dict[str, Any], actual: dict[str, Any], items: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
    expected_id, actual_id = str(expected.get("id") or ""), str(actual.get("id") or "")
    if expected_id != actual_id or expected_id not in items:
        raise ValueError(f"Miro Tips {name} endpoint item mismatch: expected={expected_id}, actual={actual_id}")
    if _has_explicit(expected) and not _has_explicit(actual):
        raise ValueError(f"Miro Tips {name} silently fell back to auto-anchor for {expected_id}")
    if not _has_explicit(expected) and _has_explicit(actual):
        raise ValueError(f"Miro Tips {name} attachment semantics drifted from reference auto-anchor for {expected_id}")
    if not _has_explicit(expected):
        return {"endpoint": name, "item_id": expected_id, "contract_mode": "reference_auto_attachment", "status": "PASS"}
    ep, ap = _point_on_item(expected, items[expected_id]), _point_on_item(actual, items[actual_id])
    delta = max(abs(ap[0] - ep[0]), abs(ap[1] - ep[1]))
    if delta > ENDPOINT_GEOMETRY_TOLERANCE:
        raise ValueError(f"Miro Tips {name} endpoint geometry drift exceeds tolerance: delta={delta:.6f}, tolerance={ENDPOINT_GEOMETRY_TOLERANCE}")
    return {"endpoint": name, "item_id": expected_id, "contract_mode": "explicit_reference_geometry", "expected": {"x": ep[0], "y": ep[1]}, "actual": {"x": ap[0], "y": ap[1]}, "max_axis_delta": delta, "tolerance": ENDPOINT_GEOMETRY_TOLERANCE, "status": "PASS"}

endpoint_geometry_row = _endpoint_geometry_row


def _absolute_reference_point(normalized: tuple[float, float], image: dict[str, Any]) -> tuple[float, float]:
    pos, geom = image.get("position") or {}, image.get("geometry") or {}
    w, h = float(geom.get("width") or 0), float(geom.get("height") or 0)
    if w <= 0 or h <= 0:
        raise ValueError("Miro Tips screenshot geometry is incomplete")
    return float(pos["x"]) - w / 2 + normalized[0] * w, float(pos["y"]) - h / 2 + normalized[1] * h


def _legacy_visual_endpoint_evidence(source: dict[str, Any], actual: dict[str, Any], items: dict[str, dict[str, Any]], image: dict[str, Any]) -> dict[str, Any] | None:
    spec = source.get("_ddda_legacy_visual_arrow")
    if not isinstance(spec, dict):
        return None
    start, end = actual.get("startItem") or {}, actual.get("endItem") or {}
    if not _has_explicit(start) or not _has_explicit(end):
        raise ValueError(f"Miro Tips legacy arrow {spec.get('key')} silently fell back to auto-anchor")
    def check(label: str, endpoint: dict[str, Any], wanted: tuple[float, float]) -> dict[str, Any]:
        item_id = str(endpoint.get("id") or "")
        if item_id not in items:
            raise ValueError(f"Miro Tips legacy arrow {spec.get('key')} endpoint control is missing")
        rendered = _point_on_item(endpoint, items[item_id])
        expected = _absolute_reference_point(wanted, image)
        delta = max(abs(rendered[0]-expected[0]), abs(rendered[1]-expected[1]))
        if delta > ENDPOINT_GEOMETRY_TOLERANCE:
            raise ValueError(f"Miro Tips legacy {label} rendered endpoint drift exceeds tolerance: delta={delta:.6f}")
        return {"expected": {"x": expected[0], "y": expected[1]}, "actual": {"x": rendered[0], "y": rendered[1]}, "max_axis_delta": delta, "status": "PASS"}
    return {"key": str(spec.get("key") or ""), "provenance": "frozen_approved_reference_screenshot", "start": check("start", start, tuple(spec["start"])), "end": check("end", end, tuple(spec["end"])), "status": "PASS"}

legacy_visual_endpoint_evidence = _legacy_visual_endpoint_evidence


def connector_geometry_evidence(reference_id: str, expected: dict[str, Any], actual: dict[str, Any], items: dict[str, dict[str, Any]], image: dict[str, Any] | None = None) -> dict[str, Any]:
    legacy = _legacy_visual_endpoint_evidence(expected, actual, items, image) if image is not None else None
    return {"reference_connector_id": reference_id, "target_connector_id": str(actual.get("id") or ""), "direction": {"start_id": _endpoint_ids(actual)[0], "end_id": _endpoint_ids(actual)[1]}, "shape": actual.get("shape"), "start": _endpoint_geometry_row(expected.get("startItem") or {}, actual.get("startItem") or {}, items, "start"), "end": _endpoint_geometry_row(expected.get("endItem") or {}, actual.get("endItem") or {}, items, "end"), "legacy_visual_geometry": legacy, "status": "PASS"}


def connector_contract_evidence(connectors: list[dict[str, Any]], image_id: str) -> dict[str, Any]:
    rows = []
    for c in connectors:
        start_id, end_id = _endpoint_ids(c)
        spec = c.get("_ddda_legacy_visual_arrow")
        role = "legacy_free_form_line" if isinstance(spec, dict) else ("direct_image_attachment" if image_id and end_id == image_id else "native_item_attachment")
        rows.append({"reference_connector_id": str(c.get("id") or ""), "role": role, "direction": {"start_id": start_id, "end_id": end_id}, "start": deepcopy(c.get("startItem") or {}), "end": deepcopy(c.get("endItem") or {}), "shape": c.get("shape"), "style": deepcopy(c.get("style") or {}), "legacy_visual_geometry": deepcopy(spec) if isinstance(spec, dict) else None})
    if len(rows) != EXPECTED_REFERENCE_CONNECTORS or len({r["reference_connector_id"] for r in rows}) != EXPECTED_REFERENCE_CONNECTORS:
        raise ValueError(f"Miro Tips endpoint contract has {len(rows)} rows; expected 11 unique connectors")
    return {"count": len(rows), "connectors": rows}


def structural_readback(client: Any, source_inventory: dict[str, Any], source_board: str, source_frame_id: str, target_board: str, target_frame_id: str, source_image: dict[str, Any], target_image: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    cfg = tips._config(manifest)
    children = list(base._children(client, target_board, target_frame_id))
    if _routing_proxies(client, target_board, target_frame_id):
        raise ValueError("Miro Tips shared routing proxy fallback is forbidden")
    visible = [i for i in children if not is_control_artifact(i, target_frame_id)]
    counts = Counter(str(i.get("type") or "") for i in visible)
    if len(visible) != tips.EXPECTED_ITEM_COUNT or dict(counts) != tips.EXPECTED_ITEM_TYPE_COUNTS:
        raise ValueError(f"Miro Tips visible target topology mismatch: {dict(counts)}")
    text = " ".join(base._visible((i.get("data") or {}).get("content")).casefold() for i in visible)
    missing = [m for m in cfg["required_markers"] if m not in text]
    if missing:
        raise ValueError(f"Miro Tips target is missing reference markers: {missing}")
    anchors = _legacy_anchors(client, target_board, target_frame_id)
    if len(anchors) != EXPECTED_COMPATIBILITY_ANCHORS:
        raise ValueError(f"Miro Tips requires 6 per-endpoint controls, got {len(anchors)}")
    native_mapping = fidelity._map_native(client, source_board, source_frame_id, target_board, target_frame_id)
    source_items = {str(i.get("id") or ""): i for i in client.list_items(source_board)}
    target_items = {str(i.get("id") or ""): i for i in children}
    connectors = list(client.list_connectors(target_board)); used: set[str] = set(); geometry = []
    for source in source_inventory["connectors"]:
        expected = full._connector_payload(source, native_mapping, source_items, source_image, str(target_image["id"]), manifest)
        pair = _endpoint_ids(expected)
        matches = [c for c in connectors if str(c.get("id") or "") not in used and _endpoint_ids(c) == pair and visual.redline.same_connector(c, expected)]
        if len(matches) != 1:
            raise ValueError(f"Miro Tips connector does not match frozen source route: {source.get('id')}")
        actual = matches[0]; used.add(str(actual["id"]))
        geometry.append(connector_geometry_evidence(str(source.get("id") or ""), expected | ({"_ddda_legacy_visual_arrow": deepcopy(source["_ddda_legacy_visual_arrow"])} if source.get("_ddda_legacy_visual_arrow") else {}), actual, target_items, target_image))
    direct = [c for c in connectors if str(target_image.get("id") or "") in _endpoint_ids(c)]
    if len(used) != 11 or len(direct) != 8:
        raise ValueError(f"Miro Tips endpoint topology mismatch: validated={len(used)}, direct_image={len(direct)}")
    return {"policy": tips.MIRO_TIPS_VISUAL_EQUIVALENCE_POLICY, "source_item_count": 17, "target_item_count": 17, "item_type_counts": dict(tips.EXPECTED_ITEM_TYPE_COUNTS), "source_connector_count": 11, "target_connector_count": 8, "actual_target_connector_count": 11, "connector_contract_count": 11, "native_item_count": len(native_mapping), "source_image_id": str(source_image.get("id") or ""), "target_image_id": str(target_image.get("id") or ""), "status": "PASS", "STRUCTURAL_REFERENCE_MATCH": "PASS", "ENDPOINT_GEOMETRY_MATCH": "PASS", "HUMAN_VISUAL_ACCEPTANCE": "PENDING", "reference_structure_policy": REFERENCE_STRUCTURE_POLICY, "visual_acceptance_authority": VISUAL_ACCEPTANCE_AUTHORITY, "reference_endpoint_contract": connector_contract_evidence(source_inventory["connectors"], str(source_image.get("id") or "")), "endpoint_geometry": {"status": "PASS", "matched": len(geometry), "expected": 11, "tolerance_board_units": ENDPOINT_GEOMETRY_TOLERANCE, "connectors": geometry}, "render_fidelity": {"status": "PASS", "routing_proxy_policy": ROUTING_PROXY_POLICY, "endpoint_policy": ENDPOINT_POLICY, "routing_proxy_count": 0, "compatibility_anchor_count": len(anchors), "actual_connector_count": len(used), "direct_image_source_connector_count": len(source_inventory["direct_image_connectors"]), "text_callout_connector_count": len(source_inventory["text_connectors"]), "direct_image_target_connector_count": len(direct)}}


def _apply_contract() -> None:
    full.EXPECTED_COMPATIBILITY_ANCHORS = EXPECTED_COMPATIBILITY_ANCHORS
    full.ROUTING_PROXY_POLICY = ROUTING_PROXY_POLICY; full.ENDPOINT_POLICY = ENDPOINT_POLICY; full.REFERENCE_STRUCTURE_POLICY = REFERENCE_STRUCTURE_POLICY
    full.is_control_artifact = is_control_artifact; full._controls_ready = controls_ready; full._rebuild_controls_below_native = rebuild_controls_below_native
    full._target_proxy = target_image_not_proxy; full._free_endpoint_contract = free_endpoint_forbidden; full._structural_readback = structural_readback
    fidelity.is_control_anchor = is_control_artifact; fidelity.EXPECTED_CONTROL_ANCHORS = EXPECTED_COMPATIBILITY_ANCHORS


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        _apply_contract(); return
    for name in ("EXPECTED_COMPATIBILITY_ANCHORS", "ROUTING_PROXY_POLICY", "ENDPOINT_POLICY", "REFERENCE_STRUCTURE_POLICY", "is_control_artifact", "_controls_ready", "_rebuild_controls_below_native", "_target_proxy", "_free_endpoint_contract", "_structural_readback"):
        _ORIGINALS[name] = getattr(full, name)
    _ORIGINALS["fidelity_is_control_anchor"] = fidelity.is_control_anchor; _ORIGINALS["fidelity_expected"] = fidelity.EXPECTED_CONTROL_ANCHORS
    _apply_contract(); _INSTALLED = True


def uninstall() -> None:
    global _INSTALLED
    if not _INSTALLED: return
    for name in ("EXPECTED_COMPATIBILITY_ANCHORS", "ROUTING_PROXY_POLICY", "ENDPOINT_POLICY", "REFERENCE_STRUCTURE_POLICY", "is_control_artifact", "_controls_ready", "_rebuild_controls_below_native", "_target_proxy", "_free_endpoint_contract", "_structural_readback"):
        setattr(full, name, _ORIGINALS[name])
    fidelity.is_control_anchor = _ORIGINALS["fidelity_is_control_anchor"]; fidelity.EXPECTED_CONTROL_ANCHORS = _ORIGINALS["fidelity_expected"]
    _INSTALLED = False
