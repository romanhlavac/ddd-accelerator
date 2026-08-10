from copy import deepcopy

from ddda_miro.miro_tips_hvr_fix import (
    MIRO_TIPS_MODE,
    desired_miro_tips_items,
    miro_tips_companion_frame_payload,
    reconcile_miro_tips_children,
)


def manifest():
    return {
        "source_companion_frames": [
            {
                "id": "source-tips",
                "title": "Miro Tips",
                "min_images": 0,
                "mode": MIRO_TIPS_MODE,
            }
        ],
        "miro_tips": {
            "width": 4600,
            "height": 2600,
            "min_font_size": 48,
            "required_sections": [
                "MIRO QUICK START",
                "1 · NAVIGACE",
                "2 · POZNÁMKY A VÝBĚR",
                "3 · SPOLUPRÁCE",
                "4 · DDDA PRAVIDLA",
            ],
        },
    }


def test_miro_tips_contract_is_readable_complete_and_image_independent():
    items = desired_miro_tips_items("target-tips", manifest())
    assert len(items) == 6
    assert all(item["payload"]["parent"] == {"id": "target-tips"} for item in items)
    assert all(
        int((item["payload"].get("style") or {}).get("fontSize") or 0) >= 48
        for item in items
    )
    text = " ".join(str(item["payload"]["data"]["content"]) for item in items)
    for marker in manifest()["miro_tips"]["required_sections"]:
        assert marker in text
    assert "00 Control Center" in text
    assert "01 Journey" in text
    assert "HOTSPOT" in text
    assert "OTÁZKA?" in text


def test_miro_tips_frame_payload_expands_readability_without_changing_translated_center():
    source_main = {"position": {"x": 9076.78, "y": -8458.92}}
    target_main = {"position": {"x": 8004.426, "y": -8927.845}}
    source_tips = {
        "data": {"title": "Miro Tips"},
        "geometry": {"width": 1919.43, "height": 1079.68},
        "position": {"x": -18762.093, "y": -11858.608},
        "style": {"fillColor": "#ffffff"},
    }
    payload = miro_tips_companion_frame_payload(
        source_tips, source_main, target_main, manifest()
    )
    assert payload["geometry"] == {"width": 4600.0, "height": 2600.0}
    assert abs(payload["position"]["x"] - (-19834.447)) < 0.01
    assert abs(payload["position"]["y"] - (-12327.533)) < 0.01


class FakeClient:
    def __init__(self):
        self.items = {
            "source": [
                {
                    "id": "source-image",
                    "type": "image",
                    "parent": {"id": "source-tips"},
                    "position": {"x": 1000, "y": 500},
                    "geometry": {"width": 1900, "height": 1000},
                    "data": {},
                }
            ],
            "target": [
                {
                    "id": "legacy-image",
                    "type": "image",
                    "parent": {"id": "target-tips"},
                    "position": {"x": 1000, "y": 500},
                    "geometry": {"width": 1900, "height": 1000},
                    "data": {},
                },
                {
                    "id": "legacy-tip",
                    "type": "sticky_note",
                    "parent": {"id": "target-tips"},
                    "position": {"x": 200, "y": 200},
                    "geometry": {"width": 118, "height": 118},
                    "data": {"content": "<p>take a look at the shortcuts</p>"},
                    "style": {"fillColor": "light_yellow"},
                },
            ],
        }
        self.connectors = {
            "source": [],
            "target": [
                {
                    "id": "legacy-connector",
                    "startItem": {"id": "legacy-tip"},
                    "endItem": {"id": "legacy-image"},
                }
            ],
        }
        self.next_id = 1

    def list_items(self, board, item_type=None):
        result = deepcopy(self.items[board])
        return [
            item for item in result if item_type is None or item.get("type") == item_type
        ]

    def list_connectors(self, board):
        return deepcopy(self.connectors[board])

    def _request(self, method, path, query=None, body=None, reconcile=None):
        parts = path.split("/")
        board = parts[1]
        if method == "POST":
            endpoint = parts[2]
            item_type = {"texts": "text", "shapes": "shape"}[endpoint]
            item = deepcopy(body)
            item["id"] = f"managed-{self.next_id}"
            self.next_id += 1
            item["type"] = item_type
            if item_type == "text":
                item.setdefault("geometry", {})["height"] = 100
            self.items[board].append(item)
            return deepcopy(item)
        if method == "PATCH":
            item_id = parts[3]
            endpoint = parts[2]
            item_type = {"texts": "text", "shapes": "shape"}[endpoint]
            for index, item in enumerate(self.items[board]):
                if item["id"] == item_id:
                    updated = deepcopy(body)
                    updated["id"] = item_id
                    updated["type"] = item_type
                    if item_type == "text":
                        updated.setdefault("geometry", {})["height"] = item.get(
                            "geometry", {}
                        ).get("height", 100)
                    self.items[board][index] = updated
                    return deepcopy(updated)
            raise AssertionError(item_id)
        if method == "GET" and parts[2] == "items":
            item_id = parts[3]
            return deepcopy(next(item for item in self.items[board] if item["id"] == item_id))
        raise AssertionError((method, path, body))

    def delete_connector(self, board, connector_id):
        self.connectors[board] = [
            connector
            for connector in self.connectors[board]
            if connector["id"] != connector_id
        ]

    def delete_item(self, board, item_id):
        self.items[board] = [item for item in self.items[board] if item["id"] != item_id]


def test_miro_tips_reconcile_replaces_legacy_screenshot_and_is_idempotent():
    client = FakeClient()
    first = reconcile_miro_tips_children(
        client,
        "source",
        "source-tips",
        "target",
        "target-tips",
        manifest(),
    )
    assert first["mode"] == MIRO_TIPS_MODE
    assert first["source_image_count"] == 1
    assert first["target_image_count"] == 0
    assert first["items"]["created"] == 6
    assert first["items"]["deleted"] == 2
    assert first["connectors"]["deleted"] == 1

    final = [
        item
        for item in client.items["target"]
        if (item.get("parent") or {}).get("id") == "target-tips"
    ]
    assert len(final) == 6
    assert not any(item["type"] == "image" for item in final)

    second = reconcile_miro_tips_children(
        client,
        "source",
        "source-tips",
        "target",
        "target-tips",
        manifest(),
    )
    assert second["items"] == {
        "created": 0,
        "updated": 0,
        "unchanged": 6,
        "deleted": 0,
    }
    assert second["connectors"] == {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "deleted": 0,
    }
