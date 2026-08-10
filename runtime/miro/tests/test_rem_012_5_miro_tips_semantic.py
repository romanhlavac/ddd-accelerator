from copy import deepcopy

from ddda_miro import frame01_redline as redline
from ddda_miro import miro_tips_hvr_semantic_fix as semantic
from ddda_miro.miro_tips_hvr_fix import desired_miro_tips_items


def manifest():
    return {
        "source_companion_frames": [
            {"id": "source-tips", "title": "Miro Tips", "min_images": 0, "mode": "ddda_owned_hvr_correction"}
        ],
        "miro_tips": {
            "width": 4600,
            "height": 2600,
            "min_font_size": 48,
            "readback_attempts": 4,
            "readback_delay_seconds": 0,
            "required_sections": [
                "MIRO QUICK START",
                "1 · NAVIGACE",
                "2 · POZNÁMKY A VÝBĚR",
                "3 · SPOLUPRÁCE",
                "4 · DDDA PRAVIDLA",
            ],
        },
    }


def remote_from(managed):
    item = deepcopy(managed["payload"])
    item["id"] = "remote-1"
    item["type"] = "shape" if "shape" in item["data"] else "text"
    item["style"].pop("fontFamily", None)
    item["style"].pop("textAlignVertical", None)
    item["style"].pop("borderWidth", None)
    return item


def test_semantic_comparator_accepts_miro_omitted_default_wire_fields():
    managed = desired_miro_tips_items("target-tips", manifest())[2]
    remote = remote_from(managed)
    assert redline.same_item(remote, managed["payload"]) is False
    assert semantic.semantic_mismatches(remote, managed["payload"]) == []
    assert semantic.same_miro_tips_item(remote, managed["payload"]) is True


def test_semantic_comparator_rejects_hvr_critical_drift():
    managed = desired_miro_tips_items("target-tips", manifest())[2]
    expected = managed["payload"]

    wrong_text = remote_from(managed)
    wrong_text["data"]["content"] = "<p>wrong</p>"
    assert "data.content" in semantic.semantic_mismatches(wrong_text, expected)

    wrong_font = remote_from(managed)
    wrong_font["style"]["fontSize"] = 24
    assert "style.fontSize" in semantic.semantic_mismatches(wrong_font, expected)

    wrong_position = remote_from(managed)
    wrong_position["position"]["x"] += 100
    assert "position.x" in semantic.semantic_mismatches(wrong_position, expected)

    wrong_fill = remote_from(managed)
    wrong_fill["style"]["fillColor"] = "#ffffff"
    assert "style.fillColor" in semantic.semantic_mismatches(wrong_fill, expected)


def test_semantic_comparator_keeps_returned_optional_fields_strict():
    managed = desired_miro_tips_items("target-tips", manifest())[2]
    remote = deepcopy(managed["payload"])
    remote["id"] = "remote-1"
    remote["type"] = "shape"
    remote["style"]["textAlignVertical"] = "middle"
    assert "style.textAlignVertical" in semantic.semantic_mismatches(remote, managed["payload"])
