from ddda_miro.review_board_recovery_wirefix import frame00_payload, frame_patch_preserving_top_left


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


def test_frame_resize_preserves_board_absolute_top_left_anchor():
    frame = {
        "geometry": {"width": 9000.0, "height": 8000.0},
        "position": {"x": -17000.0, "y": 1000.0, "origin": "center"},
    }
    patch = frame_patch_preserving_top_left(frame, {"width": 7000.0, "height": 4914.42})
    assert patch["geometry"] == {"width": 7000.0, "height": 4914.42}
    assert patch["position"]["x"] == -18000.0
    assert abs(patch["position"]["y"] - (-542.79)) < 0.001
    old_left = frame["position"]["x"] - frame["geometry"]["width"] / 2
    old_top = frame["position"]["y"] - frame["geometry"]["height"] / 2
    new_left = patch["position"]["x"] - patch["geometry"]["width"] / 2
    new_top = patch["position"]["y"] - patch["geometry"]["height"] / 2
    assert old_left == new_left
    assert old_top == new_top
