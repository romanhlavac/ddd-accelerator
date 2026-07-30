from pathlib import Path
import shutil

import pytest

from ddda_miro.config import ProjectConfig
from ddda_miro.render import (
    CANONICAL_SHELL_FRAME_IDS,
    _workshop_shell_layout,
    assert_utf8_contract,
    render_board,
    validate_layout_contract,
    validate_remote_layout,
)
from ddda_miro.yamlio import load_yaml, save_yaml


class FakeClient:
    def __init__(self):
        self.items = {}
        self.connectors = {}
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

    def list_items(self, board_id, item_type=None):
        items = list(self.items.values())
        if item_type is None:
            return items
        return [item for item in items if item.get("type") == item_type]

    def delete_item(self, board_id, item_id):
        self.items.pop(item_id, None)

    def create_connector(self, board_id, payload):
        connector_id = f"connector-{len(self.connectors) + 1}"
        connector = {"id": connector_id, "type": "connector", **payload}
        self.connectors[connector_id] = connector
        self.created.append(("connector", connector_id))
        return connector

    def update_connector(self, board_id, connector_id, payload):
        connector = {"id": connector_id, "type": "connector", **payload}
        self.connectors[connector_id] = connector
        self.updated.append(("connector", connector_id))
        return connector

    def list_connectors(self, board_id):
        return list(self.connectors.values())

    def delete_connector(self, board_id, connector_id):
        self.connectors.pop(connector_id, None)


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
    assert result["canonical_workshop_shell_count"] == 15
    assert result["stage_column_count"] == 8

    frame_by_id = {frame["id"]: frame for frame in scaffold["frames"]}
    canonical_ids = [
        frame["id"] for frame in scaffold["frames"]
        if frame.get("canonical_workshop_shell") is True
    ]
    assert canonical_ids == CANONICAL_SHELL_FRAME_IDS
    assert "canonical_workshop_shell" not in frame_by_id["method-overview"]
    assert "canonical_workshop_shell" not in frame_by_id["align-intake"]
    align_shell = _workshop_shell_layout(frame_by_id["align-intake"])
    assert align_shell["guide"]["x"] == pytest.approx(-1860)
    assert align_shell["guide"]["y"] == pytest.approx(-1500)
    assert align_shell["guide"]["width"] == pytest.approx(2040)
    assert align_shell["example"] == pytest.approx({
        "x": 1080,
        "y": 30,
        "width": 3480,
        "height": 4380,
    })
    owned_frames = [
        frame_id
        for column in scaffold["stage_columns"]
        for frame_id in column["frames"]
    ]
    assert sorted(owned_frames) == sorted(
        frame["id"] for frame in scaffold["frames"] if frame.get("role") != "overview"
    )
    assert len(owned_frames) == len(set(owned_frames))

    registry = scaffold["artifact_status_tables"]
    assert [item["id"] for item in registry["statuses"]] == [
        "scaffold", "working", "candidate", "validated", "accepted", "superseded",
    ]
    assert [item["id"] for item in registry["provenance_values"]] == [
        "generated", "workshop", "imported", "manual",
    ]
    assert [item["id"] for item in registry["registry_columns"]] == [
        "artifact", "type", "stage", "lifecycle", "provenance",
        "owner", "revision", "last_sync", "detail",
    ]


def test_render_creates_control_center_journey_legends_and_is_idempotent(tmp_path):
    config = build_config(tmp_path)
    client = FakeClient()

    first = render_board(config, client, create_board=False, dry_run=False)
    assert first["layout_contract_status"] == "PASS"
    assert first["remote_layout_status"] == "PASS"
    assert first["remote_layout_evidence"]["journey_card_count"] == 8
    assert first["remote_layout_evidence"]["gate_marker_count"] == 8
    assert first["remote_layout_evidence"]["stage_visual_count"] >= 32
    assert first["remote_layout_evidence"]["workshop_example_count"] >= 45
    assert first["remote_layout_evidence"]["example_panel_count"] == 16
    assert first["remote_layout_evidence"]["workshop_workspace_count"] == 15
    assert first["remote_layout_evidence"]["zone_header_count"] == 4
    assert first["remote_layout_evidence"]["zone_transition_count"] == 3
    assert first["remote_layout_evidence"]["transition_count"] >= 17
    assert first["remote_layout_evidence"]["navigation_connector_count"] >= 20
    assert first["remote_layout_evidence"]["artifact_registry_cell_count"] == 45
    assert first["remote_layout_evidence"]["state_lifecycle_provenance_separation"] == "PASS"
    assert first["utf8_status"] == "PASS"
    assert first["human_visual_acceptance_status"] == "PENDING"
    assert first["overall_status"] == "PENDING_HUMAN_REVIEW"

    mapping = load_yaml(config.root / "miro" / "miro-map.yaml")
    assert mapping["frames"]["control-center"]["miro_item_id"]
    assert mapping["items"]["control-center:summary"]["system_item"] is True
    assert len([key for key in mapping["items"] if key.startswith("journey:G")]) == 8
    assert len([key for key in mapping["items"] if key.startswith("gate-marker:G")]) == 8
    assert len([key for key in mapping["items"] if key.startswith("legend:")]) == 5
    assert len([key for key in mapping["items"] if key.startswith("stage-visual:G")]) >= 32
    assert len([key for key in mapping["items"] if key.startswith("example:")]) >= 45
    assert len([key for key in mapping["items"] if key.startswith("example-panel:")]) == 16
    assert len([key for key in mapping["items"] if key.startswith("workspace-panel:")]) == 15
    assert "workspace-panel:align-intake" not in mapping["items"]
    assert len([key for key in mapping["items"] if key.startswith("transition:")]) >= 9
    assert len([key for key in mapping["items"] if key.startswith("stage-gate:")]) == 8
    assert len([key for key in mapping["items"] if key.startswith("zone-transition:")]) == 3
    assert mapping["remote_layout_status"] == "PASS"
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


def test_render_removes_legacy_artifact_status_projection(tmp_path):
    config = build_config(tmp_path)
    client = FakeClient()
    render_board(config, client, create_board=False, dry_run=False)
    mapping_path = config.root / "miro" / "miro-map.yaml"
    mapping = load_yaml(mapping_path)
    legacy_remote_id = "shape-legacy-artifact-status"
    client.items[legacy_remote_id] = {
        "id": legacy_remote_id,
        "type": "shape",
        "data": {"content": "legacy"},
        "position": {"x": 0, "y": 0},
        "geometry": {"width": 100, "height": 100},
        "style": {"fontSize": 18},
    }
    mapping["items"]["artifact-table:workshop:body"] = {
        "miro_item_id": legacy_remote_id,
        "item_type": "shape",
        "frame_id": "control-center",
        "managed": False,
        "system_item": True,
        "role": "artifact_status_table",
        "sync_policy": "ignore",
        "exclude_from_ingestion": True,
    }
    save_yaml(mapping_path, mapping)

    result = render_board(config, client, create_board=False, dry_run=False)
    updated = load_yaml(mapping_path)
    assert "artifact-table:workshop:body" not in updated["items"]
    assert legacy_remote_id not in client.items
    assert any(
        operation.get("action") == "delete_deprecated_system_item"
        and operation.get("item_id") == "artifact-table:workshop:body"
        for operation in result["operations"]
    )


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
    assert client.connectors == {}
    assert not (config.root / "miro" / "miro-map.yaml").exists()


def test_mojibake_is_rejected():
    with pytest.raises(ValueError, match="UTF-8 contract"):
        assert_utf8_contract({"title": "StrategickĂˇ klasifikace"}, label="test")


def test_overlay_guard_rejects_watermark_over_work_frame(tmp_path):
    config = build_config(tmp_path)
    scaffold = load_yaml(config.scaffold_path)
    scaffold["overlays"] = [{
        "id": "developer-team", "role": "watermark",
        "x": -15000, "y": 5500, "width": 4000, "height": 2000,
    }]
    with pytest.raises(ValueError, match="overlaps work frame"):
        validate_layout_contract(scaffold)


def test_remote_layout_rejects_unreadable_journey_font(tmp_path):
    config = build_config(tmp_path)
    client = FakeClient()
    render_board(config, client, create_board=False, dry_run=False)
    scaffold = load_yaml(config.scaffold_path)
    mapping = load_yaml(config.root / "miro" / "miro-map.yaml")
    remote_id = mapping["items"]["journey:G1"]["miro_item_id"]
    client.items[remote_id]["style"]["fontSize"] = 10

    with pytest.raises(ValueError, match="below readable minimum"):
        validate_remote_layout(scaffold, mapping, client.list_items("board-1"))


def test_workshop_guides_have_links_and_examples(tmp_path):
    config = build_config(tmp_path)
    client = FakeClient()
    render_board(config, client, create_board=False, dry_run=False)
    mapping = load_yaml(config.root / "miro" / "miro-map.yaml")
    guide_entries = {key: value for key, value in mapping["items"].items() if value.get("role") == "workshop_guide"}
    assert len(guide_entries) == 16
    for entry in guide_entries.values():
        remote = client.items[entry["miro_item_id"]]
        content = remote["data"]["content"]
        assert "DDDA kuchařka" in content
        assert "Metodika DDDA" in content
        assert "DDD Starter" in content
        assert float(remote["style"]["fontSize"]) >= 26

    example_entries = [value for value in mapping["items"].values() if value.get("role") == "workshop_example"]
    assert len(example_entries) >= 45
    panel_entries = [value for value in mapping["items"].values() if value.get("role") == "workshop_example_panel"]
    assert len(panel_entries) == 16
    workspace_entries = {
        key: value for key, value in mapping["items"].items()
        if value.get("role") == "workshop_workspace_panel"
    }
    assert len(workspace_entries) == 15
    assert "workspace-panel:align-intake" not in workspace_entries
    assert all(entry.get("sync_policy") == "manual" for entry in workspace_entries.values())
    assert all(entry.get("exclude_from_ingestion") is False for entry in workspace_entries.values())

    align_guide = client.items[guide_entries["align-intake:guide"]["miro_item_id"]]["data"]["content"]
    assert "<strong>RECEPT</strong>" not in align_guide
    for frame_id in CANONICAL_SHELL_FRAME_IDS:
        content = client.items[guide_entries[f"{frame_id}:guide"]["miro_item_id"]]["data"]["content"]
        for heading in ("RECEPT", "HOTOVO KDYŽ", "OTEVŘENÉ OTÁZKY", "HEURISTIKY", "ANTI-PATTERNS"):
            assert f"<strong>{heading}</strong>" in content
    ignored_entries = [
        value for value in mapping["items"].values()
        if value.get("role") in {
            "workshop_example", "workshop_example_panel", "workshop_example_title",
            "workshop_example_connector", "stage_visual", "stage_visual_connector",
        }
    ]
    assert ignored_entries
    assert all(entry.get("sync_policy") == "ignore" for entry in ignored_entries)
    assert all(entry.get("exclude_from_ingestion") is True for entry in ignored_entries)


def test_control_center_separates_gate_state_lifecycle_and_provenance(tmp_path):
    config = build_config(tmp_path)
    client = FakeClient()
    render_board(config, client, create_board=False, dry_run=False)
    mapping = load_yaml(config.root / "miro" / "miro-map.yaml")

    roles = {
        role: [key for key, entry in mapping["items"].items() if entry.get("role") == role]
        for role in (
            "project_gate_state_title",
            "gate_state_legend",
            "artifact_lifecycle_legend",
            "artifact_provenance_legend",
            "artifact_registry_table",
        )
    }
    assert len(roles["project_gate_state_title"]) == 1
    assert len(roles["gate_state_legend"]) == 5
    assert len(roles["artifact_lifecycle_legend"]) == 1
    assert len(roles["artifact_provenance_legend"]) == 1
    assert len(roles["artifact_registry_table"]) == 45

    gate_title = client.items[
        mapping["items"]["control-center:gate-state-title"]["miro_item_id"]
    ]["data"]["content"]
    lifecycle = client.items[
        mapping["items"]["artifact-registry:lifecycle-legend"]["miro_item_id"]
    ]["data"]["content"]
    provenance = client.items[
        mapping["items"]["artifact-registry:provenance-legend"]["miro_item_id"]
    ]["data"]["content"]
    assert "PROJECT / GATE STATE" in gate_title
    for lifecycle_id in ("SCAFFOLD", "WORKING", "CANDIDATE", "VALIDATED", "ACCEPTED", "SUPERSEDED"):
        assert lifecycle_id in lifecycle
    for provenance_id in ("GENERATED", "WORKSHOP", "IMPORTED", "MANUAL"):
        assert provenance_id in provenance
    assert "PASSED" not in lifecycle
    assert "ACCEPTED" not in provenance
