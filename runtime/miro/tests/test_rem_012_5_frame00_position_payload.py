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


class _ReplacementClient:
    def __init__(self, *, legacy_children: int = 8):
        self.frames = {
            "legacy": {
                "id": "legacy",
                "data": {"title": "00 – Control"},
                "style": {"fillColor": "#f8fafc"},
                "geometry": {"width": 9000.0, "height": 8000.0},
                "position": {"x": -17000.0, "y": 1000.0, "origin": "center"},
                "parent": None,
            }
        }
        self.children = {
            "legacy": [
                {"id": f"legacy-child-{i}", "_accepted": True}
                for i in range(legacy_children)
            ]
        }
        self.events = []
        self.next_frame = 1
        self.next_child = 1

    def list_items(self, board, item_type=None):
        assert board == "target"
        if item_type == "frame":
            return [dict(frame) for frame in self.frames.values()]
        return []

    def create_item(self, board, item_type, payload):
        assert board == "target" and item_type == "frame"
        frame_id = f"replacement-{self.next_frame}"
        self.next_frame += 1
        frame = {
            "id": frame_id,
            "data": dict(payload.get("data") or {}),
            "style": dict(payload.get("style") or {}),
            "geometry": dict(payload["geometry"]),
            "position": dict(payload["position"]),
            "parent": None,
        }
        self.frames[frame_id] = frame
        self.children[frame_id] = []
        self.events.append(
            f"create_frame:{frame_id}:{frame['position']['x']}:{frame['position']['y']}"
        )
        return dict(frame)

    def update_item(self, *_args, **_kwargs):
        raise AssertionError("Frame 00 replacement must never PATCH a frame")

    def delete_item(self, board, item_id):
        assert board == "target"
        for frame_id, children in list(self.children.items()):
            for child in list(children):
                if child["id"] == item_id:
                    children.remove(child)
                    self.events.append(f"delete_child:{item_id}")
                    return
        if item_id in self.frames:
            self.frames.pop(item_id)
            self.children.pop(item_id, None)
            self.events.append(f"delete_frame:{item_id}")
            return
        raise AssertionError(f"unknown delete item {item_id}")

    def delete_connector(self, *_args):
        raise AssertionError("replacement fixture has no connectors")

    def _request(self, method, path, body=None):
        if method == "POST":
            parent = str((body.get("parent") or {}).get("id") or "")
            assert parent in self.frames and parent != "legacy"
            child_id = f"new-child-{self.next_child}"
            self.next_child += 1
            child = {"id": child_id, "_accepted": True, "_expected": body}
            self.children[parent].append(child)
            self.events.append(f"create_child:{parent}:{child_id}")
            return {"id": child_id}
        if method == "GET" and "/items/" in path:
            item_id = path.rsplit("/", 1)[-1]
            for frame_id, children in self.children.items():
                for child in children:
                    if child["id"] == item_id:
                        self.events.append(f"read_child:{frame_id}:{item_id}")
                        return dict(child)
            raise AssertionError(f"unknown child {item_id}")
        if method == "PATCH":
            raise AssertionError("replacement fixture should not patch child payloads")
        raise AssertionError(f"unexpected request: {method} {path}")


def _replacement_manifest():
    return {
        "board_id": "target",
        "frame00_id": "legacy",
        "frame_id": "frame01",
        "frame00_sticky_colors": {},
        "frame00_replacement": {
            "policy": "discover_verified_or_replace_legacy_container",
            "legacy_frame_id": "legacy",
            "title": "00 – Control",
            "target_top_left": {"x": -21500.0, "y": -3000.0},
            "staging_center": {"x": -28000.0, "y": -542.79},
            "fill_color": "#f8fafc",
        },
    }


def _replacement_contract():
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


def _wire_replacement_fixture(monkeypatch, client, contract):
    def fake_get_frame(_client, board, frame_id):
        assert board == "target"
        return dict(client.frames[frame_id])

    def fake_children(_client, board, frame_id):
        assert board == "target"
        return [dict(item) for item in client.children.get(frame_id, [])]

    def role_mapping(frame_id):
        return {
            update["role"]: client.children[frame_id][i]["id"]
            for i, update in enumerate(contract["managed_updates"])
        }

    def fake_items_state(_client, manifest, _contract):
        frame_id = str(manifest["frame00_id"])
        children = client.children.get(frame_id, [])
        if len(children) != 8 or not all(item.get("_accepted") for item in children):
            return False, {}
        return True, role_mapping(frame_id)

    def fake_container_state(_client, manifest, _contract):
        frame_id = str(manifest["frame00_id"])
        frame = client.frames.get(frame_id)
        if frame is None:
            return False, {}
        items_ok, mapping = fake_items_state(_client, manifest, _contract)
        if not items_ok:
            return False, {}
        if frame["geometry"] != {"width": 7000.0, "height": 4914.42}:
            return False, {}
        return True, mapping

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


def _install_verified_frame(client, frame_id, x, y):
    client.frames[frame_id] = {
        "id": frame_id,
        "data": {"title": "00 – Control"},
        "style": {"fillColor": "#f8fafc"},
        "geometry": {"width": 7000.0, "height": 4914.42},
        "position": {"x": x, "y": y, "origin": "center"},
        "parent": None,
    }
    client.children[frame_id] = [
        {"id": f"{frame_id}-child-{i}", "_accepted": True}
        for i in range(8)
    ]


def test_frame00_two_copy_swap_has_no_frame_patch_and_deletes_legacy_only_after_staging_verified(monkeypatch):
    client = _ReplacementClient(legacy_children=8)
    manifest = _replacement_manifest()
    contract = _replacement_contract()
    _wire_replacement_fixture(monkeypatch, client, contract)

    result = wirefix.restore_frame00_accepted_geometry_preserve_top_left(
        client, manifest, contract
    )

    final_id = manifest["frame00_id"]
    assert final_id == "replacement-2"
    assert set(client.frames) == {"replacement-2"}
    assert client.frames[final_id]["geometry"] == {
        "width": 7000.0,
        "height": 4914.42,
    }
    assert client.frames[final_id]["position"] == {
        "x": -18000.0,
        "y": -542.79,
        "origin": "center",
    }

    staging_create = client.events.index("create_frame:replacement-1:-28000.0:-542.79")
    staging_reads = [
        i for i, event in enumerate(client.events)
        if event.startswith("read_child:replacement-1:")
    ]
    legacy_delete = client.events.index("delete_frame:legacy")
    final_create = client.events.index("create_frame:replacement-2:-18000.0:-542.79")
    final_reads = [
        i for i, event in enumerate(client.events)
        if event.startswith("read_child:replacement-2:")
    ]
    staging_delete = client.events.index("delete_frame:replacement-1")

    assert staging_create < min(staging_reads)
    assert max(staging_reads[:8]) < legacy_delete < final_create
    assert final_create < min(final_reads)
    assert max(final_reads[:8]) < staging_delete
    assert result["container_replaced"] == 1
    assert result["legacy_container_deleted"] == 1
    assert result["staging_container_deleted"] == 1
    assert result["replacement_frame_id"] == "replacement-2"
    assert result["container_resized"] == 0
    assert result["container_moved"] == 0

    mutations_before = [
        event for event in client.events
        if event.startswith(("create_", "delete_"))
    ]
    second = wirefix.restore_frame00_accepted_geometry_preserve_top_left(
        client, manifest, contract
    )
    mutations_after = [
        event for event in client.events
        if event.startswith(("create_", "delete_"))
    ]
    assert mutations_after == mutations_before
    assert second["created"] == 0
    assert second["deleted"] == 0
    assert second["updated"] == 0
    assert second["unchanged"] == 8


def test_frame00_cross_process_run_rediscovers_verified_final_replacement(monkeypatch):
    client = _ReplacementClient(legacy_children=8)
    manifest = _replacement_manifest()
    contract = _replacement_contract()
    _wire_replacement_fixture(monkeypatch, client, contract)

    wirefix.restore_frame00_accepted_geometry_preserve_top_left(
        client, manifest, contract
    )
    final_id = manifest["frame00_id"]
    mutations_before = [
        event for event in client.events
        if event.startswith(("create_", "delete_"))
    ]

    fresh_manifest = _replacement_manifest()
    second = wirefix.restore_frame00_accepted_geometry_preserve_top_left(
        client, fresh_manifest, contract
    )
    mutations_after = [
        event for event in client.events
        if event.startswith(("create_", "delete_"))
    ]
    assert fresh_manifest["frame00_id"] == final_id
    assert mutations_after == mutations_before
    assert second["replacement_reused"] == 1
    assert second["unchanged"] == 8


def test_frame00_partial_legacy_fails_closed_before_staging_creation(monkeypatch):
    client = _ReplacementClient(legacy_children=3)
    manifest = _replacement_manifest()
    contract = _replacement_contract()
    _wire_replacement_fixture(monkeypatch, client, contract)

    with pytest.raises(ValueError, match="partially populated"):
        wirefix.restore_frame00_accepted_geometry_preserve_top_left(
            client, manifest, contract
        )
    assert client.events == []
    assert set(client.frames) == {"legacy"}


def test_frame00_verified_staging_resumes_after_partial_legacy_cleanup(monkeypatch):
    client = _ReplacementClient(legacy_children=3)
    contract = _replacement_contract()
    manifest = _replacement_manifest()
    _install_verified_frame(client, "replacement-1", -28000.0, -542.79)
    client.next_frame = 2
    _wire_replacement_fixture(monkeypatch, client, contract)

    result = wirefix.restore_frame00_accepted_geometry_preserve_top_left(
        client, manifest, contract
    )

    assert manifest["frame00_id"] == "replacement-2"
    assert set(client.frames) == {"replacement-2"}
    assert result["replacement_reused"] == 1
    assert result["legacy_container_deleted"] == 1
    assert result["staging_container_deleted"] == 1
    assert client.frames["replacement-2"]["position"]["x"] == -18000.0


def test_frame00_verified_final_finishes_deferred_cleanup_without_recreation(monkeypatch):
    client = _ReplacementClient(legacy_children=3)
    contract = _replacement_contract()
    manifest = _replacement_manifest()
    _install_verified_frame(client, "replacement-final", -18000.0, -542.79)
    _install_verified_frame(client, "replacement-stage", -28000.0, -542.79)
    _wire_replacement_fixture(monkeypatch, client, contract)

    result = wirefix.restore_frame00_accepted_geometry_preserve_top_left(
        client, manifest, contract
    )

    assert manifest["frame00_id"] == "replacement-final"
    assert set(client.frames) == {"replacement-final"}
    assert result["replacement_reused"] == 1
    assert result["legacy_container_deleted"] == 1
    assert result["staging_container_deleted"] == 1
    assert not any(event.startswith("create_frame:") for event in client.events)


def test_frame00_target_envelope_is_checked_before_external_mutation(monkeypatch):
    client = _ReplacementClient(legacy_children=8)
    manifest = _replacement_manifest()
    contract = _replacement_contract()
    contract["managed_updates"][-1]["x"] = 6900.0
    contract["managed_updates"][-1]["width"] = 500.0
    _wire_replacement_fixture(monkeypatch, client, contract)

    with pytest.raises(ValueError, match="does not fit accepted"):
        wirefix.restore_frame00_accepted_geometry_preserve_top_left(
            client, manifest, contract
        )
    assert client.events == []
