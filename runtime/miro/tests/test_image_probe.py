from __future__ import annotations

from pathlib import Path

from ddda_miro.client import MiroApiError
from ddda_miro.config import ProjectConfig
from ddda_miro.image_probe import run_probe


class FakeClient:
    access_token = "token"
    timeout_seconds = 5

    def __init__(self):
        self.board_exists = False
        self.images: list[dict] = []
        self.frames: dict[str, dict] = {}
        self.next_frame_id = 1
        self.next_image_id = 1

    def create_board(self, name, description, *, team_id=None, project_id=None):
        self.board_exists = True
        return {"id": "diagnostic-board", "name": name}

    def get_board(self, board_id):
        if not self.board_exists:
            raise MiroApiError(404, "GET", f"boards/{board_id}", "not found")
        return {"id": board_id}

    def create_item(self, board_id, item_type, payload):
        assert item_type == "frame"
        item_id = f"frame-{self.next_frame_id}"
        self.next_frame_id += 1
        remote = {"id": item_id, "type": "frame", **payload}
        self.frames[item_id] = remote
        return remote

    def list_items(self, board_id, item_type=None):
        assert item_type == "image"
        return list(self.images)

    def _frame_geometry(self, board_id, frame_id):
        return self.frames[frame_id]["geometry"]

    def _prepare_item_payload(self, board_id, item_type, payload):
        prepared = {key: value for key, value in payload.items() if key != "_ddda_bounds_geometry"}
        prepared["position"] = {"x": 1400.0, "y": 950.0, "origin": "center"}
        return prepared

    def _request(self, method, path, **kwargs):
        if method == "GET" and "/items/source-image" in path:
            return {
                "id": "source-image",
                "type": "image",
                "parent": {"id": "source-frame"},
                "geometry": {"width": 1000, "height": 500},
                "data": {"imageUrl": "https://api.miro.com/resource"},
            }
        if method == "GET" and "/items/" in path:
            item_id = path.rsplit("/", 1)[1]
            return next(item for item in self.images if item["id"] == item_id)
        if method == "POST" and path.endswith("/images"):
            remote = {
                "id": f"image-{self.next_image_id}",
                "type": "image",
                **kwargs["body"],
            }
            self.next_image_id += 1
            self.images.append(remote)
            return remote
        if method == "PATCH" and "/images/" in path:
            item_id = path.rsplit("/", 1)[1]
            remote = {"id": item_id, "type": "image", **kwargs["body"]}
            self.images[self.images.index(next(item for item in self.images if item["id"] == item_id))] = remote
            return remote
        if method == "DELETE" and path.startswith("boards/"):
            self.board_exists = False
            return None
        raise AssertionError((method, path, kwargs))


def _write_manifest(path: Path) -> None:
    path.write_text(
        """schema_version: 1
manifest_id: test-image-probe
diagnostic_only: true
board:
  name: Test image probe
  description: Test
frames:
  - id: target
    title: Target
    position: {x: 0, y: 0}
    geometry: {width: 2800, height: 1900}
assets:
  - id: asset
    usage: test
    source:
      board_id: source-board
      frame_id: source-frame
      item_id: source-image
      title: Source
    target:
      frame_id: target
      position: {x: 0, y: 0}
      width: 2200
""",
        encoding="utf-8",
    )


def test_run_probe_verifies_remote_images_second_run_and_cleanup(tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.yaml"
    _write_manifest(manifest_path)
    config = ProjectConfig(
        root=tmp_path,
        platform_root=tmp_path,
        raw={},
        project_id="test",
        name="Test",
        artifact_root="artifacts",
        board_id=None,
        board_id_env=None,
        token_env="MIRO_ACCESS_TOKEN",
        team_id="team",
        miro_project_id=None,
        scaffold_path=manifest_path,
        conflict_policy="manual-review",
        synchronization="disabled",
    )
    client = FakeClient()
    monkeypatch.setattr(
        "ddda_miro.image_transport.source_image",
        lambda client, board, item_id: (
            b"synthetic-image-bytes",
            "image/png",
            {
                "id": item_id,
                "type": "image",
                "parent": {"id": "source-frame"},
                "geometry": {"width": 1000, "height": 500},
            },
        ),
    )

    report = run_probe(config, client, manifest_path)

    assert report["status"] == "PASS"
    assert report["first_run"]["created"] == 1
    assert report["second_run"] == {
        "created": 0,
        "updated": 0,
        "unchanged": 1,
        "assets": report["second_run"]["assets"],
    }
    assert report["remote_verification"]["status"] == "PASS"
    assert report["remote_verification"]["second_run"]["items"][0]["remote_type"] == "image"
    assert report["remote_verification"]["second_run"]["items"][0]["source_item_id"] == "source-image"
    assert report["stable_item_ids"] is True
    assert report["zero_mutation_second_run"] is True
    assert report["cleanup"] == {"state": "deleted", "verified": True, "attempts": 1}
    assert client.board_exists is False
