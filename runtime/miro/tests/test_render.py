from pathlib import Path
import shutil

import pytest

from ddda_miro.config import ProjectConfig
from ddda_miro.render import assert_utf8_contract, render_board, validate_layout_contract
from ddda_miro.yamlio import load_yaml, save_yaml


class FakeClient:
    def __init__(self):
        self.items = {}
        self.created = []
        self.updated = []
        self.board_created = False

    def create_board(self, name, description, *, team_id=None, project_id=None):
        self.board_created = True
        return {"id": "board-created", "name": name}

    def create_item(self, board_id, item_type, payload):
        item_id = f"{item_type}-{len(self.items) + 1}"
        item = {"id": item_id, "type": item_type, **payload}
        self.items[item_id] = item
        self.created.append((item_type, item_id))
        return item

    def update_item(self, board_id, item_type, item_id, payload):
        item = {"id": item_id, "type": item_type, **payload}
        self.items[item_id] = item
        self.updated.append((item_type, item_id))
        return item


def _status_document(next_gate: str = "G1") -> dict:
    stages = ["align", "discover", "decompose", "strategize", "connect", "organize", "define", "code"]
    gates = []
    for index, stage in enumerate(stages, start=1):
        gate = f"G{index}"
        status = "passed" if index < int(next_gate[1:]) else ("ready_for_review" if gate == next_gate else "not_ready")
        gates.append({
            "gate": gate,
            "stage": stage,
            "status": status,
            "missing": [] if status != "not_ready" else [f"artifacts/{stage}/**/*.yaml"],
            "question": f"Decision question {gate}",
        })
    return {"artifact": {
        "id": "ddda.current-status", "type": "project-status", "name": "Current status",
        "description": f"Current gate {next_gate}", "status": "candidate", "stage": stages[int(next_gate[1:]) - 1],
        "current_stage": stages[int(next_gate[1:]) - 1], "next_gate": next_gate, "gates": gates,
        "decision_owner": "Business Owner", "project_commit": "a" * 40,
        "miro": {"item_type": "sticky_note", "frame_id": "control-center", "position": {"x": 0, "y": 450}, "geometry": {"width": 1200}},
    }}


def build_config(tmp_path: Path, *, board_id: str | None = "board-1") -> ProjectConfig:
    source = Path(__file__).resolve().parents[3]
    platform = tmp_path / "platform"
    project = tmp_path / "project"
    scaffold_target = platform / "scaffolds" / "miro" / "strategic-ddd-method-board.yaml"
    scaffold_target.parent.mkdir(parents=True)
    shutil.copy2(source / "scaffolds" / "miro" / "strategic-ddd-method-board.yaml", scaffold_target)
    save_yaml(project / "project.yaml", {
        "project": {"id": "life-insurance", "name": "Life", "type": "domain-discovery", "schema_version": 1},
        "ddda": {"repository": "romanhlavac/ddd-accelerator", "required_ref": "main", "lock_file": "ddda.lock.yaml"},
        "owners": {"business_owner": "Business Owner", "architecture_owner": "Architecture Owner"},
        "miro": {
            "board_id": board_id,
            "synchronization": "bidirectional",
            "scaffold": "scaffolds/miro/strategic-ddd-method-board.yaml",
        },
        "artifacts": {"canonical_source": "yaml", "root": "artifacts"},
    })
    save_yaml(project / "artifacts" / "status" / "current-status.yaml", _status_document("G1"))
    save_yaml(project / "artifacts" / "status" / "next-actions.yaml", {"artifact": {
        "id": "ddda.next-actions", "type": "next-actions", "name": "Next actions",
        "description": "Review G1", "status": "candidate", "stage": "align", "actions": ["Review G1 evidence"],
        "miro": {"item_type": "sticky_note", "frame_id": "control-center", "position": {"x": 1300, "y": 450}, "geometry": {"width": 1200}},
    }})
    return ProjectConfig.load(project, platform)


def test_real_scaffold_satisfies_layout_traceability_and_utf8_contract(tmp_path):
    config = build_config(tmp_path)
    scaffold = load_yaml(config.scaffold_path)
    result = validate_layout_contract(scaffold)
    assert result["status"] == "PASS"
    assert result["gate_count"] == 8
    assert result["traceability_count"] == 8


def test_render_creates_control_center_journey_legends_and_is_idempotent(tmp_path):
    config = build_config(tmp_path)
    client = FakeClient()

    first = render_board(config, client, create_board=False, dry_run=False)
    assert first["layout_contract_status"] == "PASS"
    assert first["utf8_status"] == "PASS"
    assert first["human_visual_acceptance_status"] == "PENDING"
    assert first["overall_status"] == "PENDING_HUMAN_REVIEW"

    mapping = load_yaml(config.root / "miro" / "miro-map.yaml")
    assert mapping["frames"]["control-center"]["miro_item_id"]
    assert mapping["items"]["control-center:summary"]["system_item"] is True
    assert len([key for key in mapping["items"] if key.startswith("journey:G")]) == 8
    assert len([key for key in mapping["items"] if key.startswith("legend:")]) == 5
    assert len(mapping["traceability"]) == 8

    created_count = len(client.created)
    first_item_ids = {key: value["miro_item_id"] for key, value in mapping["items"].items()}
    second = render_board(config, client, create_board=False, dry_run=False)
    mapping_second = load_yaml(config.root / "miro" / "miro-map.yaml")
    assert second["current_gate"] == "G1"
    assert len(client.created) == created_count
    assert len(client.updated) > 0
    assert first_item_ids == {key: value["miro_item_id"] for key, value in mapping_second["items"].items()}


def test_current_gate_highlight_changes_without_recreating_board_items(tmp_path):
    config = build_config(tmp_path)
    client = FakeClient()
    render_board(config, client, create_board=False, dry_run=False)
    mapping = load_yaml(config.root / "miro" / "miro-map.yaml")
    g1_remote_id = mapping["items"]["journey:G1"]["miro_item_id"]
    g2_remote_id = mapping["items"]["journey:G2"]["miro_item_id"]
    assert "AKTUÁLNÍ" in client.items[g1_remote_id]["data"]["content"]

    save_yaml(config.root / "artifacts" / "status" / "current-status.yaml", _status_document("G2"))
    created_count = len(client.created)
    result = render_board(config, client, create_board=False, dry_run=False)
    assert result["current_gate"] == "G2"
    assert len(client.created) == created_count
    assert "DOKONČENO" in client.items[g1_remote_id]["data"]["content"]
    assert "AKTUÁLNÍ" in client.items[g2_remote_id]["data"]["content"]


def test_render_can_create_board_and_persist_board_id(tmp_path):
    config = build_config(tmp_path, board_id=None)
    client = FakeClient()

    result = render_board(config, client, create_board=True, dry_run=False)
    assert client.board_created is True
    assert result["board_id"] == "board-created"
    assert load_yaml(config.root / "miro" / "miro-map.yaml")["board_id"] == "board-created"


def test_render_dry_run_does_not_write_and_reports_human_pending(tmp_path):
    config = build_config(tmp_path)
    client = FakeClient()

    result = render_board(config, client, create_board=False, dry_run=True)
    assert any(item["role"] == "journey_gate" for item in result["operations"] if "role" in item)
    assert result["overall_status"] == "PENDING_HUMAN_REVIEW"
    assert client.created == []
    assert not (config.root / "miro" / "miro-map.yaml").exists()


def test_mojibake_is_rejected():
    with pytest.raises(ValueError, match="UTF-8 contract"):
        assert_utf8_contract({"title": "StrategickĂˇ klasifikace"}, label="test")


def test_overlay_guard_rejects_watermark_over_work_frame(tmp_path):
    config = build_config(tmp_path)
    scaffold = load_yaml(config.scaffold_path)
    scaffold["overlays"] = [{
        "id": "developer-team", "role": "watermark",
        "x": -12500, "y": 0, "width": 4000, "height": 2000,
    }]
    with pytest.raises(ValueError, match="overlaps work frame"):
        validate_layout_contract(scaffold)
