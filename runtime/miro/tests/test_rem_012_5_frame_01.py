from __future__ import annotations

from copy import deepcopy

from ddda_miro.frame01_redline import identity, item_payload, same_item, reconcile


class FakeClient:
    def __init__(self):
        self.frames = {
            ("source", "source-frame"): {"id": "source-frame", "type": "frame", "data": {"title": "01 – DDD Starter journey, gates a iterace"}, "geometry": {"width": 58008.9, "height": 10144.3}},
            ("target", "target-frame"): {"id": "target-frame", "type": "frame", "data": {"title": "01 – DDD Starter journey, gates a iterace"}, "geometry": {"width": 58008.9, "height": 10144.3}},
        }
        self.items = {
            "source": [
                self._shape("s-stage", "source-frame", 100, 100, "<p><strong>G1 · Align</strong></p><p>READY</p>", 3400, 2000),
                self._shape("s-marker", "source-frame", 100, 300, "<p><strong>G1</strong></p><p>◉</p>", 800, 800, shape="rhombus"),
                self._text("s-resource", "source-frame", 10, 10, "<p><strong>METODIKA A ZDROJE</strong></p>", 700),
            ],
            "target": [
                self._shape("t-stage", "target-frame", 250, 100, "<p><strong>G1 · Align</strong></p><p>READY</p>", 5000, 1600),
                self._shape("t-marker", "target-frame", 100, 300, "<p><strong>G1</strong></p><p>◉</p>", 700, 700, shape="rhombus"),
                self._shape("extra", "target-frame", 900, 20, "<p>JAK ČÍST STAV GATE</p>", 900, 100),
                {"id": "image-extra", "type": "image", "parent": {"id": "target-frame"}, "position": {"x": 700, "y": 700}, "geometry": {"width": 200, "height": 100}, "data": {}},
            ],
        }
        for index in range(48):
            self.items["source"].append(self._shape(f"s-{index}", "source-frame", 1000 + index * 10, 1000, f"<p>ITEM-{index}</p>", 50, 50))
        self.connectors = {"source": [], "target": []}
        source_ids = [item["id"] for item in self.items["source"]]
        for index in range(20):
            self.connectors["source"].append({
                "id": f"sc-{index}", "startItem": {"id": source_ids[index]}, "endItem": {"id": source_ids[index + 1]},
                "shape": "curved", "style": {"strokeColor": "#365A8C", "strokeStyle": "normal", "endStrokeCap": "stealth"},
                "captions": [{"content": f"C-{index}", "position": "50%"}],
            })

    @staticmethod
    def _shape(item_id, parent, x, y, content, width, height, shape="hexagon"):
        return {"id": item_id, "type": "shape", "parent": {"id": parent}, "data": {"content": content, "shape": shape},
                "position": {"x": x, "y": y}, "geometry": {"width": width, "height": height},
                "style": {"fillColor": "#FFF2CC", "fontFamily": "arial", "fontSize": 144, "textAlign": "center", "textAlignVertical": "top", "color": "#1A1A1A", "borderColor": "#365A8C", "borderWidth": 2}}

    @staticmethod
    def _text(item_id, parent, x, y, content, width):
        return {"id": item_id, "type": "text", "parent": {"id": parent}, "data": {"content": content}, "position": {"x": x, "y": y},
                "geometry": {"width": width, "height": 100}, "style": {"fontFamily": "arial", "fontSize": 24, "textAlign": "left", "color": "#365A8C"}}

    def list_items(self, board_id, item_type=None):
        if item_type == "frame": return [value for (board, _), value in self.frames.items() if board == board_id]
        result = deepcopy(self.items.get(board_id, [])); return [item for item in result if item_type is None or item["type"] == item_type]

    def list_connectors(self, board_id): return deepcopy(self.connectors.get(board_id, []))

    def _request(self, method, path, query=None, body=None, reconcile=None):
        parts = path.split("/"); board = parts[1]
        if method == "GET" and parts[2] == "frames": return deepcopy(self.frames[(board, parts[3])])
        if parts[2] in {"shapes", "texts", "sticky_notes"}:
            kind = {"shapes": "shape", "texts": "text", "sticky_notes": "sticky_note"}[parts[2]]
            if method == "POST":
                item = deepcopy(body); item["id"] = f"new-{len(self.items[board])}"; item["type"] = kind; self.items[board].append(item); return deepcopy(item)
            if method == "PATCH":
                item_id = parts[3]
                for idx, item in enumerate(self.items[board]):
                    if item["id"] == item_id:
                        updated = deepcopy(body); updated["id"] = item_id; updated["type"] = kind
                        if kind == "text": updated.setdefault("geometry", {})["height"] = item.get("geometry", {}).get("height", 100)
                        self.items[board][idx] = updated; return deepcopy(updated)
        raise AssertionError((method, path, body))

    def create_connector(self, board_id, payload):
        item = deepcopy(payload); item["id"] = f"new-c-{len(self.connectors[board_id])}"; self.connectors[board_id].append(item); return deepcopy(item)

    def update_connector(self, board_id, connector_id, payload):
        for idx, item in enumerate(self.connectors[board_id]):
            if item["id"] == connector_id:
                updated = deepcopy(payload); updated["id"] = connector_id; self.connectors[board_id][idx] = updated; return deepcopy(updated)
        raise AssertionError(connector_id)

    def delete_connector(self, board_id, connector_id): self.connectors[board_id] = [item for item in self.connectors[board_id] if item["id"] != connector_id]
    def delete_item(self, board_id, item_id): self.items[board_id] = [item for item in self.items[board_id] if item["id"] != item_id]


def manifest():
    return {"remediation_id": "REM-PR8-HVA-CC-012.5", "source_board_id": "source", "source_frame_id": "source-frame",
            "board_id": "target", "frame_id": "target-frame", "source_frame_title": "01 – DDD Starter journey, gates a iterace",
            "source_sentinels": ["G1 · Align", "METODIKA A ZDROJE"], "source_forbidden_sentinels": ["JAK ČÍST STAV GATE"],
            "protected_frames": [str(index) for index in range(17)]}


def test_identity_preserves_stage_semantics_across_geometry_changes():
    client = FakeClient(); assert identity(client.items["source"][0]) == "stage:G1"; assert identity(client.items["target"][0]) == "stage:G1"


def test_payload_uses_redline_geometry_and_target_parent():
    client = FakeClient(); payload = item_payload(client.items["source"][0], "target-frame")
    assert payload["parent"] == {"id": "target-frame"}; assert payload["geometry"] == {"width": 3400.0, "height": 2000.0}


def test_source_to_target_reconcile_removes_non_redline_items_and_is_idempotent():
    client = FakeClient(); first = reconcile(client, manifest())
    assert first["items"]["updated"] >= 2 and first["items"]["created"] >= 1 and first["items"]["deleted"] == 2
    assert first["connectors"]["created"] == 20
    target_text = " ".join(str((item.get("data") or {}).get("content") or "") for item in client.items["target"])
    assert "METODIKA A ZDROJE" in target_text and "JAK ČÍST STAV GATE" not in target_text
    assert not any(item["type"] == "image" for item in client.items["target"])
    second = reconcile(client, manifest())
    assert all(second["items"][key] == 0 for key in ("created", "updated", "deleted"))
    assert all(second["connectors"][key] == 0 for key in ("created", "updated", "deleted"))


def test_same_item_treats_hex_color_case_insensitively():
    client = FakeClient(); source = client.items["source"][0]; payload = item_payload(source, "source-frame"); remote = deepcopy(source)
    remote["style"]["fillColor"] = "#fff2cc"; assert same_item(remote, payload)
