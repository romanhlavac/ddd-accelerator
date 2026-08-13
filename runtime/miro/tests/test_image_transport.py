from __future__ import annotations

from ddda_miro.image_transport import reconcile


class FakeClient:
    access_token = "token"
    timeout_seconds = 5

    def __init__(self):
        self.images = []
        self.calls = []

    def list_items(self, board, item_type=None):
        return list(self.images)

    def _prepare_item_payload(self, board, item_type, payload):
        prepared = {key: value for key, value in payload.items() if key != "_ddda_bounds_geometry"}
        prepared["position"] = {"x": 1400.0, "y": 950.0, "origin": "center"}
        return prepared

    def _request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        if method == "GET":
            return {"id": "source-image", "type": "image", "parent": {"id": "source-frame"}, "geometry": {"width": 1000, "height": 500}, "data": {"imageUrl": "https://api.miro.com/resource"}}
        if method == "POST":
            remote = {"id": "target-image", "type": "image", **kwargs["body"]}
            self.images.append(remote)
            return remote
        if method == "PATCH":
            remote = {"id": "target-image", "type": "image", **kwargs["body"]}
            self.images[0] = remote
            return remote
        raise AssertionError((method, path))


def manifest():
    return {"manifest_id": "test", "diagnostic_only": True, "assets": [{"id": "asset", "source": {"board_id": "source-board", "frame_id": "source-frame", "item_id": "source-image", "title": "Source"}, "target": {"frame_id": "target", "position": {"x": 0, "y": 0}, "width": 2200}, "usage": "test"}]}


def test_reconcile_is_idempotent(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("ddda_miro.image_transport._read", lambda url, token, timeout: (b"image", "image/png"))

    first = reconcile(client, "board", {"target": "frame"}, manifest())
    second = reconcile(client, "board", {"target": "frame"}, manifest())

    assert first["created"] == 1
    assert second["unchanged"] == 1
    assert second["created"] == second["updated"] == 0
    assert first["assets"][0]["target_item_id"] == second["assets"][0]["target_item_id"]
    assert [call[0] for call in client.calls].count("POST") == 1
