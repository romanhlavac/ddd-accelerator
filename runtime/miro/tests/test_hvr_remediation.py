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


def test_frame_00_artifact_health_has_explicit_project_title_and_hierarchy():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    panel = updates["3458764679756523217"]
    status = updates["3458764679756523219"]
    legend = updates["3458764679756523220"]

    assert panel["frame"] == status["frame"] == legend["frame"] == "control"
    assert panel["content"] == "<p><strong>ARTIFACT HEALTH — acceptance-claims-modernization</strong></p>"
    assert panel["width"] >= 6000
    assert panel["height"] >= 2000
    assert panel["font_size"] >= 64
    assert panel["style"]["textAlignVertical"] == "top"
    assert panel["style"]["fillColor"] == "#E7F1FF"

    assert status["width"] >= 5600
    assert status["height"] >= 650
    assert status["font_size"] >= 80
    assert "HEALTH: ATTENTION" not in status["content"]
    assert "🟦 MATURITY: 1 SCAFFOLD · 2 WORKING" in status["content"]
    assert "🟧 ATTENTION: 1" in status["content"]
    assert "🟩 BLOCKING: 0" in status["content"]

    assert legend["font_size"] >= 48
    assert "OTEVŘÍT PROJEKTOVÝ ARTIFACT REGISTRY" in legend["content"]
    assert "source of truth" in legend["content"]

    _assert_inside(panel, status)
    _assert_inside(panel, legend)


def test_frame_00_color_code_is_consistent_in_status_and_legend():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    status = updates["3458764679756523219"]["content"]
    legend = updates["3458764679756523220"]["content"]
    palette = manifest["health_palette"]

    assert palette == {
        "maturity": "#2F80ED",
        "attention": "#F2994A",
        "blocking_clear": "#27AE60",
        "blocking_active": "#EB5757",
    }
    for marker in ("🟦 MATURITY", "🟧 ATTENTION", "🟩 BLOCKING"):
        assert marker in status
        assert marker in legend
    assert "🟥 BLOCKING &gt; 0" in legend


def test_frame_00_status_is_not_duplicated_or_mixed_with_legend():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    panel = updates["3458764679756523217"]["content"]
    status = updates["3458764679756523219"]["content"]
    legend = updates["3458764679756523220"]["content"]

    assert "MATURITY:" not in panel
    assert "ATTENTION:" not in panel
    assert "BLOCKING:" not in panel
    assert "znamená" not in status
    assert "popisuje" not in status
    assert "HEALTH: ATTENTION" not in status
    assert status.count("ATTENTION: 1") == 1
    assert status.count("BLOCKING: 0") == 1
    assert "znamená" in legend or "popisuje" in legend


def test_frame_00_readability_regression_guard():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    panel = updates["3458764679756523217"]
    status = updates["3458764679756523219"]
    legend = updates["3458764679756523220"]

    assert (panel["x"], status["x"], legend["x"]) == (3500, 3500, 3500)
    assert min(panel["width"], status["width"], legend["width"]) >= 5600
    assert min(panel["font_size"], status["font_size"], legend["font_size"]) >= 48
    assert status["font_size"] > panel["font_size"] > legend["font_size"] - 1
    assert panel["style"]["borderColor"] == "#4B79A1"
    assert status["style"]["fillColor"] == "#FFFFFF"
    assert status["style"]["textAlign"] == "center"
    assert not (
        panel["width"] == 3400
        and status["width"] == 2600
        and panel["y"] == status["y"]
    )
