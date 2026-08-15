from __future__ import annotations

from copy import deepcopy

import pytest

from ddda_miro import hvr_materialization as hvr
from ddda_miro import miro_tips_full_arrow_fidelity_fix as full
from ddda_miro import miro_tips_endpoint_geometry_v4 as endpoint_v4
from ddda_miro import miro_tips_hvr_fix as tips


def _frame(frame_id: str) -> dict:
    return {
        "id": frame_id,
        "type": "frame",
        "data": {"title": "Miro Tips"},
        "position": {"x": -19834.447, "y": -11727.529},
        "geometry": {"width": 1919.433, "height": 1079.681},
    }


def _children(prefix: str, frame_id: str) -> list[dict]:
    rows: list[dict] = [
        {
            "id": f"{prefix}-image",
            "type": "image",
            "parent": {"id": frame_id},
            "position": {"x": 960.648, "y": 539.841},
            "geometry": {"width": 1919.433, "height": 1079.681},
        }
    ]
    for index in range(13):
        rows.append(
            {
                "id": f"{prefix}-sticky-{index}",
                "type": "sticky_note",
                "parent": {"id": frame_id},
                "position": {"x": 100.0 + index * 100.0, "y": 400.0 + index},
                "geometry": {"width": 118.513},
                "data": {"content": f"<p>tip {index}</p>"},
                "style": {
                    "fillColor": "#fff9b1",
                    "textAlign": "center",
                    "textAlignVertical": "middle",
                },
            }
        )
    for index in range(3):
        rows.append(
            {
                "id": f"{prefix}-text-{index}",
                "type": "text",
                "parent": {"id": frame_id},
                "position": {"x": 220.0 + index * 180.0, "y": 280.0 + index * 100.0},
                "geometry": {"width": 156.0 + index * 40.0},
                "data": {"content": f"<p>text {index}</p>"},
                "style": {
                    "fontFamily": "open_sans",
                    "fontSize": 20,
                    "textAlign": "left",
                    "color": "#1a1a1a",
                },
            }
        )
    # Three legacy free-form arrows require two deterministic canonical 8-unit endpoints each.
    for index in range(endpoint_v4.EXPECTED_COMPATIBILITY_ANCHORS):
        rows.append(
            {
                "id": f"{prefix}-anchor-{index}",
                "type": "shape",
                "parent": {"id": frame_id},
                "position": {"x": 80.0 + index * 20.0, "y": 250.0 + (index // 2) * 100.0},
                "geometry": {"width": 8.0, "height": 8.0},
                "data": {"shape": "circle", "content": "<p>\u200b</p>"},
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
        )
    return rows


def _connectors(prefix: str) -> list[dict]:
    rows = [
        {
            "id": f"{prefix}-direct-{index}",
            "startItem": {"id": f"{prefix}-sticky-{index}"},
            "endItem": {
                "id": f"{prefix}-image",
                "position": {"x": 0.08 + index * 0.1, "y": 0.12 + index * 0.07},
            },
            "shape": "curved",
            "style": {
                "strokeColor": "#000000",
                "strokeStyle": "normal",
                "startStrokeCap": "none",
                "endStrokeCap": "stealth",
            },
            "captions": [],
        }
        for index in range(8)
    ]
    rows.extend(
        {
            "id": f"{prefix}-legacy-{index}",
            "startItem": {"id": f"{prefix}-anchor-{index * 2}"},
            "endItem": {"id": f"{prefix}-anchor-{index * 2 + 1}"},
            "shape": "straight",
            "style": {
                "strokeColor": "#000000",
                "strokeStyle": "normal",
                "startStrokeCap": "none",
                "endStrokeCap": "stealth",
            },
            "captions": [],
        }
        for index in range(3)
    )
    return rows


class FakeClient:
    def __init__(self) -> None:
        self.items = {
            "platform": [
                _frame("platform-frame"),
                *_children("platform", "platform-frame"),
                {"id": "platform-other", "type": "text", "data": {"content": "unchanged"}},
            ],
            "hvr": [
                _frame("hvr-frame"),
                *_children("hvr", "hvr-frame"),
                {"id": "hvr-other", "type": "text", "data": {"content": "unchanged"}},
            ],
        }
        self.connectors = {
            "platform": _connectors("platform"),
            "hvr": _connectors("hvr"),
        }

    def _request(self, method, path, **_kwargs):
        assert method == "GET"
        if path.endswith("platform"):
            return {"id": "platform", "name": hvr.PLATFORM_LAB_NAME}
        if path.endswith("hvr"):
            return {"id": "hvr", "name": hvr.HVR_NAME}
        raise AssertionError(path)

    def list_items(self, board_id):
        return deepcopy(self.items[board_id])

    def list_connectors(self, board_id):
        return deepcopy(self.connectors[board_id])


def _install_image_readback(monkeypatch, client: FakeClient, target_bytes: bytes | None = None):
    source_bytes = b"approved-reference-screenshot"
    target_bytes = source_bytes if target_bytes is None else target_bytes

    def source_image(_client, board, item_id):
        raw = source_bytes if board == "platform" else target_bytes
        image = next(item for item in client.items[board] if item.get("id") == item_id)
        return raw, "image/png", deepcopy(image)

    monkeypatch.setattr(hvr.image_transport, "source_image", source_image)
    return source_bytes


def test_copied_board_readback_proves_structural_and_endpoint_geometry_before_human_gate(monkeypatch):
    client = FakeClient()
    _install_image_readback(monkeypatch, client)

    report = hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)

    assert report["technical_status"] == "PASS"
    assert report["STRUCTURAL_REFERENCE_MATCH"] == "PASS"
    assert report["ENDPOINT_GEOMETRY_MATCH"] == "PASS"
    assert report["HUMAN_VISUAL_ACCEPTANCE"] == "PENDING"
    assert report["overall_status"] == "READY_FOR_HUMAN_REVIEW"
    miro = report["miro_tips"]
    assert miro["item_count"] == 17
    assert miro["physical_child_count"] == 23
    assert miro["technical_anchor_count"] == 6
    assert miro["connector_count"] == 8  # established workflow compatibility alias
    assert miro["actual_connector_count"] == 11
    assert miro["direct_image_connector_count"] == 8
    assert miro["endpoint_geometry"]["matched"] == 11
    assert miro["ENDPOINT_GEOMETRY_MATCH"] == "PASS"
    assert miro["HUMAN_VISUAL_ACCEPTANCE"] == "PENDING"
    assert report["merge_allowed"] is False


def test_copied_board_readback_rejects_endpoint_shift_even_when_connector_identity_still_matches(monkeypatch):
    client = FakeClient()
    _install_image_readback(monkeypatch, client)
    client.connectors["hvr"][0]["endItem"]["position"]["x"] += 0.01

    with pytest.raises(ValueError, match="connector differs|endpoint geometry"):
        hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)


def test_copied_board_readback_rejects_missing_endpoint_control(monkeypatch):
    client = FakeClient()
    _install_image_readback(monkeypatch, client)
    client.items["hvr"] = [
        item for item in client.items["hvr"] if item.get("id") != "hvr-anchor-5"
    ]

    with pytest.raises(ValueError, match="item-type read-back|technical-anchor count"):
        hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)


def test_copied_board_readback_rejects_generic_proxy_or_extra_control_topology(monkeypatch):
    client = FakeClient()
    _install_image_readback(monkeypatch, client)
    client.items["platform"].append(
        {
            "id": "platform-proxy",
            "type": "shape",
            "parent": {"id": "platform-frame"},
            "position": {"x": 960.648, "y": 539.841},
            "geometry": {"width": 1919.433, "height": 1079.681},
            "data": {"shape": "rectangle", "content": "<p>\u200b</p>"},
            "style": {"fillOpacity": 0.0, "borderOpacity": 0.0},
        }
    )
    client.items["hvr"].append(deepcopy(client.items["platform"][-1]) | {"id": "hvr-proxy", "parent": {"id": "hvr-frame"}})

    with pytest.raises(ValueError, match="technical-anchor count|visible topology"):
        hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)


def test_copied_board_readback_rejects_font_drift(monkeypatch):
    client = FakeClient()
    _install_image_readback(monkeypatch, client)
    target = next(item for item in client.items["hvr"] if item.get("id") == "hvr-text-0")
    target["style"]["fontSize"] = 24

    with pytest.raises(ValueError, match="native item differs"):
        hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)


def test_copied_board_readback_rejects_screenshot_byte_drift(monkeypatch):
    client = FakeClient()
    _install_image_readback(monkeypatch, client, target_bytes=b"different-screenshot")

    with pytest.raises(ValueError, match="screenshot bytes differ"):
        hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)


def test_copied_board_readback_rejects_missing_connector(monkeypatch):
    client = FakeClient()
    _install_image_readback(monkeypatch, client)
    client.connectors["hvr"].pop()

    with pytest.raises(ValueError, match="connector count differs"):
        hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)


def test_human_visual_status_is_not_promoted_by_technical_endpoint_pass(monkeypatch):
    client = FakeClient()
    _install_image_readback(monkeypatch, client)
    report = hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)

    assert report["ENDPOINT_GEOMETRY_MATCH"] == "PASS"
    assert report["HUMAN_VISUAL_ACCEPTANCE"] == "PENDING"
    assert report["miro_tips"]["status"] == "PASS"
    assert "VISUAL_EQUIVALENCE_PASS" not in report
