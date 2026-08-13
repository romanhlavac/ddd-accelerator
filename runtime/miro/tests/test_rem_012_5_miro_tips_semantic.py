from copy import deepcopy

from ddda_miro import frame01_redline as redline
from ddda_miro import miro_tips_hvr_semantic_fix as semantic


def expected_item():
    return {
        "data": {"content": "<p>stickies / post-its</p>"},
        "parent": {"id": "target-tips"},
        "position": {"x": 223.867, "y": 392.085, "origin": "center"},
        "geometry": {"width": 160.296},
        "style": {
            "fontFamily": "open_sans",
            "fontSize": 20,
            "textAlign": "left",
            "color": "#1a1a1a",
        },
    }


def remote_from_expected():
    remote = deepcopy(expected_item())
    remote["id"] = "remote-1"
    remote["type"] = "text"
    remote["style"].pop("fontFamily", None)
    return remote


def test_semantic_comparator_accepts_miro_omitted_default_wire_fields():
    remote = remote_from_expected()
    assert redline.same_item(remote, expected_item()) is False
    assert semantic.semantic_mismatches(remote, expected_item()) == []
    assert semantic.same_miro_tips_item(remote, expected_item()) is True


def test_semantic_comparator_rejects_hvr_critical_drift():
    expected = expected_item()

    wrong_text = remote_from_expected()
    wrong_text["data"]["content"] = "<p>wrong</p>"
    assert "data.content" in semantic.semantic_mismatches(wrong_text, expected)

    wrong_font = remote_from_expected()
    wrong_font["style"]["fontSize"] = 14
    assert "style.fontSize" in semantic.semantic_mismatches(wrong_font, expected)

    wrong_position = remote_from_expected()
    wrong_position["position"]["x"] += 100
    assert "position.x" in semantic.semantic_mismatches(wrong_position, expected)

    wrong_color = remote_from_expected()
    wrong_color["style"]["color"] = "#ffffff"
    assert "style.color" in semantic.semantic_mismatches(wrong_color, expected)


def test_semantic_comparator_keeps_returned_optional_fields_strict():
    remote = deepcopy(expected_item())
    remote["id"] = "remote-1"
    remote["type"] = "text"
    remote["style"]["textAlign"] = "center"
    assert "style.textAlign" in semantic.semantic_mismatches(remote, expected_item())
