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


def test_frame_00_artifact_health_is_one_readable_bottom_panel():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    panel = updates["3458764679756523217"]
    status = updates["3458764679756523219"]
    detail = updates["3458764679756523220"]

    assert panel["frame"] == status["frame"] == detail["frame"] == "control"
    assert panel["width"] >= 6000
    assert panel["height"] >= 1600
    assert panel["width"] / panel["height"] >= 3.0
    assert panel["y"] >= 3500

    assert status["width"] >= 5600
    assert status["height"] <= 600
    assert status["font_size"] >= 64
    assert "HEALTH: ATTENTION" in status["content"]
    assert "BLOCKING: 0" in status["content"]

    assert panel["font_size"] >= 48
    assert detail["font_size"] >= 48
    assert status["font_size"] > panel["font_size"]
    assert status["font_size"] > detail["font_size"]

    _assert_inside(panel, status)
    _assert_inside(panel, detail)


def test_frame_00_health_panel_explains_status_before_secondary_details():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    panel = updates["3458764679756523217"]
    status = updates["3458764679756523219"]
    detail = updates["3458764679756523220"]

    assert status["y"] < panel["y"] < detail["y"]
    assert "MATURITY:" in panel["content"]
    for maturity in (
        "SCAFFOLD",
        "WORKING",
        "CANDIDATE",
        "VALIDATED",
        "ACCEPTED",
        "SUPERSEDED",
    ):
        assert maturity in panel["content"]
    assert "ATTENTION" in panel["content"]
    assert "BLOCKING" in panel["content"]
    assert "OTEVŘÍT PROJEKTOVÝ ARTIFACT REGISTRY" in detail["content"]
    assert "source of truth" in detail["content"]


def test_frame_00_health_regression_guard_rejects_old_split_legend_layout():
    manifest = _load(MANIFEST)
    updates = {str(item["id"]): item for item in manifest["updates"]}
    panel = updates["3458764679756523217"]
    status = updates["3458764679756523219"]
    detail = updates["3458764679756523220"]

    assert (panel["x"], status["x"], detail["x"]) == (3500, 3500, 3500)
    assert min(panel["width"], status["width"], detail["width"]) >= 5600
    assert panel["font_size"] != 36
    assert status["font_size"] != 36
    assert detail["font_size"] != 36
    assert not (
        panel["width"] == 3400
        and status["width"] == 2600
        and panel["y"] == status["y"]
    )
