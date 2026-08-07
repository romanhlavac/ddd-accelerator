from ddda_miro.review_board_recovery_wirefix import frame00_payload, frame01_replacement_payload


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
