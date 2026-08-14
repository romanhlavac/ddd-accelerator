from __future__ import annotations

from copy import deepcopy

import pytest

from ddda_miro import hvr_materialization as hvr
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
    return rows


def _connectors(prefix: str) -> list[dict]:
    return [
        {
            "id": f"{prefix}-connector-{index}",
            "startItem": {"id": f"{prefix}-sticky-{index}"},
            "endItem": {
                "id": f"{prefix}-image",
                "position": {"x": 0.10 + index * 0.05, "y": 0.20 + index * 0.03},
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


def test_copied_board_readback_proves_native_exact_reference_and_hvr_gate(monkeypatch):
    client = FakeClient()
    _install_image_readback(monkeypatch, client)
    report = hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)

    assert report["technical_status"] == "PASS"
    assert report["human_review_status"] == "PENDING"
    assert report["overall_status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["miro_tips"]["policy"] == tips.MIRO_TIPS_VISUAL_EQUIVALENCE_POLICY
    assert report["miro_tips"]["item_count"] == 17
    assert report["miro_tips"]["item_type_counts"] == tips.EXPECTED_ITEM_TYPE_COUNTS
    assert report["miro_tips"]["connector_count"] == 8
    assert report["miro_tips"]["image"]["source_sha256"] == report["miro_tips"]["image"]["target_sha256"]
    assert report["merge_allowed"] is False


def test_copied_board_readback_rejects_font_drift(monkeypatch):
    client = FakeClient()
    _install_image_readback(monkeypatch, client)
    target = next(item for item in client.items["hvr"] if item.get("id") == "hvr-text-0")
    target["style"]["fontSize"] = 24

    with pytest.raises(ValueError, match="native item differs"):
        hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)


def test_copied_board_readback_rejects_arrowhead_endpoint_drift(monkeypatch):
    client = FakeClient()
    _install_image_readback(monkeypatch, client)
    client.connectors["hvr"][0]["endItem"]["position"] = {"x": 0.9, "y": 0.9}

    with pytest.raises(ValueError, match="connector differs"):
        hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)


def test_copied_board_readback_rejects_screenshot_byte_drift(monkeypatch):
    client = FakeClient()
    _install_image_readback(monkeypatch, client, target_bytes=b"different-screenshot")

    with pytest.raises(ValueError, match="screenshot bytes differ"):
        hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)


def test_copied_board_readback_rejects_missing_native_connector(monkeypatch):
    client = FakeClient()
    _install_image_readback(monkeypatch, client)
    client.connectors["hvr"].pop()

    with pytest.raises(ValueError, match="connector count differs"):
        hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)
