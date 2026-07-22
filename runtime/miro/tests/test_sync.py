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
