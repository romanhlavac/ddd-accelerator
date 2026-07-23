from pathlib import Path

from ddda_miro.config import ProjectConfig
from ddda_miro.render import render_board
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


def build_config(tmp_path: Path, *, board_id: str | None = "board-1") -> ProjectConfig:
    platform = tmp_path / "platform"
    project = tmp_path / "project"
    save_yaml(platform / "scaffolds" / "miro" / "board.yaml", {
        "id": "test-scaffold",
        "palette": {"frame_background": "#F8FAFC"},
        "frames": [{
            "id": "align-intake",
            "title_cs": "Align / Intake",
            "stage": "align",
            "x": 100,
            "y": 200,
            "width": 2400,
            "height": 1800,
            "scaffold": ["goal", "scope", "gate"],
        }],
    })
    save_yaml(project / "project.yaml", {
        "project": {"id": "life-insurance", "name": "Life", "type": "portfolio-program", "schema_version": 1},
        "ddda": {"repository": "romanhlavac/ddd-accelerator", "required_ref": "main", "lock_file": "ddda.lock.yaml"},
        "miro": {
            "board_id": board_id,
            "synchronization": "bidirectional",
            "scaffold": "scaffolds/miro/board.yaml",
        },
        "artifacts": {"canonical_source": "yaml", "root": "artifacts"},
    })
    return ProjectConfig.load(project, platform)


def test_render_creates_mapping_and_is_idempotent(tmp_path):
    config = build_config(tmp_path)
    client = FakeClient()

    first = render_board(config, client, create_board=False, dry_run=False)
    assert first["operation_count"] == 1
    assert len(client.created) == 2

    mapping = load_yaml(config.root / "miro" / "miro-map.yaml")
    assert mapping["frames"]["align-intake"]["miro_item_id"]
    assert mapping["items"]["align-intake:instructions"]["system_item"] is True

    second = render_board(config, client, create_board=False, dry_run=False)
    assert second["operations"][0]["action"] == "update_frame"
    assert len(client.created) == 2
    assert len(client.updated) == 2


def test_render_can_create_board_and_persist_board_id(tmp_path):
    config = build_config(tmp_path, board_id=None)
    client = FakeClient()

    result = render_board(config, client, create_board=True, dry_run=False)
    assert client.board_created is True
    assert result["board_id"] == "board-created"
    assert load_yaml(config.root / "miro" / "miro-map.yaml")["board_id"] == "board-created"


def test_render_dry_run_does_not_write(tmp_path):
    config = build_config(tmp_path)
    client = FakeClient()

    result = render_board(config, client, create_board=False, dry_run=True)
    assert result["operations"][0]["action"] == "create_frame"
    assert client.created == []
    assert not (config.root / "miro" / "miro-map.yaml").exists()
