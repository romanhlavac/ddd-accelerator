from __future__ import annotations

"""Render-fidelity aware HVR materialization for PR8 Miro Tips.

The server-side HVR copy must preserve the visible frozen reference, the eight
direct screenshot attachments, and the six compensated 8-unit transparent per-endpoint controls used only for
the three legacy free-form lines.  Structural and endpoint-geometry evidence
are automated; human visual acceptance remains a separate authority.
"""

from collections import Counter
from copy import deepcopy
from typing import Any

from . import hvr_materialization_legacy as _base
from . import miro_tips_full_arrow_fidelity_fix as full_arrow
from . import miro_tips_endpoint_geometry_v4 as endpoint_v4
from . import miro_tips_legacy_line_fidelity_fix as legacy_line
from . import miro_tips_render_fidelity_fix as fidelity

# Preserve the existing public module surface.  Underscore helpers are delegated
# through __getattr__ below so the established test/CLI contract remains usable.
from .hvr_materialization_legacy import *  # noqa: F401,F403


# The PR8 full-arrow contract keeps the existing HVR workflow compatibility
# fields while proving that the server-side copy contains all eleven arrows.
full_arrow.install_hvr_contract(_base)


def __getattr__(name: str) -> Any:
    return getattr(_base, name)


def _visible(children: list[dict[str, Any]], frame_id: str) -> list[dict[str, Any]]:
    return [
        item for item in children
        if not full_arrow.is_control_artifact(item, frame_id)
    ]


def _anchors(children: list[dict[str, Any]], frame_id: str) -> list[dict[str, Any]]:
    return [
        item for item in children
        if full_arrow.is_control_artifact(item, frame_id)
    ]


def _assert_anchor_copy(
    source_children: list[dict[str, Any]],
    target_children: list[dict[str, Any]],
    source_frame_id: str,
    target_frame_id: str,
    mapping: dict[str, str],
) -> int:
    source_anchors = _anchors(source_children, source_frame_id)
    target_anchors = _anchors(target_children, target_frame_id)
    if (
        len(source_anchors) != fidelity.EXPECTED_CONTROL_ANCHORS
        or len(target_anchors) != fidelity.EXPECTED_CONTROL_ANCHORS
    ):
        raise ValueError(
            "HVR Miro Tips technical-anchor count differs from DDDA_PLATFORM_LAB"
        )

    used: set[str] = set()
    for source in source_anchors:
        source_position = source.get("position") or {}
        matches = [
            target
            for target in target_anchors
            if str(target.get("id") or "") not in used
            and _base.redline._close(
                (target.get("position") or {}).get("x"), source_position.get("x")
            )
            and _base.redline._close(
                (target.get("position") or {}).get("y"), source_position.get("y")
            )
        ]
        if len(matches) != 1:
            raise ValueError(
                "HVR Miro Tips technical anchor differs from DDDA_PLATFORM_LAB: "
                f"{source.get('id')}"
            )
        target = matches[0]
        expected = _base._copy_item_payload(source, target_frame_id)
        if not _base.redline.same_item(target, expected):
            raise ValueError(
                "HVR Miro Tips technical anchor payload differs from DDDA_PLATFORM_LAB: "
                f"{source.get('id')}"
            )
        source_id = str(source.get("id") or "")
        target_id = str(target.get("id") or "")
        mapping[source_id] = target_id
        used.add(target_id)
    return len(used)


def _assert_connector_copy_with_full_arrow_compatibility(
    source_connectors: list[dict[str, Any]],
    target_connectors: list[dict[str, Any]],
    mapping: dict[str, str],
) -> int:
    """Validate the 11-arrow contract while preserving the legacy report field.

    The legacy copier validates against ``tips.EXPECTED_CONNECTOR_COUNT`` before
    the full-arrow wrapper can translate the proven count back to the historical
    workflow compatibility value of eight.  During an actual v3 HVR copy, both
    boards legitimately contain eleven arrows (eight direct callouts plus three
    text callouts), so bind the legacy verifier to that exact count only for the
    duration of this proof and restore the module contract immediately after it.
    """
    source_count = len(source_connectors)
    target_count = len(target_connectors)
    if source_count != target_count:
        raise ValueError(
            "HVR Miro Tips connector count differs from DDDA_PLATFORM_LAB exact reference"
        )

    if source_count != full_arrow.EXPECTED_REFERENCE_CONNECTORS:
        return int(_base._assert_connector_copy(source_connectors, target_connectors, mapping))

    previous_expected = _base.tips.EXPECTED_CONNECTOR_COUNT
    _base.tips.EXPECTED_CONNECTOR_COUNT = full_arrow.EXPECTED_REFERENCE_CONNECTORS
    try:
        return int(_base._assert_connector_copy(source_connectors, target_connectors, mapping))
    finally:
        _base.tips.EXPECTED_CONNECTOR_COUNT = previous_expected


def _assert_hvr_endpoint_geometry(
    source_connectors: list[dict[str, Any]],
    target_connectors: list[dict[str, Any]],
    mapping: dict[str, str],
    target_children: list[dict[str, Any]],
) -> dict[str, Any]:
    items = {str(item.get("id") or ""): item for item in target_children}
    used: set[str] = set()
    rows: list[dict[str, Any]] = []
    for source in source_connectors:
        expected = deepcopy(source)
        for endpoint_name in ("startItem", "endItem"):
            endpoint = deepcopy(source.get(endpoint_name) or {})
            source_id = str(endpoint.get("id") or "")
            target_id = mapping.get(source_id)
            if not target_id:
                raise ValueError(
                    f"HVR endpoint contract has no mapped item for {source_id}"
                )
            endpoint["id"] = target_id
            expected[endpoint_name] = endpoint
        start_id = str((expected.get("startItem") or {}).get("id") or "")
        end_id = str((expected.get("endItem") or {}).get("id") or "")
        matches = [
            row for row in target_connectors
            if str(row.get("id") or "") not in used
            and str((row.get("startItem") or {}).get("id") or "") == start_id
            and str((row.get("endItem") or {}).get("id") or "") == end_id
            and _base.redline.same_connector(row, expected)
        ]
        if len(matches) != 1:
            raise ValueError(
                "HVR endpoint-geometry connector mapping differs from DDDA_PLATFORM_LAB: "
                f"source={source.get('id')}"
            )
        target = matches[0]
        used.add(str(target.get("id") or ""))
        rows.append(
            endpoint_v4.connector_geometry_evidence(
                str(source.get("id") or ""), expected, target, items
            )
        )
    if len(rows) != full_arrow.EXPECTED_REFERENCE_CONNECTORS:
        raise ValueError(
            f"HVR endpoint geometry validated {len(rows)} connectors; expected 11"
        )
    return {
        "status": "PASS",
        "matched": len(rows),
        "expected": full_arrow.EXPECTED_REFERENCE_CONNECTORS,
        "tolerance_board_units": endpoint_v4.ENDPOINT_GEOMETRY_TOLERANCE,
        "connectors": rows,
    }


def _copied_board_readback_v4(
    client: _base.MiroClient,
    source_board_id: str,
    target_board_id: str,
    source_sha: str,
) -> dict[str, Any]:
    """Fail closed unless HVR preserves visible reference and routing controls."""
    source = client._request(
        "GET", f"boards/{_base.urllib.parse.quote(source_board_id, safe='')}"
    )
    target = client._request(
        "GET", f"boards/{_base.urllib.parse.quote(target_board_id, safe='')}"
    )
    if source.get("name") != _base.PLATFORM_LAB_NAME:
        raise ValueError("HVR source is not DDDA_PLATFORM_LAB")
    if target.get("name") != _base.HVR_NAME:
        raise ValueError("copied board is not the DDDA_HVR logical slot")

    source_items = client.list_items(source_board_id)
    target_items = client.list_items(target_board_id)
    if Counter(str(item.get("type") or "") for item in source_items) != Counter(
        str(item.get("type") or "") for item in target_items
    ):
        raise ValueError("HVR board item-type read-back differs from DDDA_PLATFORM_LAB")

    source_frame = _base._tips_frame(source_items, "DDDA_PLATFORM_LAB")
    target_frame = _base._tips_frame(target_items, "DDDA_HVR")
    _base._assert_frame_copy(source_frame, target_frame)
    source_frame_id = str(source_frame.get("id") or "")
    target_frame_id = str(target_frame.get("id") or "")
    source_children = _base._children(source_items, source_frame_id)
    target_children = _base._children(target_items, target_frame_id)
    source_visible = _visible(source_children, source_frame_id)
    target_visible = _visible(target_children, target_frame_id)

    expected_types = Counter(_base.tips.EXPECTED_ITEM_TYPE_COUNTS)
    if Counter(str(item.get("type") or "") for item in source_visible) != expected_types:
        raise ValueError(
            "DDDA_PLATFORM_LAB Miro Tips visible topology differs from frozen reference"
        )
    if Counter(str(item.get("type") or "") for item in target_visible) != expected_types:
        raise ValueError("HVR Miro Tips visible topology differs from frozen reference")

    mapping = _base._assert_native_copy(
        source_visible, target_visible, target_frame_id
    )
    image_evidence = _base._assert_image_copy(
        client,
        source_board_id,
        target_board_id,
        source_visible,
        target_visible,
        mapping,
    )
    anchor_count = _assert_anchor_copy(
        source_children,
        target_children,
        source_frame_id,
        target_frame_id,
        mapping,
    )

    source_child_ids = {str(item.get("id") or "") for item in source_children}
    target_child_ids = {str(item.get("id") or "") for item in target_children}
    source_connectors = _base._related_connectors(
        client, source_board_id, source_child_ids
    )
    target_connectors = _base._related_connectors(
        client, target_board_id, target_child_ids
    )
    connector_count = _assert_connector_copy_with_full_arrow_compatibility(
        source_connectors, target_connectors, mapping
    )

    source_image_id = str(image_evidence["source_image_id"])
    target_image_id = str(image_evidence["target_image_id"])
    source_direct = [
        connector for connector in source_connectors
        if str((connector.get("endItem") or {}).get("id") or "") == source_image_id
    ]
    target_direct = [
        connector for connector in target_connectors
        if str((connector.get("endItem") or {}).get("id") or "") == target_image_id
    ]
    if len(source_direct) != full_arrow.EXPECTED_DIRECT_IMAGE_CONNECTORS:
        raise ValueError(
            "DDDA_PLATFORM_LAB Miro Tips must contain eight direct screenshot callouts"
        )
    if len(target_direct) != full_arrow.EXPECTED_DIRECT_IMAGE_CONNECTORS:
        raise ValueError(
            "HVR Miro Tips must preserve eight direct screenshot callouts"
        )
    endpoint_geometry = _assert_hvr_endpoint_geometry(
        source_connectors, target_connectors, mapping, target_children
    )

    return {
        "source_sha": source_sha,
        "source_board_id": source_board_id,
        "source_board_name": _base.PLATFORM_LAB_NAME,
        "hvr_board_id": target_board_id,
        "hvr_board_name": _base.HVR_NAME,
        "miro_tips": {
            # Existing field remains the historical structural compatibility
            # contract; the v3 full-arrow contract is exposed separately.
            "policy": _base.tips.MIRO_TIPS_VISUAL_EQUIVALENCE_POLICY,
            "reference_structure_policy": fidelity.REFERENCE_STRUCTURE_POLICY,
            "full_arrow_reference_structure_policy": endpoint_v4.REFERENCE_STRUCTURE_POLICY,
            "visual_acceptance_authority": endpoint_v4.VISUAL_ACCEPTANCE_AUTHORITY,
            "render_fidelity_policy": {
                "routing_proxy": endpoint_v4.ROUTING_PROXY_POLICY,
                "endpoint": endpoint_v4.ENDPOINT_POLICY,
            },
            "source_frame_id": source_frame_id,
            "frame_id": target_frame_id,
            "item_count": len(target_visible),
            "physical_child_count": len(target_children),
            "item_type_counts": dict(_base.tips.EXPECTED_ITEM_TYPE_COUNTS),
            "technical_anchor_count": anchor_count,
            "connector_count": connector_count,
            "actual_connector_count": len(target_connectors),
            "direct_image_connector_count": len(target_direct),
            "image": image_evidence,
            "STRUCTURAL_REFERENCE_MATCH": "PASS",
            "ENDPOINT_GEOMETRY_MATCH": "PASS",
            "HUMAN_VISUAL_ACCEPTANCE": "PENDING",
            "endpoint_geometry": endpoint_geometry,
            "status": "PASS",
            "review_url": (
                f"https://miro.com/app/board/{target_board_id}/"
                f"?moveToWidget={target_frame_id}"
            ),
        },
        "technical_status": "PASS",
        "STRUCTURAL_REFERENCE_MATCH": "PASS",
        "ENDPOINT_GEOMETRY_MATCH": "PASS",
        "HUMAN_VISUAL_ACCEPTANCE": "PENDING",
        "human_review_status": "PENDING",
        "overall_status": "READY_FOR_HUMAN_REVIEW",
        "merge_allowed": False,
        "promotion_allowed": False,
        "release_allowed": False,
    }


def copied_board_readback(
    client: _base.MiroClient,
    source_board_id: str,
    target_board_id: str,
    source_sha: str,
) -> dict[str, Any]:
    legacy_line.install()
    try:
        return _copied_board_readback_v4(
            client, source_board_id, target_board_id, source_sha
        )
    finally:
        legacy_line.uninstall()


# The legacy materializer owns credential checks, logical-slot replacement and
# server-side board copy.  Only its copied-board proof is replaced.
_base.copied_board_readback = copied_board_readback
materialize = _base.materialize


def main(argv: list[str] | None = None) -> int:
    _base.copied_board_readback = copied_board_readback
    return _base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
