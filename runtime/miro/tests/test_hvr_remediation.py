from __future__ import annotations

from pathlib import Path

from ddda_miro.hvr_remediation import _load, _native_payload, _same_item, _verify_registry


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "scaffolds" / "miro" / "rem-012-3-hvr-remediation.yaml"


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
