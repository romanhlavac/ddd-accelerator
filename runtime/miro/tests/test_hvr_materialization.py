from __future__ import annotations

import hashlib
from copy import deepcopy

from ddda_miro import hvr_materialization as hvr
from ddda_miro import miro_tips_hvr_fix as tips


class FakeClient:
    def __init__(self) -> None:
        self.items = {
            "platform": [
                {"id": "platform-frame", "type": "frame", "data": {"title": "Miro Tips"}},
                {"id": "platform-image", "type": "image", "parent": {"id": "platform-frame"}},
                {"id": "platform-text", "type": "text", "data": {"content": "unchanged"}},
            ],
            "hvr": [
                {"id": "hvr-frame", "type": "frame", "data": {"title": "Miro Tips"}},
                {
                    "id": "hvr-image",
                    "type": "image",
                    "parent": {"id": "hvr-frame"},
                    "data": {"title": tips._target_title()},
                },
                {"id": "hvr-text", "type": "text", "data": {"content": "unchanged"}},
            ],
        }
        self.connectors = {"platform": [], "hvr": []}

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


def test_copied_board_readback_proves_the_single_composite_and_hvr_gate(monkeypatch):
    client = FakeClient()
    raw = tips._composite_bytes()

    def source_image(_client, board, item_id):
        assert board == "hvr"
        assert item_id == "hvr-image"
        return raw, "image/png", deepcopy(client.items["hvr"][1])

    monkeypatch.setattr(hvr.image_transport, "source_image", source_image)
    report = hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)

    assert report["technical_status"] == "PASS"
    assert report["human_review_status"] == "PENDING"
    assert report["overall_status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["miro_tips"]["connector_count"] == 0
    assert report["miro_tips"]["composite_sha256"] == hashlib.sha256(raw).hexdigest()
    assert report["merge_allowed"] is False


def test_copied_board_readback_rejects_native_connector(monkeypatch):
    client = FakeClient()
    client.connectors["hvr"] = [{"startItem": {"id": "hvr-image"}, "endItem": {"id": "other"}}]
    monkeypatch.setattr(
        hvr.image_transport,
        "source_image",
        lambda *_args: (tips._composite_bytes(), "image/png", deepcopy(client.items["hvr"][1])),
    )

    try:
        hvr.copied_board_readback(client, "platform", "hvr", "a" * 40)
    except ValueError as exc:
        assert "must not contain native connectors" in str(exc)
    else:
        raise AssertionError("expected native-connector rejection")
