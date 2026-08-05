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


def test_frame_00_matches_approved_screenshot_hierarchy():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    panel = updates["3458764679756523217"]
    summary = updates["3458764679756523219"]
    legend = updates["3458764679756523220"]
    registry = manifest["frame_00_registry_reference"]

    assert panel["content"] == (
        "<p><strong>ARTIFACT HEALTH SUMMARY — acceptance-claims-modernization</strong></p>"
    )
    assert panel["frame"] == summary["frame"] == legend["frame"] == registry["frame"] == "control"
    assert panel["width"] >= 6500
    assert panel["height"] >= 2200
    assert panel["font_size"] >= 64
    assert panel["style"]["fillColor"] == "#E7F1FF"
    assert panel["style"]["textAlign"] == "left"
    assert panel["style"]["textAlignVertical"] == "top"

    assert registry["x"] < panel["x"]
    assert registry["y"] < summary["y"]
    assert registry["style"]["textAlign"] == "left"
    assert registry["font_size"] >= 36
    assert "OTEVŘÍT PLNÝ PROJEKTOVÝ ARTIFACT REGISTRY" in registry["content"]
    assert "Project-owned Git/YAML je source of truth" in registry["content"]
    assert "technický PASS" not in registry["content"]

    assert summary["x"] < panel["x"]
    assert summary["width"] >= 2200
    assert summary["height"] >= 1200
    assert summary["font_size"] >= 44
    assert summary["style"]["fillColor"] == "#FFFFFF"
    assert summary["style"]["textAlign"] == "left"
    assert summary["style"]["textAlignVertical"] == "top"
    for phrase in (
        "3 ARTEFAKTY",
        "Summary maturity:",
        "SCAFFOLD: 1",
        "WORKING: 2",
        "SUPERSEDED: 0",
        "Summary review flagů:",
        "🟧 ATTENTION: 1",
        "🟩 BLOCKING: 0",
    ):
        assert phrase in summary["content"]

    assert legend["type"] == "text"
    assert legend["width"] >= 6200
    assert legend["font_size"] >= 28
    assert legend["y"] > summary["y"]
    assert legend["style"]["textAlign"] == "left"
    assert "MATURITY:" in legend["content"]
    assert "REVIEW FLAGS:" in legend["content"]
    assert "🟥 BLOCKING &gt; 0" in legend["content"]

    _assert_inside(panel, registry)
    _assert_inside(panel, summary)
    _assert_inside(panel, legend)


def test_frame_00_preserves_screenshot_whitespace_and_alignment():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    panel = updates["3458764679756523217"]
    summary = updates["3458764679756523219"]
    legend = updates["3458764679756523220"]
    registry = manifest["frame_00_registry_reference"]
    maturity = manifest["frame_00_maturity_items"]

    panel_bounds = _bounds(panel)
    summary_bounds = _bounds(summary)

    assert panel_bounds["left"] < summary_bounds["left"]
    assert summary_bounds["right"] < panel["x"]
    assert registry["x"] < panel["x"]
    assert registry["y"] < summary_bounds["top"]
    assert legend["y"] > summary_bounds["bottom"]
    assert min(item["y"] for item in maturity) > summary_bounds["bottom"]
    assert max(item["y"] for item in maturity) < legend["y"]
    assert max(item["x"] for item in maturity) < panel_bounds["right"]
    assert min(item["x"] for item in maturity) > panel_bounds["left"]


def test_frame_00_maturity_palette_is_per_state_and_monotonic():
    manifest = _load(MANIFEST)
    palette = manifest["health_palette"]["maturity"]
    expected_keys = ["scaffold", "working", "candidate", "validated", "accepted", "superseded"]
    assert list(palette) == expected_keys
    assert len(set(palette.values())) == len(expected_keys)

    luminance = [_relative_luminance(palette[key]) for key in expected_keys]
    assert all(left > right for left, right in zip(luminance, luminance[1:]))
    assert luminance[0] - luminance[-1] >= 0.55


def test_frame_00_maturity_scale_is_compact_and_uses_actual_counts():
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
        assert item["font_size"] >= 24
        assert item["width"] <= 800
        assert item["height"] <= 200
        _assert_inside(panel, item)


def test_frame_00_review_flags_are_separate_from_maturity_scale():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    summary = updates["3458764679756523219"]["content"]
    legend = updates["3458764679756523220"]["content"]
    maturity_items = manifest["frame_00_maturity_items"]
    palette = manifest["health_palette"]

    assert palette["attention"] == "#F2994A"
    assert palette["blocking_clear"] == "#27AE60"
    assert palette["blocking_active"] == "#EB5757"
    assert "Summary maturity:" in summary
    assert "Summary review flagů:" in summary
    assert summary.index("Summary maturity:") < summary.index("Summary review flagů:")
    assert "ATTENTION" not in " ".join(item["label"] for item in maturity_items)
    assert "BLOCKING" not in " ".join(item["label"] for item in maturity_items)
    assert "🟧 ATTENTION: 1" in summary
    assert "🟩 BLOCKING: 0" in summary
    assert "🟧 ATTENTION" in legend
    assert "🟩 BLOCKING = 0" in legend
    assert "🟥 BLOCKING &gt; 0" in legend


def test_frame_00_does_not_reintroduce_rejected_layout():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    panel = updates["3458764679756523217"]
    summary = updates["3458764679756523219"]
    legend = updates["3458764679756523220"]
    registry = manifest["frame_00_registry_reference"]

    assert "ARTIFACT HEALTH —" not in panel["content"]
    assert "ARTIFACT HEALTH SUMMARY" in panel["content"]
    assert summary["style"]["textAlign"] != "center"
    assert summary["height"] > 1000
    assert legend["x"] == panel["x"]
    assert registry["style"]["textAlign"] != "center"
    assert registry["y"] < 3500
    assert max(item["height"] for item in manifest["frame_00_maturity_items"]) < 250
