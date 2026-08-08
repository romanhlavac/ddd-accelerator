from __future__ import annotations

from copy import deepcopy

from ddda_miro.frame01_redline import identity, item_payload, same_item, reconcile
from ddda_miro.review_board_recovery import frame00_payload, frame00_state, restore_frame00


class FakeClient:
    def __init__(self):
        self.frames = {
            ("source", "source-frame"): {"id": "source-frame", "type": "frame", "data": {"title": "01 – DDD Starter journey, gates a iterace"}, "geometry": {"width": 58008.9, "height": 10144.3}},
            ("target", "target-frame"): {"id": "target-frame", "type": "frame", "data": {"title": "01 – DDD Starter journey, gates a iterace"}, "geometry": {"width": 58008.9, "height": 10144.3}},
            ("target", "frame00"): {"id": "frame00", "type": "frame", "data": {"title": "00 – Control Center"}, "geometry": {"width": 9000.0, "height": 8000.0}},
        }
        self.events: list[str] = []
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
                self._shape("old00", "frame00", 8000, 7000, "<p>GENERIC CONTROL CENTER</p>", 1200, 600, shape="rectangle"),
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
        if item_type == "frame":
            return [deepcopy(value) for (board, _), value in self.frames.items() if board == board_id]
        result = deepcopy(self.items.get(board_id, []))
        return [item for item in result if item_type is None or item["type"] == item_type]

    def list_connectors(self, board_id): return deepcopy(self.connectors.get(board_id, []))

    def _request(self, method, path, query=None, body=None, reconcile=None):
        parts = path.split("/"); board = parts[1]
        if method == "GET" and parts[2] == "frames":
            return deepcopy(self.frames[(board, parts[3])])
        if method == "GET" and parts[2] == "items":
            item_id = parts[3]
            return deepcopy(next(item for item in self.items[board] if item["id"] == item_id))
        if parts[2] == "frames" and method == "PATCH":
            frame_id = parts[3]
            target = body["geometry"]
            for item in self.items.get(board, []):
                if str((item.get("parent") or {}).get("id")) != frame_id:
                    continue
                x, y = float((item.get("position") or {}).get("x") or 0), float((item.get("position") or {}).get("y") or 0)
                width = float((item.get("geometry") or {}).get("width") or 0)
                height = float((item.get("geometry") or {}).get("height") or 0)
                if x - width / 2 < 0 or x + width / 2 > float(target["width"]) or y - height / 2 < 0 or y + height / 2 > float(target["height"]):
                    raise ValueError("Child item cannot be placed outside the bounds of its parent")
            self.frames[(board, frame_id)]["geometry"] = deepcopy(target)
            self.events.append(f"resize:{frame_id}")
            return deepcopy(self.frames[(board, frame_id)])
        if parts[2] in {"shapes", "texts", "sticky_notes"}:
            kind = {"shapes": "shape", "texts": "text", "sticky_notes": "sticky_note"}[parts[2]]
            if method == "POST":
                item = deepcopy(body); item["id"] = f"new-{len(self.items[board])}"; item["type"] = kind
                if kind == "text": item.setdefault("geometry", {})["height"] = 100
                self.items[board].append(item); self.events.append(f"create:{item['id']}"); return deepcopy(item)
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

    def delete_connector(self, board_id, connector_id):
        self.connectors[board_id] = [item for item in self.connectors[board_id] if item["id"] != connector_id]
        self.events.append(f"delete-connector:{connector_id}")

    def delete_item(self, board_id, item_id):
        self.items[board_id] = [item for item in self.items[board_id] if item["id"] != item_id]
        self.events.append(f"delete:{item_id}")


def manifest():
    return {"remediation_id": "REM-PR8-HVA-CC-012.5", "source_board_id": "source", "source_frame_id": "source-frame",
            "board_id": "target", "frame_id": "target-frame", "frame00_id": "frame00",
            "source_frame_title": "01 – DDD Starter journey, gates a iterace",
            "source_sentinels": ["G1 · Align", "METODIKA A ZDROJE"], "source_forbidden_sentinels": ["JAK ČÍST STAV GATE"],
            "frame00_sticky_colors": {"phase_gate_state": "light_yellow", "owner_next_action": "light_blue", "attention_blockers": "light_green"},
            "protected_frames": [str(index) for index in range(16)]}


def accepted_frame00_contract():
    return {"frame": {"width": 7000, "height": 4914.42}, "managed_updates": [
        {"role": "project_identity", "type": "shape", "x": 3500, "y": 350, "width": 6200, "height": 500, "font_size": 36, "content": "<p><strong>00 — CONTROL CENTER</strong></p>"},
        {"role": "decision_now", "type": "text", "x": 3500, "y": 850, "width": 5600, "font_size": 36, "content": "<p><strong>ROZHODNUTÍ NYNÍ</strong></p>"},
        {"role": "phase_gate_state", "type": "sticky_note", "x": 1100, "y": 2100, "width": 1900, "content": "<p>FÁZE / GATE</p><p>ALIGN / G1</p>"},
        {"role": "owner_next_action", "type": "sticky_note", "x": 3500, "y": 2100, "width": 2000, "content": "<p>ROZHODUJE</p>"},
        {"role": "attention_blockers", "type": "sticky_note", "x": 5900, "y": 2100, "width": 1900, "content": "<p>ATTENTION — 1</p>"},
        {"role": "artifact_panel", "type": "shape", "x": 3500, "y": 4000, "width": 6400, "height": 1600, "content": "", "style": {"fillColor": "#E0F2FE"}},
        {"role": "artifact_status", "type": "text", "x": 3500, "y": 3750, "width": 5600, "font_size": 32, "content": "<p><strong>ARTIFACT HEALTH — CURRENT STATUS</strong></p>"},
        {"role": "artifact_legend", "type": "text", "x": 3500, "y": 4510, "width": 5600, "font_size": 24, "content": "<p><strong>ARTIFACT LIFECYCLE / MATURITY</strong></p>"},
    ]}


def test_identity_preserves_stage_semantics_across_geometry_changes():
    client = FakeClient(); assert identity(client.items["source"][0]) == "stage:G1"; assert identity(client.items["target"][0]) == "stage:G1"


def test_payload_uses_redline_geometry_and_target_parent():
    client = FakeClient(); payload = item_payload(client.items["source"][0], "target-frame")
    assert payload["parent"] == {"id": "target-frame"}; assert payload["geometry"] == {"width": 3400.0, "height": 2000.0}


def test_source_to_target_reconcile_removes_non_redline_items_and_is_idempotent():
    client = FakeClient(); first = reconcile(client, manifest())
    assert first["items"]["updated"] >= 2 and first["items"]["created"] >= 1 and first["items"]["deleted"] == 2
    assert first["connectors"]["created"] == 20
    target_text = " ".join(str((item.get("data") or {}).get("content") or "") for item in client.items["target"] if str((item.get("parent") or {}).get("id")) == "target-frame")
    assert "METODIKA A ZDROJE" in target_text and "JAK ČÍST STAV GATE" not in target_text
    assert not any(item["type"] == "image" and str((item.get("parent") or {}).get("id")) == "target-frame" for item in client.items["target"])
    second = reconcile(client, manifest())
    assert all(second["items"][key] == 0 for key in ("created", "updated", "deleted"))
    assert all(second["connectors"][key] == 0 for key in ("created", "updated", "deleted"))


def test_same_item_treats_hex_color_case_insensitively():
    client = FakeClient(); source = client.items["source"][0]; payload = item_payload(source, "source-frame"); remote = deepcopy(source)
    remote["style"]["fillColor"] = "#fff2cc"; assert same_item(remote, payload)


def test_recovered_frame00_payload_retargets_frame01_link_and_preserves_sticky_palette():
    m = manifest(); m["board_id"] = "uXjVH0doLYY="; m["frame_id"] = "new-frame-01"
    update = {"role": "owner_next_action", "type": "sticky_note", "x": 3500, "y": 2100, "width": 2000,
              "content": '<p>ROZHODUJE</p><p><a href="https://miro.com/app/board/uXjVH1phki0=/?moveToWidget=3458764679756478059">01</a></p>'}
    payload = frame00_payload(update, "new-frame-00", m)
    assert payload["style"]["fillColor"] == "light_blue"
    assert "uXjVH0doLYY=" in payload["data"]["content"] and "new-frame-01" in payload["data"]["content"]
    assert "uXjVH1phki0=" not in payload["data"]["content"]


def test_frame00_recovery_creates_accepted_children_before_shrinking_parent_and_is_idempotent():
    client = FakeClient(); m = manifest(); contract = accepted_frame00_contract()
    first = restore_frame00(client, m, contract)
    assert first["created"] == 8 and first["deleted"] == 1
    create_indexes = [index for index, event in enumerate(client.events) if event.startswith("create:")]
    resize_index = client.events.index("resize:frame00")
    assert len(create_indexes) == 8 and max(create_indexes) < resize_index
    assert client.frames[("target", "frame00")]["geometry"] == {"width": 7000.0, "height": 4914.42}
    assert frame00_state(client, m, contract)[0]
    second = restore_frame00(client, m, contract)
    assert second["created"] == 0 and second["deleted"] == 0 and second["unchanged"] == 8
