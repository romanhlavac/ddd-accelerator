from __future__ import annotations

from copy import deepcopy

from ddda_miro import miro_tips_render_fidelity_fix as fidelity


def test_normalized_control_position_maps_frozen_arrowhead_to_target_image():
    connector = {"id": "c1", "endItem": {"position": {"x": 0.25, "y": 0.10}}}
    image = {
        "position": {"x": 960.0, "y": 540.0},
        "geometry": {"width": 1900.0, "height": 1000.0},
    }
    assert fidelity.normalized_control_position(connector, image) == (485.0, 140.0)


def test_anchor_payload_is_transparent_tiny_child():
    payload = fidelity._anchor_payload("tips", 120.0, 80.0)
    assert payload["parent"] == {"id": "tips"}
    assert payload["geometry"] == {"width": 8.0, "height": 8.0}
    assert payload["style"]["fillOpacity"] == 0.0
    assert payload["style"]["borderOpacity"] == 0.0
    assert payload["data"]["shape"] == "circle"


def test_control_connector_payload_terminates_on_anchor(monkeypatch):
    monkeypatch.setattr(
        fidelity.visual,
        "readable_connector_payload",
        lambda source, start, end, manifest: {
            "startItem": {"id": start, "snapTo": "right"},
            "endItem": {
                "id": end,
                "position": deepcopy((source.get("endItem") or {}).get("position")),
            },
            "shape": "curved",
            "style": {"strokeColor": "#000000"},
        },
    )
    payload = fidelity._control_connector_payload(
        {"endItem": {"position": {"x": 0.2, "y": 0.3}}},
        "target-start",
        "target-anchor",
        {},
    )
    assert payload["startItem"] == {"id": "target-start", "snapTo": "right"}
    assert payload["endItem"] == {"id": "target-anchor"}


class AnchorClient:
    def __init__(self):
        self.items = {
            "target": [
                {
                    "id": "target-image",
                    "type": "image",
                    "parent": {"id": "target-frame"},
                    "position": {"x": 960.0, "y": 540.0},
                    "geometry": {"width": 1900.0, "height": 1000.0},
                },
                *[
                    {
                        "id": f"target-start-{index}",
                        "type": "sticky_note",
                        "parent": {"id": "target-frame"},
                    }
                    for index in range(8)
                ],
            ]
        }
        self.connectors = {
            "target": [
                {
                    "id": f"legacy-{index}",
                    "startItem": {"id": f"target-start-{index}"},
                    "endItem": {"id": "target-image"},
                    "shape": "curved",
                    "style": {"strokeColor": "#000000"},
                }
                for index in range(8)
            ]
        }
        self.next_item = 1
        self.next_connector = 1

    def _request(self, method, path, body=None, **_kwargs):
        assert method in {"POST", "PATCH"}
        if "/shapes" not in path:
            raise AssertionError(path)
        if method == "POST":
            item = deepcopy(body)
            item["id"] = f"anchor-{self.next_item}"
            item["type"] = "shape"
            self.next_item += 1
            self.items["target"].append(item)
            return deepcopy(item)
        item_id = path.rsplit("/", 1)[-1]
        for index, item in enumerate(self.items["target"]):
            if item.get("id") == item_id:
                updated = deepcopy(body)
                updated["id"] = item_id
                updated["type"] = "shape"
                self.items["target"][index] = updated
                return deepcopy(updated)
        raise AssertionError(item_id)

    def list_connectors(self, board):
        return deepcopy(self.connectors[board])

    def create_connector(self, board, payload):
        connector = deepcopy(payload)
        connector["id"] = f"managed-{self.next_connector}"
        self.next_connector += 1
        self.connectors[board].append(connector)
        return deepcopy(connector)

    def update_connector(self, board, connector_id, payload):
        for index, connector in enumerate(self.connectors[board]):
            if connector.get("id") == connector_id:
                updated = deepcopy(payload)
                updated["id"] = connector_id
                self.connectors[board][index] = updated
                return deepcopy(updated)
        raise AssertionError(connector_id)

    def delete_connector(self, board, connector_id):
        self.connectors[board] = [
            row for row in self.connectors[board] if row.get("id") != connector_id
        ]

    def delete_item(self, board, item_id):
        self.items[board] = [row for row in self.items[board] if row.get("id") != item_id]


def test_control_anchor_reconcile_replaces_direct_image_connectors_and_is_idempotent(monkeypatch):
    client = AnchorClient()
    source_image = {
        "id": "source-image",
        "type": "image",
        "position": {"x": 960.0, "y": 540.0},
        "geometry": {"width": 1900.0, "height": 1000.0},
    }
    target_image = deepcopy(source_image)
    target_image["id"] = "target-image"
    source_connectors = [
        {
            "id": f"source-c-{index}",
            "startItem": {"id": f"source-start-{index}"},
            "endItem": {
                "id": "source-image",
                "position": {"x": 0.08 + index * 0.10, "y": 0.10 + index * 0.08},
            },
            "shape": "curved",
            "style": {
                "strokeColor": "#000000",
                "strokeStyle": "normal",
                "startStrokeCap": "none",
                "endStrokeCap": "stealth",
            },
        }
        for index in range(8)
    ]
    mapping = {f"source-start-{index}": f"target-start-{index}" for index in range(8)}

    monkeypatch.setattr(
        fidelity.base,
        "_children",
        lambda _client, board, frame: [
            deepcopy(item)
            for item in client.items[board]
            if str((item.get("parent") or {}).get("id") or "") == frame
        ],
    )
    monkeypatch.setattr(
        fidelity,
        "_target_image",
        lambda *_args: (deepcopy(source_image), deepcopy(target_image)),
    )
    monkeypatch.setattr(
        fidelity,
        "_source_connectors",
        lambda *_args: deepcopy(source_connectors),
    )
    monkeypatch.setattr(fidelity, "_map_native", lambda *_args: dict(mapping))
    monkeypatch.setattr(
        fidelity.visual,
        "readable_connector_payload",
        lambda source, start, end, manifest: {
            "startItem": {"id": start},
            "endItem": {"id": end},
            "shape": source.get("shape"),
            "style": deepcopy(source.get("style") or {}),
        },
    )

    def same_connector(remote, expected):
        return all(remote.get(key) == value for key, value in expected.items())

    monkeypatch.setattr(fidelity.visual.redline, "same_connector", same_connector)

    first = fidelity._reconcile_anchors_and_connectors(
        client, "source", "source-frame", "target", "target-frame", {}
    )
    assert first["anchor_items"]["created"] == 8
    assert first["connectors"]["created"] == 8
    assert first["connectors"]["deleted"] == 8
    assert first["control_anchor_count"] == 8
    assert first["control_anchor_connector_count"] == 8
    assert all(
        str((connector.get("endItem") or {}).get("id") or "").startswith("anchor-")
        for connector in client.connectors["target"]
    )

    second = fidelity._reconcile_anchors_and_connectors(
        client, "source", "source-frame", "target", "target-frame", {}
    )
    assert second["anchor_items"] == {
        "created": 0,
        "updated": 0,
        "unchanged": 8,
        "deleted": 0,
    }
    assert second["connectors"] == {
        "created": 0,
        "updated": 0,
        "unchanged": 8,
        "deleted": 0,
    }


class LayerClient:
    def __init__(self):
        self.source = [
            {
                "id": f"source-{index}",
                "type": "sticky_note" if index < 13 else "text",
                "parent": {"id": "source-frame"},
            }
            for index in range(16)
        ]
        self.target = [
            {
                "id": "background",
                "type": "image",
                "parent": {"id": "target-frame"},
            },
            *[
                {
                    "id": f"old-{index}",
                    "type": "sticky_note" if index < 13 else "text",
                    "parent": {"id": "target-frame"},
                }
                for index in range(16)
            ],
        ]
        self.operations: list[tuple[str, str]] = []
        self.next_item = 1

    def list_connectors(self, _board):
        return []

    def delete_connector(self, _board, connector_id):
        self.operations.append(("delete_connector", connector_id))

    def delete_item(self, board, item_id):
        assert board == "target"
        self.operations.append(("delete_item", item_id))
        self.target = [row for row in self.target if row.get("id") != item_id]

    def _request(self, method, path, body=None, **_kwargs):
        assert method == "POST"
        self.operations.append(("post", path))
        item = deepcopy(body)
        item["id"] = f"new-{self.next_item}"
        self.next_item += 1
        item["type"] = "sticky_note" if "/sticky_notes" in path else "text"
        self.target.append(item)
        return deepcopy(item)


def test_layer_repair_retains_background_and_recreates_visible_callouts_after_it(monkeypatch):
    client = LayerClient()

    def children(_client, board, frame):
        rows = client.source if board == "source" else client.target
        return [
            deepcopy(item)
            for item in rows
            if str((item.get("parent") or {}).get("id") or "") == frame
        ]

    monkeypatch.setattr(fidelity.base, "_children", children)
    monkeypatch.setattr(fidelity.visual.redline, "identity", lambda item: str(item.get("id")))
    monkeypatch.setattr(
        fidelity.visual,
        "_ORIGINAL_ITEM_PAYLOAD",
        lambda source, frame: {"parent": {"id": frame}},
    )
    monkeypatch.setattr(fidelity.visual.redline, "same_item", lambda *_args: True)

    result = fidelity._rebuild_native_above_background(
        client, "source", "source-frame", "target", "target-frame"
    )
    assert result["native_deleted"] == 16
    assert result["native_created"] == 16
    assert any(item.get("id") == "background" for item in client.target)
    assert not any(operation == ("delete_item", "background") for operation in client.operations)
    first_post = next(index for index, row in enumerate(client.operations) if row[0] == "post")
    assert all(row[0] == "delete_item" for row in client.operations[:first_post])
    assert len([row for row in client.operations if row[0] == "post"]) == 16
