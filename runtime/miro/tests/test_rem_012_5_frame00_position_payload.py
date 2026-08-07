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
    source_main = {
        "position": {"x": 9076.78, "y": -8458.92},
    }
    target_main = {
        "position": {"x": 8004.426, "y": -8927.845},
    }
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
