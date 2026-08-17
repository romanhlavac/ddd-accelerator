from __future__ import annotations

import pytest

from ddda_miro import miro_tips_endpoint_geometry_v4 as v4


REST_IDS = [
    "3458764679531043384",
    "3458764679531043385",
    "3458764679531043388",
    "3458764679531043389",
    "3458764679531043390",
    "3458764679531043391",
    "3458764679531043392",
    "3458764679531043394",
]


def _manifest() -> dict:
    return {"miro_tips": {"expected_rest_connector_ids": list(REST_IDS)}}


def test_reference_rest_connector_contract_freezes_all_eight_live_ids():
    v4.validate_rest_connector_identity([{"id": value} for value in REST_IDS], _manifest())

    with pytest.raises(ValueError, match="connector identity drift"):
        v4.validate_rest_connector_identity(
            [{"id": value} for value in REST_IDS[:-1]] + [{"id": "wrong"}],
            _manifest(),
        )


def test_generic_free_endpoint_fallback_is_forbidden():
    with pytest.raises(ValueError, match="generic/free endpoint fallback is forbidden"):
        v4.free_endpoint_forbidden(
            {"position": {"x": 0.04, "y": 0.35}}, {}, {}, "proxy"
        )


def test_endpoint_geometry_gate_rejects_shift_larger_than_two_board_units():
    item = {
        "id": "image",
        "position": {"x": 1000.0, "y": 500.0},
        "geometry": {"width": 2000.0, "height": 1000.0},
    }
    expected = {"id": "image", "position": {"x": 0.25, "y": 0.10}}
    same = {"id": "image", "position": {"x": 0.25, "y": 0.10}}
    assert v4.endpoint_geometry_row(expected, same, {"image": item}, "end")["status"] == "PASS"

    shifted = {"id": "image", "position": {"x": 0.252, "y": 0.10}}
    with pytest.raises(ValueError, match="endpoint geometry drift exceeds tolerance"):
        v4.endpoint_geometry_row(expected, shifted, {"image": item}, "end")


def test_endpoint_geometry_gate_rejects_silent_auto_anchor_fallback():
    item = {
        "id": "image",
        "position": {"x": 1000.0, "y": 500.0},
        "geometry": {"width": 2000.0, "height": 1000.0},
    }
    with pytest.raises(ValueError, match="silently fell back to auto-anchor"):
        v4.endpoint_geometry_row(
            {"id": "image", "position": {"x": 0.25, "y": 0.10}},
            {"id": "image"},
            {"image": item},
            "end",
        )


def test_v4_control_artifact_rejects_full_screenshot_proxy():
    proxy = {
        "id": "proxy",
        "type": "shape",
        "parent": {"id": "frame"},
        "data": {"shape": "rectangle", "content": "<p>\u200b</p>"},
        "geometry": {"width": 1919.433, "height": 1079.681},
        "style": {"fillOpacity": 0.0, "borderOpacity": 0.0},
    }
    assert not v4.is_control_artifact(proxy, "frame")


def test_legacy_rendered_endpoint_gate_checks_circle_boundary_not_centre():
    image = {
        "id": "image",
        "position": {"x": 1000.0, "y": 500.0},
        "geometry": {"width": 2000.0, "height": 1000.0},
    }
    spec = {
        "key": "navigation_mode",
        "start": (0.06320, 0.23765),
        "end": (0.04375, 0.23765),
    }
    desired_start = v4._absolute_reference_point(spec["start"], image)
    desired_end = v4._absolute_reference_point(spec["end"], image)
    radius = 4.0
    items = {
        "start": {
            "id": "start",
            "position": {"x": desired_start[0] + radius, "y": desired_start[1]},
            "geometry": {"width": 8.0, "height": 8.0},
        },
        "end": {
            "id": "end",
            "position": {"x": desired_end[0] - radius, "y": desired_end[1]},
            "geometry": {"width": 8.0, "height": 8.0},
        },
    }
    connector = {
        "startItem": {"id": "start", "position": {"x": 0.0, "y": 0.5}},
        "endItem": {"id": "end", "position": {"x": 1.0, "y": 0.5}},
    }
    evidence = v4.legacy_visual_endpoint_evidence(
        {"_ddda_legacy_visual_arrow": spec}, connector, items, image
    )
    assert evidence and evidence["start"]["max_axis_delta"] == 0
    assert evidence["end"]["max_axis_delta"] == 0

    items["end"]["position"]["x"] += 4.0
    with pytest.raises(ValueError, match="rendered endpoint drift exceeds tolerance"):
        v4.legacy_visual_endpoint_evidence(
            {"_ddda_legacy_visual_arrow": spec}, connector, items, image
        )
