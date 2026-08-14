from __future__ import annotations

import hashlib
from copy import deepcopy

from ddda_miro import miro_tips_hvr_fix as tips


def manifest():
    return {
        "source_companion_frames": [
            {
                "id": "source-tips",
                "title": "Miro Tips",
                "min_images": 1,
                "mode": tips.MIRO_TIPS_MODE,
                "source_board_id": "source",
            }
        ],
        "miro_tips": {
            "mode": tips.MIRO_TIPS_MODE,
            "reference_source_board_id": "source",
            "reference_source_frame_id": "source-tips",
            "reference_source_image_id": "source-image",
            "reference_background_sha256": tips.REFERENCE_BACKGROUND_SHA256,
            "source_native_item_count": tips.SOURCE_NATIVE_ITEM_COUNT,
            "source_native_item_type_counts": dict(tips.SOURCE_NATIVE_ITEM_TYPE_COUNTS),
            "source_native_connector_count": tips.SOURCE_NATIVE_CONNECTOR_COUNT,
            "composite_asset_sha256": tips.COMPOSITE_SHA256,
            "composite_asset_dimensions": dict(tips.COMPOSITE_DIMENSIONS),
            "target_item_count": tips.TARGET_ITEM_COUNT,
            "target_item_type_counts": dict(tips.TARGET_ITEM_TYPE_COUNTS),
            "target_connector_count": tips.TARGET_CONNECTOR_COUNT,
            "container_policy": tips.MIRO_TIPS_CONTAINER_POLICY,
            "visual_equivalence_policy": tips.MIRO_TIPS_VISUAL_EQUIVALENCE_POLICY,
            "target_position": {"x": -19834.447, "y": -11727.533},
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


def reference_items(parent_id="source-tips", image_id="source-image"):
    rows = [
        {
            "id": image_id,
            "type": "image",
            "parent": {"id": parent_id},
            "position": {"x": 0.0, "y": 0.0},
            "geometry": {"width": 1900.0, "height": 1000.0},
            "data": {"title": "Miro UI"},
        }
    ]
    for index, marker in enumerate(tips.DEFAULT_REQUIRED_MARKERS[:13]):
        rows.append(
            {
                "id": f"{parent_id}-sticky-{index}",
                "type": "sticky_note",
                "parent": {"id": parent_id},
                "position": {"x": 100.0 + index * 20.0, "y": 400.0},
                "geometry": {"width": 120.0},
                "data": {"content": f"<p>{marker}</p>"},
                "style": {"fillColor": "#fff9b1"},
            }
        )
    for index, marker in enumerate(tips.DEFAULT_REQUIRED_MARKERS[13:]):
        rows.append(
            {
                "id": f"{parent_id}-text-{index}",
                "type": "text",
                "parent": {"id": parent_id},
                "position": {"x": 200.0 + index * 40.0, "y": 100.0},
                "geometry": {"width": 300.0},
                "data": {"content": f"<p>{marker}</p>"},
                "style": {"fontSize": 20, "color": "#1a1a1a"},
            }
        )
    while sum(item["type"] == "text" for item in rows) < 3:
        index = sum(item["type"] == "text" for item in rows)
        rows.append(
            {
                "id": f"{parent_id}-text-extra-{index}",
                "type": "text",
                "parent": {"id": parent_id},
                "position": {"x": 300.0 + index * 40.0, "y": 100.0},
                "geometry": {"width": 300.0},
                "data": {"content": "<p>reference</p>"},
                "style": {"fontSize": 20, "color": "#1a1a1a"},
            }
        )
    return rows


class FakeClient:
    def __init__(self):
        self.items = {
            "source": reference_items(),
            "target": reference_items("target-tips", "target-old-image"),
        }
        self.connectors = {
            "source": self._connectors("source-tips"),
            "target": self._connectors("target-tips"),
        }
        self.frames = {
            ("source", "source-tips"): frame(
                "source-tips", "Miro Tips", -18762.0, -11858.0, 1919.433, 1079.681
            ),
            ("target", "target-tips"): frame(
                "target-tips", "Miro Tips", -19834.447, -11727.533, 1919.433, 1079.681
            ),
        }
        self.events: list[str] = []

    @staticmethod
    def _connectors(parent):
        image_id = "source-image" if parent == "source-tips" else "target-old-image"
        return [
            {
                "id": f"{parent}-connector-{index}",
                "startItem": {"id": f"{parent}-sticky-{index}"},
                "endItem": {"id": image_id},
                "shape": "curved",
                "style": {"strokeColor": "#000000", "endStrokeCap": "stealth"},
                "captions": [],
            }
            for index in range(8)
        ]

    def list_items(self, board_id, item_type=None):
        rows = deepcopy(self.items[board_id])
        if item_type == "frame":
            return [deepcopy(value) for (board, _), value in self.frames.items() if board == board_id]
        return [item for item in rows if item_type is None or item["type"] == item_type]

    def list_connectors(self, board_id):
        return deepcopy(self.connectors[board_id])

    def _prepare_item_payload(self, board_id, item_type, payload):
        _ = board_id, item_type
        return deepcopy(payload)

    def _request(self, method, path, query=None, body=None, reconcile=None):
        _ = query, reconcile
        parts = path.split("/")
        board = parts[1]
        if method == "GET" and parts[2] == "frames":
            return deepcopy(self.frames[(board, parts[3])])
        if method == "POST" and parts[2] == "images":
            created = deepcopy(body)
            created["id"] = "target-composite"
            created["type"] = "image"
            self.items[board].append(created)
            self.events.append("create:target-composite")
            return deepcopy(created)
        raise AssertionError((method, path, body))

    def delete_connector(self, board_id, connector_id):
        self.connectors[board_id] = [
            item for item in self.connectors[board_id] if item["id"] != connector_id
        ]
        self.events.append(f"delete-connector:{connector_id}")

    def delete_item(self, board_id, item_id):
        self.items[board_id] = [item for item in self.items[board_id] if item["id"] != item_id]
        self.events.append(f"delete-item:{item_id}")


def install_image_readback(monkeypatch, client, source_bytes=b"reference-background"):
    composite = tips._composite_bytes()

    def source_image(_client, board, item_id):
        image = next(item for item in client.items[board] if item["id"] == item_id)
        raw = source_bytes if board == "source" else composite
        return raw, "image/png", deepcopy(image)

    monkeypatch.setattr(tips.image_transport, "source_image", source_image)
    monkeypatch.setattr(tips, "REFERENCE_BACKGROUND_SHA256", hashlib.sha256(source_bytes).hexdigest())


def test_composite_asset_is_pinned_by_sha_and_dimensions():
    raw = tips._composite_bytes()
    assert hashlib.sha256(raw).hexdigest() == tips.COMPOSITE_SHA256
    assert int.from_bytes(raw[16:20], "big") == 1439
    assert int.from_bytes(raw[20:24], "big") == 812


def test_composite_contract_rejects_retired_native_clone_fields():
    value = manifest()
    value["miro_tips"]["expected_item_count"] = 17
    try:
        tips._config(value)
    except ValueError as exc:
        assert "retired native-clone field" in str(exc)
    else:
        raise AssertionError("expected native-clone contract rejection")


def test_composite_contract_accepts_zero_target_connectors_and_rejects_a_missing_value():
    assert tips._config(manifest())

    value = manifest()
    del value["miro_tips"]["target_connector_count"]
    try:
        tips._config(value)
    except ValueError as exc:
        assert "must not contain native connectors" in str(exc)
    else:
        raise AssertionError("expected missing target connector count rejection")


def test_source_reference_identity_requires_frozen_native_topology_and_background_hash(monkeypatch):
    client = FakeClient()
    install_image_readback(monkeypatch, client)
    observed = tips.assert_reference_identity(client, "source", "source-tips", manifest())
    assert observed["native_item_count"] == 17
    assert observed["native_connector_count"] == 8

    client.items["source"] = client.items["source"][:-1]
    try:
        tips.assert_reference_identity(client, "source", "source-tips", manifest())
    except ValueError as exc:
        assert "child items" in str(exc)
    else:
        raise AssertionError("expected frozen source topology rejection")


def test_source_reference_identity_uses_the_frozen_snapshot_not_mutable_live_image_bytes(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(
        tips.image_transport,
        "source_image",
        lambda *_args: (_ for _ in ()).throw(AssertionError("live reference bytes must not be read")),
    )
    observed = tips.assert_reference_identity(client, "source", "source-tips", manifest())
    assert observed["reference_background_sha256"] == tips.REFERENCE_BACKGROUND_SHA256
    assert observed["reference_background_verification"] == "frozen_manifest_snapshot"


def test_miro_tips_replaces_native_overlay_with_one_composite_after_full_cleanup(monkeypatch):
    client = FakeClient()
    install_image_readback(monkeypatch, client)

    first = tips.reconcile_miro_tips_children(
        client, "source", "source-tips", "target", "target-tips", 1, manifest()
    )
    assert first["items"] == {"created": 1, "updated": 0, "unchanged": 0, "deleted": 17}
    assert first["connectors"] == {"created": 0, "updated": 0, "unchanged": 0, "deleted": 8}
    assert first["target_visual_snapshot"]["sha256"] == tips.COMPOSITE_SHA256
    assert first["target_visual_snapshot"]["connector_count"] == 0
    assert [item["type"] for item in client.items["target"]] == ["image"]

    first_item_delete = next(i for i, event in enumerate(client.events) if event.startswith("delete-item:"))
    last_connector_delete = max(i for i, event in enumerate(client.events) if event.startswith("delete-connector:"))
    image_create = client.events.index("create:target-composite")
    assert last_connector_delete < first_item_delete < image_create

    second = tips.reconcile_miro_tips_children(
        client, "source", "source-tips", "target", "target-tips", 1, manifest()
    )
    assert second["items"] == {"created": 0, "updated": 0, "unchanged": 1, "deleted": 0}
    assert second["connectors"] == {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0}
    assert client.events.count("create:target-composite") == 1


def test_target_image_byte_drift_triggers_full_composite_replacement(monkeypatch):
    client = FakeClient()
    source_bytes = b"reference-background"
    install_image_readback(monkeypatch, client, source_bytes)
    client.items["target"] = []
    client.connectors["target"] = []
    target = client.frames[("target", "target-tips")]
    stale = tips._prepared_composite_payload(client, "target", target)
    stale.update({"id": "target-composite", "type": "image"})
    client.items["target"].append(stale)
    reads = {"target": 0}
    composite = tips._composite_bytes()

    def source_image(_client, board, item_id):
        image = next(item for item in client.items[board] if item["id"] == item_id)
        if board == "source":
            return source_bytes, "image/png", deepcopy(image)
        reads["target"] += 1
        raw = b"wrong-image-bytes" if reads["target"] == 1 else composite
        return raw, "image/png", deepcopy(image)

    monkeypatch.setattr(tips.image_transport, "source_image", source_image)
    result = tips.reconcile_miro_tips_children(
        client, "source", "source-tips", "target", "target-tips", 1, manifest()
    )
    assert result["items"] == {"created": 1, "updated": 0, "unchanged": 0, "deleted": 1}
    assert result["target_visual_snapshot"]["sha256"] == tips.COMPOSITE_SHA256


def test_frame_payload_keeps_the_verified_target_slot():
    source = frame("source-tips", "Miro Tips", -18762.0, -11858.0, 1919.433, 1079.681)
    payload = tips.miro_tips_companion_frame_payload(source, {}, {}, manifest())
    assert payload["geometry"] == source["geometry"]
    assert payload["position"] == {"x": -19834.447, "y": -11727.533, "origin": "center"}
