from __future__ import annotations

from pathlib import Path

from ddda_miro.hvr_remediation import _load, _native_payload, _same_item, _verify_registry


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "scaffolds" / "miro" / "rem-012-3-hvr-remediation.yaml"


def _bounds(item):
    return {
        "left": float(item["x"]) - float(item["width"]) / 2,
        "right": float(item["x"]) + float(item["width"]) / 2,
        "top": float(item["y"]) - float(item["height"]) / 2,
        "bottom": float(item["y"]) + float(item["height"]) / 2,
    }


def _assert_inside(container, child):
    outer = _bounds(container)
    if "height" in child:
        inner = _bounds(child)
        assert outer["left"] <= inner["left"]
        assert inner["right"] <= outer["right"]
        assert outer["top"] <= inner["top"]
        assert inner["bottom"] <= outer["bottom"]
    else:
        assert outer["left"] <= float(child["x"]) - float(child["width"]) / 2
        assert float(child["x"]) + float(child["width"]) / 2 <= outer["right"]
        assert outer["top"] <= float(child["y"]) <= outer["bottom"]


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]

    def linear(value: float) -> float:
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(value) for value in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def test_rem_012_3_contract_is_project_owned_and_complete():
    manifest = _load(MANIFEST)
    assert manifest["remediation_id"] == "REM-PR8-HVA-CC-012.3"
    assert len(manifest["images"]["assets"]) == 17
    assert sum(int(item["expected_supported_count"]) for item in manifest["native_clones"]) == 129
    assert manifest["project_registry"]["markdown_path"].startswith(
        "examples/minimal/projects/acceptance-claims-modernization/"
    )
    assert not manifest["project_registry"]["markdown_path"].startswith("docs/artifacts/")
    assert _verify_registry(manifest)["status"] == "PASS"


def test_native_payload_scales_source_geometry_and_position():
    source = {
        "type": "shape",
        "data": {"content": "<p>Value proposition</p>", "shape": "rectangle"},
        "style": {"fontSize": 22, "fillColor": "#18bdb6", "borderWidth": 2},
        "position": {"x": 100, "y": 80},
        "geometry": {"width": 200, "height": 120},
    }
    payload = _native_payload(
        source,
        "target-frame",
        {"scale": 2.0, "offset_x": 500, "offset_y": 200},
    )
    assert payload["parent"] == {"id": "target-frame"}
    assert payload["position"]["x"] == 700
    assert payload["position"]["y"] == 360
    assert payload["geometry"] == {"width": 400, "height": 240}
    assert payload["style"]["fontSize"] == 48
    assert _same_item({"type": "shape", **payload}, payload)


def test_gate_legend_moves_to_journey_and_attention_is_explained():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    assert updates["3458764679756523198"]["frame"] == "journey"
    assert updates["3458764679756523206"]["frame"] == "journey"
    control_text = " ".join(
        str(item.get("content") or "")
        for item in manifest["updates"]
        if item["frame"] == "control"
    )
    assert "ATTENTION" in control_text
    assert "BLOCKING" in control_text
    assert "PROVENANCE · GENERATED" not in control_text


def test_frame_00_artifact_health_separates_status_legend_and_registry():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    panel = updates["3458764679756523217"]
    status = updates["3458764679756523219"]
    legend = updates["3458764679756523220"]
    registry = manifest["frame_00_registry_reference"]

    assert panel["frame"] == status["frame"] == legend["frame"] == registry["frame"] == "control"
    assert panel["content"] == "<p><strong>ARTIFACT HEALTH — acceptance-claims-modernization</strong></p>"
    assert panel["width"] >= 6000
    assert panel["height"] >= 2000
    assert panel["font_size"] >= 64
    assert panel["style"]["textAlignVertical"] == "top"
    assert panel["style"]["fillColor"] == "#E7F1FF"

    assert status["font_size"] >= 72
    assert "3 ARTEFAKTY" in status["content"]
    assert "🟧 ATTENTION: 1" in status["content"]
    assert "🟩 BLOCKING: 0" in status["content"]
    assert "MATURITY" not in status["content"]

    assert legend["type"] == "text"
    assert legend["font_size"] >= 44
    assert legend["x"] > panel["x"]
    assert legend["y"] < manifest["frame_00_maturity_items"][0]["y"]
    assert "MATURITY" in legend["content"]
    assert "ATTENTION" in legend["content"]
    assert "BLOCKING" in legend["content"]
    assert "OTEVŘÍT PROJEKTOVÝ ARTIFACT REGISTRY" not in legend["content"]
    assert "source of truth" not in legend["content"]

    assert registry["type"] == "text"
    assert registry["width"] >= 5800
    assert registry["font_size"] >= 44
    assert registry["y"] > manifest["frame_00_maturity_items"][0]["y"]
    assert "OTEVŘÍT PROJEKTOVÝ ARTIFACT REGISTRY" in registry["content"]
    assert "source of truth" in registry["content"]
    assert "MATURITY" not in registry["content"]
    assert "ATTENTION" not in registry["content"]
    assert "BLOCKING" not in registry["content"]

    _assert_inside(panel, status)
    _assert_inside(panel, legend)
    _assert_inside(panel, registry)


def test_frame_00_maturity_palette_is_per_state_and_monotonic():
    manifest = _load(MANIFEST)
    palette = manifest["health_palette"]["maturity"]
    expected_keys = ["scaffold", "working", "candidate", "validated", "accepted", "superseded"]
    assert list(palette) == expected_keys
    assert len(set(palette.values())) == len(expected_keys)

    luminance = [_relative_luminance(palette[key]) for key in expected_keys]
    assert all(left > right for left, right in zip(luminance, luminance[1:]))
    assert luminance[0] - luminance[-1] >= 0.55


def test_frame_00_maturity_items_use_palette_and_actual_counts():
    manifest = _load(MANIFEST)
    panel = {str(item["id"]): item for item in manifest["updates"]}["3458764679756523217"]
    palette = manifest["health_palette"]["maturity"]
    items = manifest["frame_00_maturity_items"]
    expected_labels = ["SCAFFOLD", "WORKING", "CANDIDATE", "VALIDATED", "ACCEPTED", "SUPERSEDED"]

    assert [item["label"] for item in items] == expected_labels
    assert [item["key"] for item in items] == [label.lower() for label in expected_labels]
    assert [item["count"] for item in items] == [1, 2, 0, 0, 0, 0]
    assert sum(int(item["count"]) for item in items) == 3
    assert [item["x"] for item in items] == sorted(item["x"] for item in items)
    assert len({item["y"] for item in items}) == 1

    for item in items:
        assert item["fill_color"] == palette[item["key"]]
        assert item["font_size"] >= 32
        assert item["width"] >= 800
        assert item["height"] >= 400
        _assert_inside(panel, item)


def test_frame_00_attention_and_blocking_code_is_consistent():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    status = updates["3458764679756523219"]["content"]
    legend = updates["3458764679756523220"]["content"]
    palette = manifest["health_palette"]

    assert palette["attention"] == "#F2994A"
    assert palette["blocking_clear"] == "#27AE60"
    assert palette["blocking_active"] == "#EB5757"
    for marker in ("🟧 ATTENTION", "🟩 BLOCKING"):
        assert marker in status
        assert marker in legend
    assert "🟥 BLOCKING &gt; 0" in legend


def test_frame_00_status_is_not_duplicated_or_mixed_with_legend():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    panel = updates["3458764679756523217"]["content"]
    status = updates["3458764679756523219"]["content"]
    legend = updates["3458764679756523220"]["content"]

    assert "ATTENTION:" not in panel
    assert "BLOCKING:" not in panel
    assert "znamená" not in status
    assert "popisuje" not in status
    assert "HEALTH: ATTENTION" not in status
    assert status.count("ATTENTION: 1") == 1
    assert status.count("BLOCKING: 0") == 1
    assert "znamená" in legend


def test_frame_00_readability_and_layout_regression_guard():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    panel = updates["3458764679756523217"]
    status = updates["3458764679756523219"]
    legend = updates["3458764679756523220"]
    registry = manifest["frame_00_registry_reference"]
    maturity = manifest["frame_00_maturity_items"]

    assert status["x"] < panel["x"] < legend["x"]
    assert status["y"] == legend["y"]
    assert status["width"] >= 2500
    assert legend["width"] >= 2500
    assert legend["type"] == "text"
    assert registry["style"]["textAlign"] == "center"
    assert panel["style"]["borderColor"] == "#4B79A1"
    assert status["style"]["fillColor"] == "#FFFFFF"
    assert status["style"]["textAlign"] == "center"
    assert min(item["font_size"] for item in maturity) >= 32
    assert legend["font_size"] >= 44
    assert registry["font_size"] >= 44
    assert not (legend["width"] == 3400 and legend["height"] == 1100)
