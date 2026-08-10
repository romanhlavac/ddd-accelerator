from __future__ import annotations

from copy import deepcopy

from ddda_miro import miro_tips_hvr_fix as tips


def manifest():
    return {
        "source_frame_id": "source-main",
        "frame_id": "target-main",
        "source_companion_frames": [
            {
                "id": "source-tips",
                "title": "Miro Tips",
                "min_images": 1,
                "mode": tips.MIRO_TIPS_MODE,
            }
        ],
        "miro_tips": {
            "min_images": 1,
            "min_connectors": 8,
            "container_policy": tips.MIRO_TIPS_CONTAINER_POLICY,
            "readback_attempts": 4,
            "readback_delay_seconds": 0,
            "required_markers": list(tips.DEFAULT_REQUIRED_MARKERS),
        },
    }


def frame(frame_id, title, x, y, width, height):
    return {
        "id": frame_id,
        "type": "frame",
        "data": {"title": title},
        "position": {"x": x, "y": y},
        "geometry": {"width": width, "height": height},
        "style": {"fillColor": "#ffffff"},
    }


def test_miro_tips_frame_payload_preserves_reference_geometry_and_relative_placement():
    source_main = frame("source-main", "01 – DDD Starter journey, gates a iterace", 9076.78, -8458.92, 58008.9, 10144.3)
    target_main = frame("target-main", "01 – DDD Starter journey, gates a iterace", 8004.426, -8927.845, 58008.9, 10144.3)
    source_tips = frame("source-tips", "Miro Tips", -18762.093, -11858.608, 1919.43, 1079.68)

    payload = tips.miro_tips_companion_frame_payload(
        source_tips, source_main, target_main, manifest()
    )

    assert payload["geometry"] == {"width": 1919.43, "height": 1079.68}
    assert abs(payload["position"]["x"] - (-19834.447)) < 0.01
    assert abs(payload["position"]["y"] - (-12327.533)) < 0.01
    assert tips.desired_miro_tips_items("target-tips", manifest()) == []


def test_miro_tips_outer_frame_comparison_defers_irreducible_container_patch(monkeypatch):
    remote = frame("target-tips", "Miro Tips", -19834.447, -12327.533, 4600, 2600)
    expected = frame("target-tips", "Miro Tips", -19834.447, -12327.533, 1919.43, 1079.68)
    monkeypatch.setattr(tips, "_ORIGINAL_SAME_FRAME", lambda left, right: left == right)

    assert tips.same_frame_defer_miro_tips(remote, expected) is True

    other_remote = frame("x", "Align", 1, 1, 10, 10)
    other_expected = frame("x", "Align", 1, 1, 20, 10)
    assert tips.same_frame_defer_miro_tips(other_remote, other_expected) is False


class FakeClient:
    def __init__(self):
        self.frames = {
            ("source", "source-main"): frame("source-main", "01 – DDD Starter journey, gates a iterace", 9076.78, -8458.92, 58008.9, 10144.3),
            ("target", "target-main"): frame("target-main", "01 – DDD Starter journey, gates a iterace", 8004.426, -8927.845, 58008.9, 10144.3),
            ("source", "source-tips"): frame("source-tips", "Miro Tips", -18762.093, -11858.608, 1919.43, 1079.68),
            ("target", "target-tips"): frame("target-tips", "Miro Tips", -19834.447, -12327.533, 4600, 2600),
        }
        self.next_frame = 1
        all_markers = " | ".join(tips.DEFAULT_REQUIRED_MARKERS)
        self.items = {
            "source": [
                {
                    "id": "source-image",
                    "type": "image",
                    "parent": {"id": "source-tips"},
                    "position": {"x": 960, "y": 540},
                    "geometry": {"width": 1900, "height": 1000},
                    "data": {"title": "Miro UI"},
                },
                {
                    "id": "source-text",
                    "type": "text",
                    "parent": {"id": "source-tips"},
                    "position": {"x": 500, "y": 400},
                    "geometry": {"width": 500},
                    "data": {"content": f"<p>{all_markers}</p>"},
                    "style": {"fontSize": 20},
                },
            ],
            "target": [
                {
                    "id": "legacy-card",
                    "type": "shape",
                    "parent": {"id": "target-tips"},
                    "position": {"x": 1200, "y": 950},
                    "geometry": {"width": 2100, "height": 900},
                    "data": {"content": "<p>1 · NAVIGACE</p>", "shape": "round_rectangle"},
                }
            ],
        }
        self.connectors = {
            "source": [
                {
                    "id": f"source-c-{index}",
                    "startItem": {"id": "source-text"},
                    "endItem": {"id": "source-image", "position": {"x": index * 10, "y": index * 10}},
                }
                for index in range(8)
            ],
            "target": [],
        }

    def create_item(self, board, item_type, payload):
        assert board == "target"
        assert item_type == "frame"
        frame_id = f"replacement-tips-{self.next_frame}"
        self.next_frame += 1
        created = deepcopy(payload)
        created["id"] = frame_id
        created["type"] = "frame"
        self.frames[(board, frame_id)] = created
        return deepcopy(created)

    def delete_connector(self, board, connector_id):
        self.connectors[board] = [c for c in self.connectors[board] if c["id"] != connector_id]

    def delete_item(self, board, item_id):
        if (board, item_id) in self.frames:
            del self.frames[(board, item_id)]
            return
        self.items[board] = [item for item in self.items[board] if item["id"] != item_id]

    def update_item(self, board, item_type, item_id, payload):
        raise AssertionError("transactional Miro Tips replacement must not PATCH an irreducible frame")


def _install_fakes(monkeypatch, client):
    monkeypatch.setattr(
        tips.base,
        "_get_frame",
        lambda c, board, frame_id: deepcopy(c.frames[(board, frame_id)]),
    )
    monkeypatch.setattr(
        tips.base,
        "_children",
        lambda c, board, frame_id: [
            deepcopy(item)
            for item in c.items[board]
            if str((item.get("parent") or {}).get("id") or "") == frame_id
        ],
    )
    monkeypatch.setattr(
        tips.base,
        "_related_connectors",
        lambda c, board, ids: [
            deepcopy(connector)
            for connector in c.connectors[board]
            if str((connector.get("startItem") or {}).get("id") or "") in ids
            or str((connector.get("endItem") or {}).get("id") or "") in ids
        ],
    )
    monkeypatch.setattr(
        tips.visual,
        "_companion_source_connectors",
        lambda c, board, ids: [
            deepcopy(connector)
            for connector in c.connectors[board]
            if str((connector.get("startItem") or {}).get("id") or "") in ids
            and str((connector.get("endItem") or {}).get("id") or "") in ids
        ],
    )
    monkeypatch.setattr(
        tips,
        "_ORIGINAL_COMPANION_FRAME_PAYLOAD",
        lambda source_frame, source_main, target_main: {
            "data": {"title": source_frame["data"]["title"]},
            "geometry": deepcopy(source_frame["geometry"]),
            "position": {
                "x": source_frame["position"]["x"] + target_main["position"]["x"] - source_main["position"]["x"],
                "y": source_frame["position"]["y"] + target_main["position"]["y"] - source_main["position"]["y"],
                "origin": "center",
            },
            "style": deepcopy(source_frame["style"]),
        },
    )
    monkeypatch.setattr(
        tips,
        "_ORIGINAL_SAME_FRAME",
        lambda remote, expected: (
            remote["data"]["title"] == expected["data"]["title"]
            and abs(remote["geometry"]["width"] - expected["geometry"]["width"]) < 0.01
            and abs(remote["geometry"]["height"] - expected["geometry"]["height"]) < 0.01
            and abs(remote["position"]["x"] - expected["position"]["x"]) < 0.01
            and abs(remote["position"]["y"] - expected["position"]["y"]) < 0.01
        ),
    )
    monkeypatch.setattr(tips.visual, "_cleanup_frame", lambda c, board, frame_id: c.delete_item(board, frame_id))

    def source_copy(c, source_board, source_frame_id, target_board, target_frame_id, min_images, manifest_value):
        del source_frame_id, min_images, manifest_value
        current = [
            item
            for item in c.items[target_board]
            if (item.get("parent") or {}).get("id") == target_frame_id
        ]
        if current:
            return {
                "source_item_count": 2,
                "source_image_count": 1,
                "source_connector_count": 8,
                "items": {"created": 0, "updated": 0, "unchanged": 2, "deleted": 0},
                "connectors": {"created": 0, "updated": 0, "unchanged": 8, "deleted": 0},
            }

        id_map = {"source-image": "target-image", "source-text": "target-text"}
        for item in c.items[source_board]:
            copied = deepcopy(item)
            copied["id"] = id_map[item["id"]]
            copied["parent"] = {"id": target_frame_id}
            c.items[target_board].append(copied)
        c.connectors[target_board] = []
        for connector in c.connectors[source_board]:
            copied = deepcopy(connector)
            copied["id"] = connector["id"].replace("source-", "target-")
            copied["startItem"]["id"] = id_map[copied["startItem"]["id"]]
            copied["endItem"]["id"] = id_map[copied["endItem"]["id"]]
            c.connectors[target_board].append(copied)
        return {
            "source_item_count": 2,
            "source_image_count": 1,
            "source_connector_count": 8,
            "items": {"created": 2, "updated": 0, "unchanged": 0, "deleted": 0},
            "connectors": {"created": 8, "updated": 0, "unchanged": 0, "deleted": 0},
        }

    monkeypatch.setattr(tips, "_ORIGINAL_RECONCILE_COMPANION_CHILDREN", source_copy)


def test_miro_tips_transactionally_replaces_irreducible_card_only_guide(monkeypatch):
    client = FakeClient()
    _install_fakes(monkeypatch, client)

    first = tips.reconcile_miro_tips_children(
        client, "source", "source-tips", "target", "target-tips", manifest()
    )

    replacement_id = first["replacement_frame_id"]
    assert first["mode"] == tips.MIRO_TIPS_MODE
    assert first["container_policy"] == tips.MIRO_TIPS_CONTAINER_POLICY
    assert first["frame_replaced"] == 1
    assert first["legacy_frame_id"] == "target-tips"
    assert replacement_id != "target-tips"
    assert ("target", "target-tips") not in client.frames
    assert ("target", replacement_id) in client.frames
    assert first["source_image_count"] == 1
    assert first["target_image_count"] == 1
    assert first["source_connector_count"] == 8
    assert first["target_connector_count"] == 8
    assert first["source_image_anchor_connector_count"] == 8
    assert first["target_image_anchor_connector_count"] == 8
    assert first["required_marker_count"] == len(tips.DEFAULT_REQUIRED_MARKERS)
    assert first["target_geometry"] == {"width": 1919.43, "height": 1079.68}
    assert not any(item["id"] == "legacy-card" for item in client.items["target"])

    second = tips.reconcile_miro_tips_children(
        client, "source", "source-tips", "target", replacement_id, manifest()
    )
    assert second["frame_replaced"] == 0
    assert second["legacy_frame_id"] is None
    assert second["replacement_frame_id"] == replacement_id
    assert second["items"] == {"created": 0, "updated": 0, "unchanged": 2, "deleted": 0}
    assert second["connectors"] == {"created": 0, "updated": 0, "unchanged": 8, "deleted": 0}


def test_miro_tips_contract_rejects_card_only_or_unanchored_source_before_write(monkeypatch):
    client = FakeClient()
    _install_fakes(monkeypatch, client)
    client.connectors["source"] = client.connectors["source"][:7]

    try:
        tips.reconcile_miro_tips_children(
            client, "source", "source-tips", "target", "target-tips", manifest()
        )
    except ValueError as exc:
        assert "connectors" in str(exc)
        assert client.next_frame == 1
    else:
        raise AssertionError("expected reference tutorial connector contract failure")
