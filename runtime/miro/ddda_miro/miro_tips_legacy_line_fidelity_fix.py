from __future__ import annotations

"""Reconstruct the three legacy free-form Miro Tips arrows omitted by REST v2.

The approved Miro Tips board contains eight REST-v2 connectors plus three
visible free-form arrows next to the navigation/sticky/connection-line text.
Those three legacy lines are visible in the approved reference but cannot be
read back as REST-v2 connectors because Miro v2 does not support loose or
dangling connectors.  This module therefore treats the approved screenshot as
an explicit visual oracle for those three arrows and reconstructs them with
transparent per-endpoint shapes.  Miro enforces an 8-unit minimum circle
geometry, so each helper centre is offset by half that rendered size and each
connector endpoint is explicitly pinned to the facing edge.  The visible line
therefore begins/ends at the frozen reference coordinate rather than at the
helper centre.

The endpoint coordinates below are normalized to the approved reference image
/frame.  They are versioned data, not heuristic layout.  REST-readable
connectors continue to be cloned from the live reference metadata.
"""

from copy import deepcopy
from typing import Any

from . import miro_tips_full_arrow_fidelity_fix as full
from . import miro_tips_hvr_fix as tips
from . import miro_tips_endpoint_geometry_v4 as endpoint_v4
from . import review_board_recovery as base
from . import review_board_recovery_wirefix as visual


REFERENCE_REST_CONNECTOR_COUNT = 8
LEGACY_VISUAL_ARROW_COUNT = 3

# Normalized against the approved Miro Tips frame screenshot.  Each arrow runs
# from start (right) to end (left) and ends with the arrowhead beside the Miro
# toolbar icon.  The values come from the frozen reference screenshot, whose
# geometry is already asserted by the Miro Tips contract.
LEGACY_ARROW_SPECS: tuple[dict[str, Any], ...] = (
    {
        "key": "navigation_mode",
        "text_marker": "toggle between navigation mode & edit mode",
        "start": (0.06320, 0.23765),
        "end": (0.04375, 0.23765),
    },
    {
        "key": "sticky_notes",
        "text_marker": "stickies / post-its",
        "start": (0.06390, 0.36520),
        "end": (0.04445, 0.36520),
    },
    {
        "key": "connection_lines",
        "text_marker": "arrows / connection lines",
        "start": (0.06530, 0.45255),
        "end": (0.04585, 0.45255),
    },
)

_ORIGINAL_SOURCE_INVENTORY = full._source_inventory
_ORIGINAL_COMPATIBILITY_POSITIONS = full._compatibility_anchor_positions
_ORIGINAL_CONNECTOR_PAYLOAD = full._connector_payload
_ORIGINAL_RECONCILE_CONNECTORS = full._reconcile_connectors
_INSTALLED = False


def _visible_text(item: dict[str, Any]) -> str:
    return base._visible((item.get("data") or {}).get("content")).casefold()


def _absolute_position(
    target_image: dict[str, Any], normalized: tuple[float, float]
) -> tuple[float, float]:
    position = target_image.get("position") or {}
    geometry = target_image.get("geometry") or {}
    width = float(geometry.get("width") or 0)
    height = float(geometry.get("height") or 0)
    if width <= 0 or height <= 0:
        raise ValueError("Miro Tips target screenshot has invalid geometry")
    left = float(position["x"]) - width / 2.0
    top = float(position["y"]) - height / 2.0
    return (
        left + float(normalized[0]) * width,
        top + float(normalized[1]) * height,
    )


def _legacy_source_connectors(
    items: list[dict[str, Any]],
    source_image_id: str,
    template: dict[str, Any],
) -> list[dict[str, Any]]:
    text_items = [item for item in items if str(item.get("type") or "") == "text"]
    result: list[dict[str, Any]] = []
    for spec in LEGACY_ARROW_SPECS:
        matches = [
            item for item in text_items if spec["text_marker"] in _visible_text(item)
        ]
        if len(matches) != 1:
            raise ValueError(
                "Miro Tips legacy visual arrow could not resolve its source text: "
                f"{spec['text_marker']!r}; matches={len(matches)}"
            )
        source_text = matches[0]
        style = deepcopy(template.get("style") or {})
        style["startStrokeCap"] = "none"
        style["endStrokeCap"] = style.get("endStrokeCap") or "stealth"
        result.append(
            {
                "id": f"ddda-legacy-visual-arrow-{spec['key']}",
                "shape": "straight",
                "style": style,
                "startItem": {"id": str(source_text.get("id") or "")},
                "endItem": {
                    "id": str(source_image_id),
                    "position": {
                        "x": f"{float(spec['end'][0]) * 100:g}%",
                        "y": f"{float(spec['end'][1]) * 100:g}%",
                    },
                },
                "_ddda_legacy_visual_arrow": deepcopy(spec),
            }
        )
    return result


def source_inventory_with_legacy_visual_arrows(
    client: Any,
    board: str,
    frame_id: str,
    image_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    expected = full._reference_contract(manifest)
    items = list(base._children(client, board, frame_id))
    child_ids = {str(item.get("id") or "") for item in items}
    text_ids = {
        str(item.get("id") or "")
        for item in items
        if str(item.get("type") or "") == "text"
    }
    rows = full.classify_reference_connectors(
        list(client.list_connectors(board)), child_ids, image_id, text_ids
    )
    if len(rows["all"]) != REFERENCE_REST_CONNECTOR_COUNT:
        raise ValueError(
            "Miro Tips REST-readable reference connector count changed: "
            f"expected={REFERENCE_REST_CONNECTOR_COUNT}, actual={len(rows['all'])}, "
            f"connectors={full._connector_diagnostic(rows['all'])}"
        )
    if len(rows["direct_image"]) != REFERENCE_REST_CONNECTOR_COUNT:
        raise ValueError(
            "Miro Tips approved REST connector set is no longer the eight screenshot callouts"
        )
    if rows["text"]:
        raise ValueError(
            "Miro Tips legacy text arrows unexpectedly became REST-readable; "
            "review the v4 reconstruction contract before changing behavior"
        )

    endpoint_v4.validate_rest_connector_identity(rows["direct_image"], manifest)

    template = rows["direct_image"][0]
    legacy = _legacy_source_connectors(items, image_id, template)
    connectors = list(rows["all"]) + legacy
    counts = {
        "total": len(connectors),
        "direct": len(rows["direct_image"]),
        "text": len(legacy),
    }
    if counts != expected:
        raise ValueError(
            f"Miro Tips visual reference inventory mismatch: expected={expected}, actual={counts}"
        )

    state = {
        "items": items,
        "item_type_counts": {
            kind: sum(1 for item in items if str(item.get("type") or "") == kind)
            for kind in ("image", "sticky_note", "text")
        },
        "connectors": connectors,
        "text": " ".join(_visible_text(item) for item in items),
    }
    state["item_type_counts"] = {
        key: value for key, value in state["item_type_counts"].items() if value
    }
    cfg = tips._config(manifest)
    tips._assert_snapshot(
        state, cfg, "Miro Tips source", require_reference_image=True
    )
    return {
        "items": items,
        "connectors": connectors,
        "direct_image_connectors": rows["direct_image"],
        "text_connectors": legacy,
        "counts": counts,
        "rest_connector_count": len(rows["all"]),
        "legacy_visual_arrow_count": len(legacy),
    }


def compatibility_positions_with_legacy_arrows(
    direct_connectors: list[dict[str, Any]], target_image: dict[str, Any]
) -> list[tuple[float, float]]:
    if len(direct_connectors) != REFERENCE_REST_CONNECTOR_COUNT:
        raise ValueError("Miro Tips direct screenshot connector set must contain eight rows")
    radius = float(full.fidelity.CONTROL_ANCHOR_SIZE) / 2.0
    positions: list[tuple[float, float]] = []
    for spec in LEGACY_ARROW_SPECS:
        start = _absolute_position(target_image, spec["start"])
        end = _absolute_position(target_image, spec["end"])
        if abs(start[1] - end[1]) > 0.01 or start[0] <= end[0]:
            raise ValueError(
                f"Miro Tips legacy visual arrow {spec['key']} is no longer a left-pointing horizontal contract"
            )
        positions.append((start[0] + radius, start[1]))
        positions.append((end[0] - radius, end[1]))
    if len(positions) != endpoint_v4.EXPECTED_COMPATIBILITY_ANCHORS:
        raise AssertionError("Miro Tips control-artifact compatibility count changed")
    return positions


def _find_anchor(
    client: Any,
    board: str,
    frame_id: str,
    x: float,
    y: float,
    used: set[str],
) -> dict[str, Any]:
    matches = [
        item
        for item in full._legacy_anchors(client, board, frame_id)
        if str(item.get("id") or "") not in used
        and full.fidelity._same_anchor(item, frame_id, x, y)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Miro Tips legacy visual arrow endpoint expected one technical anchor at {(x, y)}, got {len(matches)}"
        )
    used.add(str(matches[0].get("id") or ""))
    return matches[0]


def connector_payload_with_legacy_visual_arrow(
    source: dict[str, Any],
    native_mapping: dict[str, str],
    source_items: dict[str, dict[str, Any]],
    source_image: dict[str, Any],
    proxy_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    spec = source.get("_ddda_legacy_visual_arrow")
    if not isinstance(spec, dict):
        return _ORIGINAL_CONNECTOR_PAYLOAD(
            source,
            native_mapping,
            source_items,
            source_image,
            proxy_id,
            manifest,
        )
    anchor_id = str(source.get("_ddda_target_start_anchor_id") or "")
    end_anchor_id = str(source.get("_ddda_target_end_anchor_id") or "")
    if not anchor_id or not end_anchor_id:
        raise ValueError(
            f"Miro Tips legacy visual arrow {spec.get('key')} has no resolved technical endpoints"
        )
    payload = visual.readable_connector_payload(
        source, anchor_id, end_anchor_id, manifest
    )
    payload["startItem"] = {
        "id": anchor_id,
        "position": {"x": 0.0, "y": 0.5},
    }
    payload["endItem"] = {
        "id": end_anchor_id,
        "position": {"x": 1.0, "y": 0.5},
    }
    payload["shape"] = "straight"
    return payload


def reconcile_connectors_with_legacy_visual_arrows(
    client: Any,
    source_inventory: dict[str, Any],
    source_board: str,
    target_board: str,
    target_frame_id: str,
    source_image: dict[str, Any],
    target_image: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    used: set[str] = set()
    positions = compatibility_positions_with_legacy_arrows(
        source_inventory["direct_image_connectors"], target_image
    )
    for index, connector in enumerate(source_inventory["text_connectors"]):
        start_x, start_y = positions[index * 2]
        end_x, end_y = positions[index * 2 + 1]
        start_anchor = _find_anchor(
            client, target_board, target_frame_id, start_x, start_y, used
        )
        end_anchor = _find_anchor(
            client, target_board, target_frame_id, end_x, end_y, used
        )
        connector["_ddda_target_start_anchor_id"] = str(start_anchor["id"])
        connector["_ddda_target_end_anchor_id"] = str(end_anchor["id"])
    return _ORIGINAL_RECONCILE_CONNECTORS(
        client,
        source_inventory,
        source_board,
        target_board,
        target_frame_id,
        source_image,
        target_image,
        manifest,
    )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        endpoint_v4.install()
        full._source_inventory = source_inventory_with_legacy_visual_arrows
        full._compatibility_anchor_positions = compatibility_positions_with_legacy_arrows
        full._connector_payload = connector_payload_with_legacy_visual_arrow
        full._reconcile_connectors = reconcile_connectors_with_legacy_visual_arrows
        return
    endpoint_v4.install()
    full._source_inventory = source_inventory_with_legacy_visual_arrows
    full._compatibility_anchor_positions = compatibility_positions_with_legacy_arrows
    full._connector_payload = connector_payload_with_legacy_visual_arrow
    full._reconcile_connectors = reconcile_connectors_with_legacy_visual_arrows
    _INSTALLED = True


def uninstall() -> None:
    global _INSTALLED
    if not _INSTALLED:
        return
    full._source_inventory = _ORIGINAL_SOURCE_INVENTORY
    full._compatibility_anchor_positions = _ORIGINAL_COMPATIBILITY_POSITIONS
    full._connector_payload = _ORIGINAL_CONNECTOR_PAYLOAD
    full._reconcile_connectors = _ORIGINAL_RECONCILE_CONNECTORS
    endpoint_v4.uninstall()
    _INSTALLED = False
