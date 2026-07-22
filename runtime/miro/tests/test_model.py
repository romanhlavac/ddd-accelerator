from pathlib import Path

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


def test_unmanaged_item_is_ignored():
    assert remote_semantic({"data": {"content": "Workshop note"}}, "life-insurance") is None


def test_scaffold_instruction_marker_is_not_a_domain_artifact():
    content = "<p>Instructions</p><p><small>DDDA-SCAFFOLD:life-insurance:align-intake:instructions</small></p>"
    assert remote_semantic({"data": {"content": content}}, "life-insurance") is None
