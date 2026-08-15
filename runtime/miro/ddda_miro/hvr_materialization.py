from __future__ import annotations

"""Render-fidelity aware HVR materialization for PR8 Miro Tips.

The server-side HVR copy must preserve the visible frozen reference plus the
transparent technical routing controls used to avoid Miro's direct-image
connector normalization.  Visible reference fidelity remains structurally
automated; human visual acceptance remains a separate authority.
"""

from collections import Counter
from copy import deepcopy
from typing import Any

from . import hvr_materialization_legacy as _base
from . import miro_tips_full_arrow_fidelity_fix as full_arrow
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
        if not fidelity.is_control_anchor(item, frame_id)
    ]


def _anchors(children: list[dict[str, Any]], frame_id: str) -> list[dict[str, Any]]:
    return [
        item for item in children
        if fidelity.is_control_anchor(item, frame_id)
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


def copied_board_readback(
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
    if source_direct or target_direct:
        raise ValueError(
            "HVR Miro Tips contains direct-image callouts; transparent routing proxy is required"
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
            "full_arrow_reference_structure_policy": full_arrow.REFERENCE_STRUCTURE_POLICY,
            "visual_acceptance_authority": full_arrow.VISUAL_ACCEPTANCE_AUTHORITY,
            "render_fidelity_policy": {
                "routing_proxy": full_arrow.ROUTING_PROXY_POLICY,
                "endpoint": full_arrow.ENDPOINT_POLICY,
            },
            "source_frame_id": source_frame_id,
            "frame_id": target_frame_id,
            "item_count": len(target_visible),
            "physical_child_count": len(target_children),
            "item_type_counts": dict(_base.tips.EXPECTED_ITEM_TYPE_COUNTS),
            "technical_anchor_count": anchor_count,
            # Historical workflow compatibility value; the wrapped copy proof
            # validates 11 actual connectors before returning 8 here.
            "connector_count": connector_count,
            "actual_connector_count": len(target_connectors),
            "direct_image_connector_count": len(target_direct),
            "image": image_evidence,
            "status": "PASS",
            "review_url": (
                f"https://miro.com/app/board/{target_board_id}/"
                f"?moveToWidget={target_frame_id}"
            ),
        },
        "technical_status": "PASS",
        "human_review_status": "PENDING",
        "overall_status": "READY_FOR_HUMAN_REVIEW",
        "merge_allowed": False,
        "promotion_allowed": False,
        "release_allowed": False,
    }


# The legacy materializer owns credential checks, logical-slot replacement and
# server-side board copy.  Only its copied-board proof is replaced.
_base.copied_board_readback = copied_board_readback
materialize = _base.materialize


def main(argv: list[str] | None = None) -> int:
    _base.copied_board_readback = copied_board_readback
    return _base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
