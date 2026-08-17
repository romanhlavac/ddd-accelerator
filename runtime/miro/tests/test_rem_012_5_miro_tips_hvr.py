from __future__ import annotations

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
            "expected_item_count": 17,
            "expected_item_type_counts": dict(tips.EXPECTED_ITEM_TYPE_COUNTS),
            "expected_connector_count": 8,
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


def reference_items(parent_id="source-tips"):
    rows = [
        {
            "id": "source-image",
            "type": "image",
            "parent": {"id": parent_id},
            "position": {"x": 960.0, "y": 540.0},
            "geometry": {"width": 1900.0, "height": 1000.0},
            "data": {"title": "Miro UI"},
        }
    ]
    for index, marker in enumerate(tips.DEFAULT_REQUIRED_MARKERS[:13]):
        rows.append(
            {
                "id": f"sticky-{index}",
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
                "id": f"text-{index}",
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
                "id": f"text-extra-{index}",
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
        self.items = {"source": reference_items()}
        self.connectors = {
            "source": [
                {
                    "id": f"connector-{index}",
                    "startItem": {"id": f"sticky-{index}"},
                    "endItem": {
                        "id": "source-image",
                        "position": {"x": 0.10 + index * 0.05, "y": 0.10},
                    },
                    "shape": "curved",
                    "style": {"strokeColor": "#000000", "endStrokeCap": "stealth"},
                    "captions": [],
                }
                for index in range(8)
            ]
        }
        self.frames = {
            ("source", "source-tips"): frame(
                "source-tips", "Miro Tips", -18762.0, -11858.0, 1919.433, 1079.681
            )
        }


def install_state_fakes(monkeypatch, client):
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
        tips.visual,
        "_companion_source_connectors",
        lambda c, board, ids: [
            deepcopy(connector)
            for connector in c.connectors[board]
            if str((connector.get("startItem") or {}).get("id") or "") in ids
            and str((connector.get("endItem") or {}).get("id") or "") in ids
        ],
    )


def test_miro_tips_exact_reference_contract_rejects_retired_topology_fields():
    value = manifest()
    value["miro_tips"]["onboarding"] = {"mode": "ddda_owned_native_onboarding"}
    try:
        tips._config(value)
    except ValueError as exc:
        assert "retired topology field" in str(exc)
    else:
        raise AssertionError("expected native-onboarding contract rejection")


def test_miro_tips_reference_identity_requires_the_exact_17_item_snapshot(monkeypatch):
    client = FakeClient()
    install_state_fakes(monkeypatch, client)

    tips.assert_reference_identity(client, "source", "source-tips", manifest())

    client.items["source"] = client.items["source"][:-1]
    try:
        tips.assert_reference_identity(client, "source", "source-tips", manifest())
    except ValueError as exc:
        assert "child items" in str(exc)
    else:
        raise AssertionError("expected exact snapshot rejection")


def test_miro_tips_frame_payload_keeps_the_verified_target_slot():
    source = frame("source-tips", "Miro Tips", -18762.0, -11858.0, 1919.433, 1079.681)
    payload = tips.miro_tips_companion_frame_payload(source, {}, {}, manifest())
    assert payload["geometry"] == source["geometry"]
    assert payload["position"] == {
        "x": -19834.447,
        "y": -11727.533,
        "origin": "center",
    }
