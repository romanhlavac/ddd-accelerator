from pathlib import Path

import pytest

from ddda_miro.model import load_artifacts, remote_semantic
from ddda_miro.yamlio import save_yaml


def test_load_artifact_and_marker_roundtrip(tmp_path: Path):
    save_yaml(tmp_path / "artifacts" / "event.yaml", {"artifact": {
        "id": "evt-policy-issued", "type": "domain_event", "name": "Policy issued",
        "description": "Policy is active", "status": "candidate", "stage": "discover",
    }})
    artifact = load_artifacts(tmp_path, "artifacts")[0]
    remote = {"data": {"content": artifact.to_miro_content("life-insurance")}}
    semantic = remote_semantic(remote, "life-insurance")
    assert semantic is not None
    assert semantic["artifact_id"] == "evt-policy-issued"
    assert semantic["artifact_type"] == "domain_event"
    assert semantic["name"] == "Policy issued"


def test_sticky_payload_uses_miro_color_enum_and_single_geometry_dimension(tmp_path: Path):
    save_yaml(tmp_path / "artifacts" / "event.yaml", {"artifact": {
        "id": "evt-policy-issued", "type": "domain_event", "name": "Policy issued",
        "description": "Policy is active", "status": "candidate", "stage": "discover",
        "miro": {
            "item_type": "sticky_note",
            "style": {"fillColor": "#F6A04D"},
            "geometry": {"width": 350, "height": 228},
        },
    }})
    artifact = load_artifacts(tmp_path, "artifacts")[0]
    payload = artifact.to_miro_payload("life-insurance", include_layout=True)
    assert payload["style"]["fillColor"] == "orange"
    assert payload["geometry"] == {"width": 350}


def test_invalid_sticky_color_is_rejected(tmp_path: Path):
    save_yaml(tmp_path / "artifacts" / "event.yaml", {"artifact": {
        "id": "evt-policy-issued", "type": "domain_event", "name": "Policy issued",
        "description": "Policy is active", "status": "candidate", "stage": "discover",
        "miro": {"item_type": "sticky_note", "style": {"fillColor": "chartreuse"}},
    }})
    artifact = load_artifacts(tmp_path, "artifacts")[0]
    with pytest.raises(ValueError, match="Unsupported Miro sticky-note fillColor"):
        artifact.to_miro_payload("life-insurance")


def test_unmanaged_item_is_ignored():
    assert remote_semantic({"data": {"content": "Workshop note"}}, "life-insurance") is None


def test_scaffold_instruction_marker_is_not_a_domain_artifact():
    content = "<p>Instructions</p><p><small>DDDA-SCAFFOLD:life-insurance:align-intake:instructions</small></p>"
    assert remote_semantic({"data": {"content": content}}, "life-insurance") is None
