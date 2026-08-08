import pytest

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
        self.children = []
        self.events = []
        self.update_payloads = []
        self.atomic_patch_applied = False
        self.resize_read_back = False

    def delete_connector(self, *_args):
        raise AssertionError("accepted Frame 00 fixture has no connectors")

    def delete_item(self, *_args):
        raise AssertionError("FAST-LOOP recovery must not delete accepted Frame 00 children")

    def _request(self, method, path, body=None):
        if method == "POST":
            assert path == "boards/target/texts"
            item_id = f"new-{len(self.children)}"
            item = {"id": item_id, "_expected": body}
            self.children.append(item)
            self.events.append(f"create:{item_id}")
            return {"id": item_id}
        if method == "GET" and "/items/" in path:
            item_id = path.rsplit("/", 1)[-1]
            item = next(item for item in self.children if item["id"] == item_id)
            if not self.atomic_patch_applied:
                self.events.append(f"child_readback:{item_id}")
            return dict(item)
        if method == "PATCH":
            raise AssertionError("accepted child payloads should not need reapply in this fixture")
        raise AssertionError(f"unexpected request: {method} {path}")

    def update_item(self, board, item_type, item_id, payload):
        assert board == "target" and item_type == "frame" and item_id == "frame00"
        assert len(self.children) == 8
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


def _ordering_manifest():
    return {
        "board_id": "target",
        "frame00_id": "frame00",
        "frame_id": "frame01",
        "frame00_sticky_colors": {},
    }


def _ordering_contract():
    return {
        "frame": {"width": 7000.0, "height": 4914.42},
        "managed_updates": [
            {
                "role": f"role-{i}",
                "type": "text",
                "x": 500.0 + i * 800.0,
                "y": 500.0 + (i % 2) * 700.0,
                "width": 500.0,
                "visual_height": 300.0,
                "font_size": 48,
                "content": f"<p>role-{i}</p>",
            }
            for i in range(8)
        ],
    }


def _wire_ordering_fixture(monkeypatch, client, contract):
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

    def role_mapping():
        return {
            update["role"]: client.children[i]["id"]
            for i, update in enumerate(contract["managed_updates"])
        }

    def fake_items_state(*_args):
        if len(client.children) != 8:
            return False, {}
        return True, role_mapping()

    def fake_container_state(*_args):
        if (
            len(client.children) == 8
            and client.frame["geometry"] == {"width": 7000.0, "height": 4914.42}
        ):
            return True, role_mapping()
        return False, {}

    monkeypatch.setattr(wirefix.base, "_get_frame", fake_get_frame)
    monkeypatch.setattr(wirefix.base, "_children", fake_children)
    monkeypatch.setattr(wirefix.base, "_related_connectors", lambda *_args: [])
    monkeypatch.setattr(wirefix, "_frame00_items_state", fake_items_state)
    monkeypatch.setattr(wirefix, "frame00_state_accepted_container", fake_container_state)
    monkeypatch.setattr(
        wirefix,
        "same_item",
        lambda remote, expected: remote.get("_expected") == expected,
    )


def test_frame00_creates_accepted_children_before_single_atomic_resize(monkeypatch):
    client = _OrderingClient()
    manifest = _ordering_manifest()
    contract = _ordering_contract()
    _wire_ordering_fixture(monkeypatch, client, contract)

    result = wirefix.restore_frame00_accepted_geometry_preserve_top_left(
        client, manifest, contract
    )

    create_indexes = [i for i, event in enumerate(client.events) if event.startswith("create:")]
    readback_indexes = [
        i for i, event in enumerate(client.events) if event.startswith("child_readback:")
    ]
    assert len(create_indexes) == 8
    assert len(readback_indexes) == 8
    assert max(readback_indexes) < client.events.index("atomic_resize")
    assert client.events.index("atomic_resize") < client.events.index("resize_readback")
    assert len(client.update_payloads) == 1
    assert client.frame["geometry"] == {"width": 7000.0, "height": 4914.42}
    assert abs(client.frame["position"]["x"] - (-18000.0)) < 0.001
    assert abs(client.frame["position"]["y"] - (-542.79)) < 0.001
    assert result["created"] == 8
    assert result["deleted"] == 0
    assert result["connectors_deleted"] == 0
    assert result["container_resized"] == 1
    assert result["container_moved"] == 1
    assert result["top_left_preserved"] is True

    events_before_second_run = list(client.events)
    second = wirefix.restore_frame00_accepted_geometry_preserve_top_left(
        client, manifest, contract
    )
    assert client.events == events_before_second_run
    assert second["created"] == 0
    assert second["deleted"] == 0
    assert second["updated"] == 0
    assert second["unchanged"] == 8
    assert second["container_resized"] == 0


def test_frame00_partial_populated_state_fails_closed_without_mutation(monkeypatch):
    client = _OrderingClient()
    client.children = [{"id": "partial", "_expected": {}}]
    manifest = _ordering_manifest()
    contract = _ordering_contract()

    monkeypatch.setattr(
        wirefix,
        "frame00_state_accepted_container",
        lambda *_args: (False, {}),
    )
    monkeypatch.setattr(wirefix.base, "_get_frame", lambda *_args: dict(client.frame))
    monkeypatch.setattr(wirefix.base, "_children", lambda *_args: list(client.children))

    with pytest.raises(ValueError, match="partially populated"):
        wirefix.restore_frame00_accepted_geometry_preserve_top_left(
            client, manifest, contract
        )
    assert client.events == []
    assert client.update_payloads == []


def test_frame00_target_envelope_is_checked_before_external_mutation(monkeypatch):
    client = _OrderingClient()
    manifest = _ordering_manifest()
    contract = _ordering_contract()
    contract["managed_updates"][-1]["x"] = 6900.0
    contract["managed_updates"][-1]["width"] = 500.0

    monkeypatch.setattr(
        wirefix,
        "frame00_state_accepted_container",
        lambda *_args: (False, {}),
    )

    with pytest.raises(ValueError, match="does not fit accepted"):
        wirefix.restore_frame00_accepted_geometry_preserve_top_left(
            client, manifest, contract
        )
    assert client.events == []
    assert client.update_payloads == []
