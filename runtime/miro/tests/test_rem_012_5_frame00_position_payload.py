import ddda_miro.frame00_resize_ordering_wirefix as wirefix

from ddda_miro.review_board_recovery_wirefix import (
    companion_frame_payload,
    frame00_container_payload_preserve_top_left,
    frame00_payload,
    frame01_replacement_payload,
    readable_connector_payload,
    readable_frame01_item_payload,
)


def test_frame00_create_payload_omits_read_only_relative_to_metadata():
    manifest = {
        "board_id": "uXjVH0doLYY=",
        "frame_id": "frame01",
        "frame00_sticky_colors": {
            "phase_gate_state": "light_yellow",
            "owner_next_action": "light_blue",
            "attention_blockers": "light_green",
        },
    }
    update = {
        "role": "decision_now",
        "type": "text",
        "x": 3500,
        "y": 850,
        "width": 5600,
        "font_size": 36,
        "content": "<p><strong>ROZHODNUTÍ NYNÍ</strong></p>",
    }
    payload = frame00_payload(update, "frame00", manifest)
    assert payload["parent"] == {"id": "frame00"}
    assert payload["position"] == {"x": 3500.0, "y": 850.0, "origin": "center"}
    assert "relativeTo" not in payload["position"]


def test_frame01_replacement_uses_redline_geometry_and_preserves_old_top_left():
    old_frame = {
        "data": {"title": "01 – DDD Starter journey, gates a iterace"},
        "geometry": {"width": 58000.0, "height": 13000.0},
        "position": {"x": 8000.0, "y": -7500.0, "origin": "center"},
        "style": {"fillColor": "#ffffff"},
    }
    source_frame = {
        "data": {"title": "01 – DDD Starter journey, gates a iterace"},
        "geometry": {"width": 58008.9, "height": 10144.3},
        "position": {"x": 0.0, "y": 0.0, "origin": "center"},
        "style": {"fillColor": "#ffffff"},
    }
    payload = frame01_replacement_payload(old_frame, source_frame)
    assert payload["geometry"] == {"width": 58008.9, "height": 10144.3}
    assert abs(payload["position"]["x"] - 8004.45) < 0.001
    assert abs(payload["position"]["y"] - (-8927.85)) < 0.001
    old_left = old_frame["position"]["x"] - old_frame["geometry"]["width"] / 2
    old_top = old_frame["position"]["y"] - old_frame["geometry"]["height"] / 2
    new_left = payload["position"]["x"] - payload["geometry"]["width"] / 2
    new_top = payload["position"]["y"] - payload["geometry"]["height"] / 2
    assert abs(old_left - new_left) < 0.001
    assert abs(old_top - new_top) < 0.001
    assert payload["style"]["fillColor"] == "#ffffff"


def test_frame00_accepted_resize_preserves_canvas_top_left():
    current = {
        "geometry": {"width": 9000.0, "height": 8000.0},
        "position": {"x": -17000.0, "y": 1000.0, "origin": "center"},
    }
    payload = frame00_container_payload_preserve_top_left(current, 7000.0, 4914.42)
    assert payload["geometry"] == {"width": 7000.0, "height": 4914.42}
    assert abs(payload["position"]["x"] - (-18000.0)) < 0.001
    assert abs(payload["position"]["y"] - (-542.79)) < 0.001
    old_left = current["position"]["x"] - current["geometry"]["width"] / 2
    old_top = current["position"]["y"] - current["geometry"]["height"] / 2
    new_left = payload["position"]["x"] - payload["geometry"]["width"] / 2
    new_top = payload["position"]["y"] - payload["geometry"]["height"] / 2
    assert abs(old_left - new_left) < 0.001
    assert abs(old_top - new_top) < 0.001


def test_companion_frame_preserves_reference_offset_from_main_journey():
    source_main = {"position": {"x": 9076.78, "y": -8458.92}}
    target_main = {"position": {"x": 8004.426, "y": -8927.845}}
    source_align = {
        "data": {"title": "Align"},
        "geometry": {"width": 1583.26, "height": 890.156},
        "position": {"x": -15623.039, "y": -9826.156},
        "style": {"fillColor": "#e0e7ee"},
    }
    payload = companion_frame_payload(source_align, source_main, target_main)
    assert payload["data"]["title"] == "Align"
    assert payload["geometry"] == {"width": 1583.26, "height": 890.156}
    assert abs(
        (payload["position"]["x"] - target_main["position"]["x"])
        - (source_align["position"]["x"] - source_main["position"]["x"])
    ) < 0.001
    assert abs(
        (payload["position"]["y"] - target_main["position"]["y"])
        - (source_align["position"]["y"] - source_main["position"]["y"])
    ) < 0.001


def test_methodology_payload_is_uplifted_to_readable_contract():
    source = {
        "id": "methodology",
        "type": "text",
        "data": {"content": "<p><strong>METODIKA A ZDROJE</strong></p><p>link</p>"},
        "position": {"x": 556.0, "y": 769.0},
        "geometry": {"width": 701.0, "height": 300.0},
        "style": {
            "fontFamily": "arial",
            "fontSize": 23,
            "textAlign": "left",
            "color": "#365a8c",
        },
    }
    manifest = {
        "readability": {
            "methodology_min_font_size": 80,
            "methodology_width": 4800,
            "methodology_x": 2600,
            "methodology_y": 850,
        }
    }
    payload = readable_frame01_item_payload(source, "target-frame", manifest)
    assert payload["style"]["fontSize"] >= 80
    assert payload["geometry"]["width"] == 4800.0
    assert payload["position"]["x"] == 2600.0
    assert payload["position"]["y"] == 850.0


def test_connector_payload_preserves_endpoint_layout_and_enforces_readable_caption():
    source = {
        "startItem": {"id": "s", "snapTo": "right", "position": {"x": 1.0, "y": 0.5}},
        "endItem": {"id": "e", "snapTo": "left", "position": {"x": 0.0, "y": 0.5}},
        "shape": "curved",
        "style": {
            "strokeColor": "#365a8c",
            "strokeStyle": "normal",
            "strokeWidth": 2,
            "fontSize": 14,
            "color": "#1a1a1a",
            "textOrientation": "aligned",
        },
        "captions": [{"content": "přechod mezi fázemi", "position": "50%"}],
    }
    payload = readable_connector_payload(
        source,
        "target-start",
        "target-end",
        {"readability": {"connector_caption_min_font_size": 48}},
    )
    assert payload["startItem"]["position"] == {"x": 1.0, "y": 0.5}
    assert payload["endItem"]["position"] == {"x": 0.0, "y": 0.5}
    assert payload["startItem"]["snapTo"] == "right"
    assert payload["endItem"]["snapTo"] == "left"
    assert payload["style"]["fontSize"] >= 48
    assert payload["style"]["color"] == "#1a1a1a"
    assert payload["style"]["textOrientation"] == "horizontal"


class _OrderingClient:
    def __init__(self):
        self.frame = {
            "id": "frame00",
            "geometry": {"width": 9000.0, "height": 8000.0},
            "position": {"x": -17000.0, "y": 1000.0, "origin": "center"},
        }
        self.children = [{"id": f"child-{i}"} for i in range(8)]
        self.events = []
        self.update_payloads = []
        self.atomic_patch_applied = False
        self.resize_read_back = False

    def delete_connector(self, *_args):
        raise AssertionError("accepted Frame 00 fixture has no connectors")

    def delete_item(self, board, item_id):
        assert board == "target"
        self.events.append(f"delete:{item_id}")
        self.children = [item for item in self.children if item["id"] != item_id]

    def update_item(self, board, item_type, item_id, payload):
        assert board == "target" and item_type == "frame" and item_id == "frame00"
        assert set(payload) == {"geometry", "position"}
        assert payload["geometry"] == {"width": 7000.0, "height": 4914.42}
        assert abs(payload["position"]["x"] - (-18000.0)) < 0.001
        assert abs(payload["position"]["y"] - (-542.79)) < 0.001
        self.events.append("atomic_resize")
        self.update_payloads.append(payload)
        self.atomic_patch_applied = True
        self.frame["geometry"] = dict(payload["geometry"])
        self.frame["position"] = dict(payload["position"])
        return dict(self.frame)


def test_frame00_empty_shrink_happens_before_recreate_and_preserves_top_left(monkeypatch):
    client = _OrderingClient()
    manifest = {"board_id": "target", "frame00_id": "frame00"}
    contract = {"frame": {"width": 7000.0, "height": 4914.42}, "managed_updates": [{}] * 8}

    def fake_get_frame(_client, board, frame_id):
        assert board == "target" and frame_id == "frame00"
        if client.atomic_patch_applied and not client.resize_read_back:
            client.events.append("resize_readback")
            client.resize_read_back = True
        return {
            "id": client.frame["id"],
            "geometry": dict(client.frame["geometry"]),
            "position": dict(client.frame["position"]),
        }

    def fake_children(_client, board, frame_id):
        assert board == "target" and frame_id == "frame00"
        return [dict(item) for item in client.children]

    def fake_wait_empty(_client, board, frame_id):
        assert board == "target" and frame_id == "frame00"
        assert client.children == []
        client.events.append("empty")

    helper_calls = []

    def fake_atomic_payload(frame, target_width, target_height):
        helper_calls.append((dict(frame), target_width, target_height))
        return frame00_container_payload_preserve_top_left(frame, target_width, target_height)

    def fake_restore(_client, _manifest, _contract):
        assert len(client.update_payloads) == 1
        assert client.resize_read_back is True
        assert client.children == []
        assert client.frame["geometry"] == {"width": 7000.0, "height": 4914.42}
        client.events.append("recreate")
        client.children = [{"id": f"new-{i}"} for i in range(8)]
        return {
            "created": 8,
            "deleted": 0,
            "connectors_deleted": 0,
            "unchanged": 0,
            "role_ids": {"accepted": "ids"},
        }

    monkeypatch.setattr(wirefix.base, "_get_frame", fake_get_frame)
    monkeypatch.setattr(wirefix.base, "_children", fake_children)
    monkeypatch.setattr(wirefix.base, "_related_connectors", lambda *_args: [])
    monkeypatch.setattr(wirefix.base, "_wait_frame_empty", fake_wait_empty)
    monkeypatch.setattr(
        wirefix.wirefix,
        "frame00_container_payload_preserve_top_left",
        fake_atomic_payload,
    )
    monkeypatch.setattr(wirefix, "_frame00_items_state", lambda *_args: (True, {"accepted": "old"}))
    monkeypatch.setattr(wirefix, "_ORIGINAL_RESTORE_FRAME00", fake_restore)
    monkeypatch.setattr(
        wirefix,
        "frame00_state_accepted_container",
        lambda *_args: (
            (True, {"accepted": "ids"})
            if len(client.children) == 8 and client.frame["geometry"]["width"] == 7000.0
            else (False, {})
        ),
    )

    result = wirefix.restore_frame00_accepted_geometry_preserve_top_left(client, manifest, contract)

    delete_indexes = [i for i, event in enumerate(client.events) if event.startswith("delete:")]
    assert len(delete_indexes) == 8
    assert max(delete_indexes) < client.events.index("empty")
    assert client.events.index("empty") < client.events.index("atomic_resize")
    assert client.events.index("atomic_resize") < client.events.index("resize_readback")
    assert client.events.index("resize_readback") < client.events.index("recreate")
    assert len(client.update_payloads) == 1
    assert len(helper_calls) == 1
    assert client.frame["geometry"] == {"width": 7000.0, "height": 4914.42}
    assert abs(client.frame["position"]["x"] - (-18000.0)) < 0.001
    assert abs(client.frame["position"]["y"] - (-542.79)) < 0.001
    assert result["created"] == 8
    assert result["deleted"] == 8
    assert result["container_resized"] == 1
    assert result["container_moved"] == 1
    assert result["top_left_preserved"] is True
