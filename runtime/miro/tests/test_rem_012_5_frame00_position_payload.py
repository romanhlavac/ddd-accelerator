from ddda_miro.review_board_recovery_wirefix import frame00_payload


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
