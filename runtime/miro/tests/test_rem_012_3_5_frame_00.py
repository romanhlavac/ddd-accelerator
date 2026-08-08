from pathlib import Path
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "scaffolds" / "miro" / "rem-012-3-5-frame-00.yaml"
YAML_READER = YAML(typ="safe")
MATURITY_KEYS = ["scaffold", "working", "candidate", "validated", "accepted", "superseded"]


def load():
    return YAML_READER.load(TARGET.read_text(encoding="utf-8"))


def luminance(value: str) -> float:
    rgb = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in rgb]
    return .2126 * linear[0] + .7152 * linear[1] + .0722 * linear[2]


def by_role(items):
    return {item["role"]: item for item in items}


def test_exact_scope_and_lineage():
    data = load()
    assert data["remediation_id"] == "REM-PR8-HVA-CC-012.3.6"
    assert data["authorized_predecessor_sha"] == "12d7b67cca1c4c3fc68d3de4b7033a375368ce3a"
    assert data["frame_id"] == "3458764679756478046"
    assert len(data["protected_frame_ids"]) == 17


def test_summary_uses_dedicated_rows_not_one_overloaded_shape():
    data = load()
    assert data["fixed_items"]["summary"]["content"] == "<p><strong>3 ARTEFAKTY</strong></p>"
    rows = by_role(data["summary_text_items"])
    assert rows["maturity_heading"]["content"] == "<p>Summary maturity:</p>"
    assert rows["review_heading"]["content"] == "<p>Summary review flagů:</p>"
    expected_counts = {
        "scaffold": "SCAFFOLD: 1",
        "working": "WORKING: 2",
        "candidate": "CANDIDATE: 0",
        "validated": "VALIDATED: 0",
        "accepted": "ACCEPTED: 0",
        "superseded": "SUPERSEDED: 0",
    }
    for key, phrase in expected_counts.items():
        assert phrase in rows[key]["content"]
        assert rows[key]["font_size"] >= 34
    assert "ATTENTION: 1" in rows["attention"]["content"]
    assert "BLOCKING: 0" in rows["blocking"]["content"]


def test_summary_markers_are_inline_with_matching_rows_and_inside_card():
    data = load()
    rows = by_role(data["summary_text_items"])
    summary = data["fixed_items"]["summary"]
    left = summary["x"] - summary["width"] / 2
    right = summary["x"] + summary["width"] / 2
    top = summary["y"] - summary["height"] / 2
    bottom = summary["y"] + summary["height"] / 2
    markers = data["summary_markers"]
    assert [marker["key"] for marker in markers] == MATURITY_KEYS
    for marker in markers:
        row = rows[marker["key"]]
        row_left = row["x"] - row["width"] / 2
        marker_right = marker["x"] + marker["width"] / 2
        assert abs(marker["y"] - row["y"]) <= 1
        assert 0 <= row_left - marker_right <= 80
        assert left <= marker["x"] - marker["width"] / 2
        assert marker["x"] + marker["width"] / 2 <= right
        assert top <= marker["y"] - marker["height"] / 2
        assert marker["y"] + marker["height"] / 2 <= bottom


def test_legend_markers_are_inline_with_matching_explanations():
    data = load()
    rows = by_role(data["legend_text_items"])
    markers = data["legend_markers"]
    assert [marker["key"] for marker in markers] == MATURITY_KEYS
    for marker in markers:
        row = rows[marker["key"]]
        row_left = row["x"] - row["width"] / 2
        marker_right = marker["x"] + marker["width"] / 2
        assert abs(marker["y"] - row["y"]) <= 1
        assert 0 <= row_left - marker_right <= 80
        assert marker["width"] <= 44 and marker["height"] <= 44


def test_palette_is_light_to_dark_and_shared_by_both_marker_sets():
    data = load()
    values = [data["palette"][key] for key in MATURITY_KEYS]
    levels = [luminance(value) for value in values]
    assert len(set(values)) == 6
    assert all(a > b for a, b in zip(levels, levels[1:]))
    assert [item["key"] for item in data["summary_markers"]] == MATURITY_KEYS
    assert [item["key"] for item in data["legend_markers"]] == MATURITY_KEYS


def test_bottom_legend_explains_all_states_and_review_flags():
    data = load()
    rows = by_role(data["legend_text_items"])
    expected = {
        "scaffold": "založená počáteční struktura",
        "working": "aktivně rozpracovaná pracovní verze",
        "candidate": "připravená k formálnímu review",
        "validated": "prošla technickou a metodickou validací",
        "accepted": "člověkem přijatá pro další použití",
        "superseded": "nahrazená novější verzí",
    }
    for key, explanation in expected.items():
        assert explanation in rows[key]["content"]
        assert rows[key]["font_size"] >= 24
    review = rows["review_flags"]["content"]
    assert "ATTENTION" in review and "BLOCKING = 0" in review and "BLOCKING &gt; 0" in review
    all_text = " ".join(item["content"] for item in data["summary_text_items"] + data["legend_text_items"])
    for phrase in data["forbidden_phrases"]:
        assert phrase not in all_text


def test_no_marker_is_detached_from_a_managed_text_row():
    data = load()
    summary_rows = by_role(data["summary_text_items"])
    legend_rows = by_role(data["legend_text_items"])
    linked = set()
    for marker in data["summary_markers"]:
        linked.add(("summary", marker["key"], marker["x"], marker["y"]))
        assert marker["key"] in summary_rows
    for marker in data["legend_markers"]:
        linked.add(("legend", marker["key"], marker["x"], marker["y"]))
        assert marker["key"] in legend_rows
    assert len(linked) == 12
