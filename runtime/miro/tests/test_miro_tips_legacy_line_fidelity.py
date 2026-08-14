from __future__ import annotations

from copy import deepcopy

from ddda_miro import miro_tips_legacy_line_fidelity_fix as legacy


def _text(item_id: str, content: str) -> dict:
    return {
        "id": item_id,
        "type": "text",
        "data": {"content": f"<p>{content}</p>"},
    }


def _template() -> dict:
    return {
        "id": "template",
        "shape": "curved",
        "style": {
            "strokeColor": "#000000",
            "strokeStyle": "normal",
            "startStrokeCap": "none",
            "endStrokeCap": "stealth",
        },
        "startItem": {"id": "sticky"},
        "endItem": {"id": "image", "position": {"x": "10%", "y": "10%"}},
    }


def test_three_legacy_visual_arrows_resolve_from_the_three_reference_text_items():
    items = [
        _text(
            "nav",
            "toggle between navigation mode & edit mode (shortcut: V) Switch to navigation mode when not editing",
        ),
        _text("stickies", "stickies / post-its"),
        _text("lines", "arrows / connection lines"),
    ]
    rows = legacy._legacy_source_connectors(items, "image", _template())

    assert len(rows) == 3
    assert {row["id"] for row in rows} == {
        "ddda-legacy-visual-arrow-navigation_mode",
        "ddda-legacy-visual-arrow-sticky_notes",
        "ddda-legacy-visual-arrow-connection_lines",
    }
    assert all(row["shape"] == "straight" for row in rows)
    assert all(row["style"]["endStrokeCap"] == "stealth" for row in rows)


def test_legacy_arrow_endpoints_are_versioned_against_approved_reference():
    assert len(legacy.LEGACY_ARROW_SPECS) == 3
    for spec in legacy.LEGACY_ARROW_SPECS:
        start_x, start_y = spec["start"]
        end_x, end_y = spec["end"]
        assert 0.0 < end_x < start_x < 0.1
        assert abs(start_y - end_y) < 1e-9
        assert 0.2 < start_y < 0.5


def test_compatibility_controls_use_six_legacy_line_endpoints_plus_one_anchor(monkeypatch):
    image = {
        "position": {"x": 1000.0, "y": 500.0},
        "geometry": {"width": 2000.0, "height": 1000.0},
    }
    direct = [_template() for _ in range(8)]
    monkeypatch.setattr(
        legacy.full.fidelity,
        "normalized_control_position",
        lambda connector, target_image: (123.0, 456.0),
    )

    positions = legacy.compatibility_positions_with_legacy_arrows(direct, image)

    assert len(positions) == 7
    assert positions[-1] == (123.0, 456.0)
    assert positions[0] != positions[1]
    assert positions[2] != positions[3]
    assert positions[4] != positions[5]


def test_synthetic_legacy_connector_uses_two_transparent_endpoints_not_same_proxy(monkeypatch):
    source = _template()
    source["_ddda_legacy_visual_arrow"] = deepcopy(legacy.LEGACY_ARROW_SPECS[0])
    source["_ddda_target_start_anchor_id"] = "start-anchor"
    source["_ddda_target_end_anchor_id"] = "end-anchor"

    monkeypatch.setattr(
        legacy.visual,
        "readable_connector_payload",
        lambda row, start_id, end_id, manifest: {
            "startItem": {"id": start_id},
            "endItem": {"id": end_id},
            "shape": row["shape"],
            "style": deepcopy(row["style"]),
        },
    )

    payload = legacy.connector_payload_with_legacy_visual_arrow(
        source,
        {},
        {},
        {"id": "image"},
        "routing-proxy",
        {},
    )

    assert payload["startItem"] == {"id": "start-anchor"}
    assert payload["endItem"] == {"id": "end-anchor"}
    assert payload["startItem"]["id"] != payload["endItem"]["id"]
    assert payload["shape"] == "straight"
