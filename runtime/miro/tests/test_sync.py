from pathlib import Path

from ddda_miro.config import ProjectConfig
from ddda_miro.sync import sync_project
from ddda_miro.yamlio import load_yaml, save_yaml


class FakeClient:
    def __init__(self):
        self.items = []
        self.created = []
        self.deleted = []

    def list_items(self, board_id):
        return list(self.items)

    def create_item(self, board_id, item_type, payload):
        item = {"id": f"item-{len(self.items)+1}", "type": item_type, **payload}
        self.items.append(item)
        self.created.append(item)
        return item

    def update_item(self, board_id, item_type, item_id, payload):
        item = next(value for value in self.items if value["id"] == item_id)
        item.update(payload)
        return item

    def delete_item(self, board_id, item_id):
        self.items = [value for value in self.items if value["id"] != item_id]
        self.deleted.append(item_id)


def build_project(tmp_path: Path) -> ProjectConfig:
    save_yaml(tmp_path / "project.yaml", {
        "project": {"id": "life-insurance", "name": "Life", "type": "portfolio-program", "schema_version": 1},
        "ddda": {"repository": "romanhlavac/ddd-accelerator", "required_ref": "main", "lock_file": "ddda.lock.yaml"},
        "miro": {"board_id": "board-1", "synchronization": "bidirectional", "access_token_env": "MIRO_ACCESS_TOKEN"},
        "artifacts": {"canonical_source": "yaml", "root": "artifacts", "conflict_policy": "manual-review"},
    })
    save_yaml(tmp_path / "artifacts" / "discover" / "event.yaml", {"artifact": {
        "id": "evt-policy-issued", "type": "domain_event", "name": "Policy issued",
        "description": "Policy is active", "status": "candidate", "stage": "discover",
        "miro": {"frame_id": "discover-big-picture-es"},
    }})
    return ProjectConfig.load(tmp_path)


def test_push_creates_managed_item(tmp_path):
    config = build_project(tmp_path)
    client = FakeClient()
    result = sync_project(config, client, direction="push", dry_run=False, include_layout=False, confirm_delete=False)
    assert result["conflict_count"] == 0
    assert len(client.created) == 1
    assert (tmp_path / "miro" / "miro-map.yaml").exists()
    assert (tmp_path / "miro" / "sync-state.yaml").exists()


def test_dry_run_does_not_write(tmp_path):
    config = build_project(tmp_path)
    client = FakeClient()
    result = sync_project(config, client, direction="push", dry_run=True, include_layout=False, confirm_delete=False)
    assert result["operation_count"] == 1
    assert not (tmp_path / "miro" / "miro-map.yaml").exists()


def test_pull_does_not_mark_unpushed_local_change_as_synced(tmp_path):
    config = build_project(tmp_path)
    client = FakeClient()
    sync_project(config, client, direction="push", dry_run=False, include_layout=False, confirm_delete=False)
    state_before = load_yaml(tmp_path / "miro" / "sync-state.yaml")
    event_path = tmp_path / "artifacts" / "discover" / "event.yaml"
    changed = load_yaml(event_path)
    changed["artifact"]["name"] = "Locally changed policy event"
    save_yaml(event_path, changed)
    sync_project(config, client, direction="pull", dry_run=False, include_layout=False, confirm_delete=False)
    state_after = load_yaml(tmp_path / "miro" / "sync-state.yaml")
    assert state_after["items"]["evt-policy-issued"]["local_hash"] == state_before["items"]["evt-policy-issued"]["local_hash"]


def test_missing_mapped_local_artifact_requires_explicit_resolution(tmp_path):
    config = build_project(tmp_path)
    client = FakeClient()
    sync_project(config, client, direction="push", dry_run=False, include_layout=False, confirm_delete=False)
    (tmp_path / "artifacts" / "discover" / "event.yaml").unlink()
    result = sync_project(config, client, direction="both", dry_run=True, include_layout=False, confirm_delete=False)
    assert result["conflict_count"] == 1
    assert result["operations"][0]["reason"] == "mapped_local_artifact_missing"


def test_project_config_reuses_board_id_from_mapping(tmp_path):
    save_yaml(tmp_path / "project.yaml", {
        "project": {"id": "life-insurance", "name": "Life", "type": "portfolio-program", "schema_version": 1},
        "ddda": {"repository": "romanhlavac/ddd-accelerator", "required_ref": "main", "lock_file": "ddda.lock.yaml"},
        "miro": {"board_id": None, "synchronization": "bidirectional"},
        "artifacts": {"canonical_source": "yaml", "root": "artifacts"},
    })
    save_yaml(tmp_path / "miro" / "miro-map.yaml", {"board_id": "board-from-map"})
    assert ProjectConfig.load(tmp_path).board_id == "board-from-map"


def test_explicit_promotion_creates_yaml_for_new_marked_miro_item(tmp_path):
    config = build_project(tmp_path)
    client = FakeClient()
    client.items.append({
        "id": "item-new",
        "type": "sticky_note",
        "data": {"content": (
            "<p><strong>Medical evidence is incomplete</strong></p>"
            "<p>Owner must clarify the evidence threshold.</p>"
            "<p><small>Typ: hotspot</small></p>"
            "<p><small>Stav: candidate</small></p>"
            "<p><small>Fáze: discover</small></p>"
            "<p><small>DDDA:life-insurance:hotspot-medical-evidence</small></p>"
        )},
    })
    result = sync_project(
        config, client, direction="pull", dry_run=False, include_layout=False,
        confirm_delete=False, promote_new=True,
    )
    assert any(item["action"] == "pull_promote_yaml" for item in result["operations"])
    created = tmp_path / "artifacts" / "discover" / "hotspot" / "hotspot-medical-evidence.yaml"
    assert created.exists()
    assert load_yaml(created)["artifact"]["type"] == "hotspot"


def build_steering_project(tmp_path: Path) -> ProjectConfig:
    config = build_project(tmp_path)
    save_yaml(tmp_path / "miro" / "miro-map.yaml", {
        "schema_version": 1,
        "project_id": "life-insurance",
        "board_id": "board-1",
        "layout_contract_status": "PASS",
        "utf8_status": "PASS",
        "human_visual_acceptance_status": "PENDING",
        "overall_status": "PENDING_HUMAN_REVIEW",
        "frames": {"control-center": {"miro_item_id": "frame-control"}},
        "items": {},
    })
    for path, artifact_id, artifact_type, x, color in [
        ("align/project-charter.yaml", "life-insurance.project-charter", "project-charter", -1200, "light_yellow"),
        ("status/current-status.yaml", "ddda.current-status", "project-status", 0, "light_blue"),
        ("status/next-actions.yaml", "ddda.next-actions", "next-actions", 1300, "light_green"),
    ]:
        save_yaml(tmp_path / "artifacts" / path, {"artifact": {
            "id": artifact_id, "type": artifact_type, "name": artifact_id,
            "description": "Řízený český obsah", "status": "candidate", "stage": "align",
            "miro": {
                "item_type": "sticky_note", "frame_id": "control-center",
                "position": {"x": x, "y": 450, "origin": "center"},
                "geometry": {"width": 1100}, "style": {"fillColor": color},
            },
        }})
    return ProjectConfig.load(tmp_path)


def test_required_steering_artifacts_are_placed_in_control_center_and_report_human_pending(tmp_path):
    config = build_steering_project(tmp_path)
    client = FakeClient()
    result = sync_project(config, client, direction="push", dry_run=False, include_layout=False, confirm_delete=False)
    assert result["technical_sync_status"] == "PASS"
    assert result["layout_contract_status"] == "PASS"
    assert result["utf8_status"] == "PASS"
    assert result["human_visual_acceptance_status"] == "PENDING"
    assert result["overall_status"] == "PENDING_HUMAN_REVIEW"
    mapping = load_yaml(tmp_path / "miro" / "miro-map.yaml")
    for artifact_id in ["life-insurance.project-charter", "ddda.current-status", "ddda.next-actions"]:
        assert mapping["items"][artifact_id]["frame_id"] == "control-center"
        assert "x" in mapping["items"][artifact_id]["position"]
        assert "y" in mapping["items"][artifact_id]["position"]
        remote = next(item for item in client.items if item["id"] == mapping["items"][artifact_id]["miro_item_id"])
        assert remote["parent"]["id"] == "frame-control"
    report = load_yaml(next((tmp_path / "reports" / "miro-sync").glob("sync-*.yaml")))
    assert report["technical_sync_status"] == "PASS"
    assert report["overall_status"] == "PENDING_HUMAN_REVIEW"


def test_required_steering_artifact_without_placement_is_rejected(tmp_path):
    config = build_steering_project(tmp_path)
    path = tmp_path / "artifacts" / "status" / "current-status.yaml"
    document = load_yaml(path)
    document["artifact"]["miro"]["frame_id"] = None
    save_yaml(path, document)
    client = FakeClient()
    import pytest
    with pytest.raises(ValueError, match="frame_id must be control-center"):
        sync_project(config, client, direction="push", dry_run=True, include_layout=False, confirm_delete=False)


def test_mojibake_in_managed_artifact_is_rejected(tmp_path):
    config = build_steering_project(tmp_path)
    path = tmp_path / "artifacts" / "status" / "next-actions.yaml"
    document = load_yaml(path)
    document["artifact"]["description"] = "StrategickĂˇ klasifikace"
    save_yaml(path, document)
    client = FakeClient()
    import pytest
    with pytest.raises(ValueError, match="UTF-8 contract"):
        sync_project(config, client, direction="push", dry_run=True, include_layout=False, confirm_delete=False)


def test_status_change_does_not_overwrite_existing_manual_layout_without_explicit_flag(tmp_path):
    config = build_project(tmp_path)
    event_path = tmp_path / "artifacts" / "discover" / "event.yaml"
    document = load_yaml(event_path)
    document["artifact"]["miro"]["position"] = {"x": 100, "y": 200, "origin": "center"}
    document["artifact"]["miro"]["geometry"] = {"width": 350}
    save_yaml(event_path, document)
    client = FakeClient()
    sync_project(config, client, direction="push", dry_run=False, include_layout=False, confirm_delete=False)
    mapping = load_yaml(tmp_path / "miro" / "miro-map.yaml")
    remote_id = mapping["items"]["evt-policy-issued"]["miro_item_id"]
    remote = next(item for item in client.items if item["id"] == remote_id)
    assert remote["position"]["x"] == 100

    changed = load_yaml(event_path)
    changed["artifact"]["name"] = "Policy issued after status change"
    changed["artifact"]["miro"]["position"]["x"] = 9999
    save_yaml(event_path, changed)
    sync_project(config, client, direction="push", dry_run=False, include_layout=False, confirm_delete=False)
    remote_after = next(item for item in client.items if item["id"] == remote_id)
    assert remote_after["position"]["x"] == 100


def test_secret_is_not_written_to_mapping_state_or_report(tmp_path, monkeypatch):
    secret = "miro-secret-token-never-persist"
    monkeypatch.setenv("MIRO_ACCESS_TOKEN", secret)
    config = build_steering_project(tmp_path)
    client = FakeClient()
    sync_project(config, client, direction="push", dry_run=False, include_layout=False, confirm_delete=False)
    persisted = "\n".join(
        path.read_text(encoding="utf-8-sig")
        for path in [
            tmp_path / "miro" / "miro-map.yaml",
            tmp_path / "miro" / "sync-state.yaml",
            next((tmp_path / "reports" / "miro-sync").glob("sync-*.yaml")),
        ]
    )
    assert secret not in persisted


def test_sync_explicitly_ignores_example_panel_and_connector_entries(tmp_path):
    config = build_project(tmp_path)
    save_yaml(tmp_path / "miro" / "miro-map.yaml", {
        "schema_version": 1,
        "project_id": "life-insurance",
        "board_id": "board-1",
        "frames": {},
        "items": {
            "example-panel:discover-big-picture-es": {
                "miro_item_id": "shape-example-panel",
                "item_type": "shape",
                "system_item": False,
                "sync_policy": "ignore",
                "exclude_from_ingestion": True,
            },
            "example-connector:discover-big-picture-es:timeline": {
                "miro_item_id": "connector-example",
                "item_type": "connector",
                "system_item": False,
                "sync_policy": "ignore",
                "exclude_from_ingestion": True,
            },
        },
    })
    client = FakeClient()
    result = sync_project(
        config, client, direction="both", dry_run=True,
        include_layout=False, confirm_delete=False, promote_new=True,
    )
    ignored_ids = {
        "example-panel:discover-big-picture-es",
        "example-connector:discover-big-picture-es:timeline",
    }
    assert not any(operation.get("artifact_id") in ignored_ids for operation in result["operations"])
