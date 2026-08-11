from __future__ import annotations

from copy import deepcopy

from ddda_miro import miro_tips_control_anchor_fix as anchors


def test_normalized_control_position_maps_reference_arrowhead_to_target_image():
    connector = {"id": "c1", "endItem": {"position": {"x": 0.25, "y": 0.10}}}
    image = {
        "position": {"x": 960.0, "y": 540.0},
        "geometry": {"width": 1900.0, "height": 1000.0},
    }
    assert anchors._normalized_control_position(connector, image) == (485.0, 140.0)


def test_normalized_control_position_accepts_miro_percentage_strings():
    connector = {
        "id": "c-percent",
        "endItem": {"position": {"x": "15.7494%", "y": "8.5%"}},
    }
    image = {
        "position": {"x": 960.0, "y": 540.0},
        "geometry": {"width": 1900.0, "height": 1000.0},
    }
    x, y = anchors._normalized_control_position(connector, image)
    assert abs(x - 309.2386) < 1e-9
    assert abs(y - 125.0) < 1e-9


def test_control_connector_payload_terminates_on_anchor_without_image_endpoint(monkeypatch):
    def base_payload(source, start, end, manifest):
        del source, manifest
        return {
            "startItem": {"id": start, "snapTo": "right"},
            "endItem": {"id": end, "position": {"x": 0.25, "y": 0.10}, "snapTo": "top"},
            "style": {"strokeColor": "#000000"},
        }

    monkeypatch.setattr(anchors.endpoint, "_ORIGINAL_READABLE_CONNECTOR_PAYLOAD", base_payload)
    payload = anchors._control_connector_payload(
        {"id": "source-c"}, "target-start", "target-anchor", {}
    )
    assert payload["endItem"] == {"id": "target-anchor"}
    assert payload["startItem"] == {"id": "target-start", "snapTo": "right"}


def test_anchor_payload_is_transparent_tiny_child():
    payload = anchors._anchor_payload("tips", "marker", 120.0, 80.0, 8.0)
    assert payload["parent"]["id"] == "tips"
    assert payload["geometry"] == {"width": 8.0, "height": 8.0}
    assert payload["style"]["fillOpacity"] == 0.0
    assert payload["style"]["borderOpacity"] == 0.0
    assert payload["data"]["shape"] == "circle"


class FakeClient:
    def __init__(self):
        self.items = {"source": [], "target": []}
        self.connectors = {"source": [], "target": []}
        self.next_item = 1
        self.next_connector = 1

    def create_item(self, board, item_type, payload):
        item = deepcopy(payload)
        item["id"] = f"anchor-{self.next_item}"
        item["type"] = item_type
        self.next_item += 1
        self.items[board].append(item)
        return deepcopy(item)

    def update_item(self, board, item_type, item_id, payload):
        for index, item in enumerate(self.items[board]):
            if item["id"] == item_id:
                updated = deepcopy(payload)
                updated["id"] = item_id
                updated["type"] = item_type
                self.items[board][index] = updated
                return deepcopy(updated)
        raise AssertionError(f"missing item {item_id}")

    def delete_item(self, board, item_id):
        self.items[board] = [item for item in self.items[board] if item["id"] != item_id]

    def list_connectors(self, board):
        return [deepcopy(item) for item in self.connectors[board]]

    def create_connector(self, board, payload):
        connector = deepcopy(payload)
        connector["id"] = f"target-c-{self.next_connector}"
        self.next_connector += 1
        self.connectors[board].append(connector)
        return deepcopy(connector)

    def update_connector(self, board, connector_id, payload):
        for index, connector in enumerate(self.connectors[board]):
            if connector["id"] == connector_id:
                updated = deepcopy(payload)
                updated["id"] = connector_id
                self.connectors[board][index] = updated
                return deepcopy(updated)
        raise AssertionError(f"missing connector {connector_id}")

    def delete_connector(self, board, connector_id):
        self.connectors[board] = [
            connector for connector in self.connectors[board] if connector["id"] != connector_id
        ]


def _fixture():
    client = FakeClient()
    source_image = {
        "id": "source-image",
        "type": "image",
        "parent": {"id": "source-tips"},
        "position": {"x": 960.0, "y": 540.0},
        "geometry": {"width": 1900.0, "height": 1000.0},
        "data": {"title": "Miro UI"},
    }
    target_image = deepcopy(source_image)
    target_image["id"] = "target-image"
    target_image["parent"] = {"id": "target-tips"}
    client.items["source"].append(source_image)
    client.items["target"].append(target_image)

    for index in range(8):
        source = {
            "id": f"source-start-{index}",
            "type": "sticky_note",
            "parent": {"id": "source-tips"},
            "data": {"content": f"<p>tip-{index}</p>"},
            "position": {"x": 100.0 + index * 40.0, "y": 200.0},
            "geometry": {"width": 100.0},
            "style": {},
        }
        target = deepcopy(source)
        target["id"] = f"target-start-{index}"
        target["parent"] = {"id": "target-tips"}
        client.items["source"].append(source)
        client.items["target"].append(target)
        source_connector = {
            "id": f"source-c-{index}",
            "startItem": {"id": source["id"]},
            "endItem": {
                "id": "source-image",
                "position": {"x": 0.08 + index * 0.11, "y": 0.08 + index * 0.09},
            },
            "shape": "curved",
            "style": {
                "strokeColor": "#000000",
                "strokeStyle": "normal",
                "startStrokeCap": "none",
                "endStrokeCap": "stealth",
            },
        }
        client.connectors["source"].append(source_connector)
        legacy = deepcopy(source_connector)
        legacy["id"] = f"legacy-c-{index}"
        legacy["startItem"]["id"] = target["id"]
        legacy["endItem"]["id"] = "target-image"
        client.connectors["target"].append(legacy)
    return client


def test_control_anchor_reconcile_replaces_image_connectors_and_is_idempotent(monkeypatch):
    client = _fixture()

    monkeypatch.setattr(
        anchors.base,
        "_children",
        lambda c, board, frame: [
            deepcopy(item)
            for item in c.items[board]
            if str((item.get("parent") or {}).get("id") or "") == frame
        ],
    )
    monkeypatch.setattr(
        anchors.visual,
        "_companion_source_connectors",
        lambda c, board, ids: [
            deepcopy(connector)
            for connector in c.connectors[board]
            if str((connector.get("startItem") or {}).get("id") or "") in ids
            and str((connector.get("endItem") or {}).get("id") or "") in ids
        ],
    )
    monkeypatch.setattr(
        anchors.visual,
        "_same_image",
        lambda remote, source, frame: (
            remote.get("type") == "image"
            and (remote.get("parent") or {}).get("id") == frame
            and remote.get("position") == source.get("position")
            and remote.get("geometry") == source.get("geometry")
        ),
    )
    monkeypatch.setattr(
        anchors.endpoint,
        "_ORIGINAL_READABLE_CONNECTOR_PAYLOAD",
        lambda source, start, end, manifest: {
            "startItem": {"id": start},
            "endItem": {
                "id": end,
                "position": deepcopy((source.get("endItem") or {}).get("position")),
            },
            "shape": source.get("shape"),
            "style": deepcopy(source.get("style") or {}),
        },
    )
    monkeypatch.setattr(
        anchors.visual.redline,
        "same_connector",
        lambda remote, expected: all(
            remote.get(key) == value for key, value in expected.items()
        ),
    )

    manifest = {"miro_tips": {"min_connectors": 8, "control_anchor_size": 8}}
    first = anchors._reconcile_control_anchors_and_connectors(
        client, "source", "source-tips", "target", "target-tips", manifest
    )
    assert first["control_anchor_count"] == 8
    assert first["control_anchor_connector_count"] == 8
    assert first["anchor_items"]["created"] == 8
    assert first["connectors"]["created"] == 8
    assert first["connectors"]["deleted"] == 8
    assert all(
        str((connector.get("endItem") or {}).get("id") or "").startswith("anchor-")
        for connector in client.connectors["target"]
    )

    second = anchors._reconcile_control_anchors_and_connectors(
        client, "source", "source-tips", "target", "target-tips", manifest
    )
    assert second["anchor_items"] == {
        "created": 0, "updated": 0, "unchanged": 8, "deleted": 0
    }
    assert second["connectors"] == {
        "created": 0, "updated": 0, "unchanged": 8, "deleted": 0
    }
