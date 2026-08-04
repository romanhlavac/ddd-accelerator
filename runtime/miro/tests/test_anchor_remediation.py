from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ddda_miro.anchor_contract import canonical_miro_text
from ddda_miro.anchor_remediation import (
    _deletion_candidates,
    _image_manifest,
    _item_matches,
    _protected_snapshot,
    _target_payload,
    _verify_no_anchor_overlap,
    _verify_registry_item,
    _verify_registry_markdown,
    detect_board_state,
    load_manifest,
)
from ddda_miro.yamlio import load_yaml


ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = ROOT / "scaffolds" / "miro" / "rem-012-2-anchor-frames.yaml"
REGISTRY_OVERLAY_PATH = ROOT / "scaffolds" / "miro" / "rem-012-2-artifact-registry-gh-md.yaml"
REGISTRY_SCHEMA_PATH = ROOT / "schemas" / "miro-artifact-registry-projection.schema.json"


class FakeClient:
    def __init__(self, frames=None, items=None, connectors=None):
        self.frames = deepcopy(frames or {})
        self.items = deepcopy(items or [])
        self.connectors = deepcopy(connectors or [])

    def _request(self, method, path, **kwargs):
        assert method == "GET"
        if "/frames/" in path:
            return deepcopy(self.frames[path.rsplit("/", 1)[-1]])
        if "/items/" in path:
            item_id = path.rsplit("/", 1)[-1]
            return deepcopy(next(item for item in self.items if str(item["id"]) == item_id))
        raise AssertionError(path)

    def list_items(self, board_id, item_type=None):
        result = deepcopy(self.items)
        if item_type:
            result = [item for item in result if item.get("type") == item_type]
        return result

    def list_connectors(self, board_id):
        return deepcopy(self.connectors)


def frame(item_id, x, y, width, height):
    return {
        "id": item_id,
        "type": "frame",
        "data": {"title": item_id},
        "position": {"x": x, "y": y, "origin": "center"},
        "geometry": {"width": width, "height": height},
    }


def test_anchor_remediation_module_imports():
    import ddda_miro.anchor_remediation as module

    assert callable(module.main)


def test_canonical_miro_text_normalizes_html_entities_and_whitespace():
    assert canonical_miro_text(None) == ""
    assert canonical_miro_text("<p>INSPIRACE&nbsp; PRO</p><div>TEST<br/>line</div>") == "INSPIRACE PRO TEST line"
    assert canonical_miro_text("  INSPIRACE\tPRO\nTEST  ") == "INSPIRACE PRO TEST"


def test_item_matches_treats_equivalent_miro_html_as_equal():
    remote = {"data": {"content": "<p>Domain&nbsp; discovery</p>"}}
    payload = {"data": {"content": "Domain discovery"}}

    assert _item_matches(remote, payload)
    assert not _item_matches(remote, {"data": {"content": "Domain design"}})


def test_manifest_is_pinned_and_scoped_to_three_anchor_frames():
    manifest = load_manifest(MANIFEST_PATH)

    assert manifest["authorized_base_sha"] == "7badffb6ef6f3364569e68926eb511600eed38d3"
    assert set(manifest["frames"]) == {"control", "journey", "align"}
    assert len(manifest["protected_frames"]) == 15
    assert len(manifest["images"]["assets"]) == 17
    assert all(len(asset["expected_sha256"]) == 64 for asset in manifest["images"]["assets"])
    assert manifest["artifact_registry"]["mode"] == "github_markdown"
    assert manifest["artifact_registry"]["pages_backlog_issue"] == 45
    assert "table_item_id" not in manifest
    assert "table_target" not in manifest


def test_registry_overlay_contract_matches_schema_identity():
    schema = json.loads(REGISTRY_SCHEMA_PATH.read_text(encoding="utf-8"))
    overlay = load_yaml(REGISTRY_OVERLAY_PATH)
    registry = overlay["artifact_registry"]

    assert schema["$id"] == "https://ddda.local/schemas/miro-artifact-registry-projection.schema.json"
    assert set(schema["required"]) <= set(overlay)
    assert set(schema["properties"]["artifact_registry"]["required"]) <= set(registry)
    assert schema["properties"]["schema_version"]["const"] == overlay["schema_version"] == 1
    assert (
        schema["properties"]["projection_id"]["const"]
        == overlay["projection_id"]
        == "REM-PR8-HVA-CC-012.2-gh-md-v1"
    )
    assert registry["mode"] == "github_markdown"
    assert registry["title"] == "ARTIFACT HEALTH"
    assert registry["pages_backlog_issue"] == 45
    assert set(registry["expected_lifecycle_counts"]) == {
        "scaffold", "working", "candidate", "validated", "accepted", "superseded"
    }


def test_github_markdown_registry_and_miro_projection_contract():
    manifest = load_manifest(MANIFEST_PATH)
    markdown = _verify_registry_markdown(manifest)
    registry = manifest["artifact_registry"]
    control_id = manifest["frames"]["control"]["id"]
    registry_item = {
        "id": registry["miro_item_id"],
        "type": "text",
        "data": {"content": registry["content"]},
        "position": {
            "x": registry["x"],
            "y": registry["y"],
            "origin": "center",
            "relativeTo": "parent_top_left",
        },
        "geometry": {"width": registry["width"]},
        "parent": {"id": control_id},
    }
    client = FakeClient(items=[registry_item])

    assert markdown["status"] == "PASS"
    assert markdown["mode"] == "github_markdown"
    assert markdown["artifact_count"] == 3
    assert markdown["lifecycle_counts"] == {
        "scaffold": 1,
        "working": 2,
        "candidate": 0,
        "validated": 0,
        "accepted": 0,
        "superseded": 0,
    }
    assert markdown["pages_backlog_issue"] == 45
    assert _verify_registry_item(client, manifest, target=False)["target_verified"] is False
    assert _verify_registry_item(client, manifest, target=True)["target_verified"] is True

    invalid_manifest = deepcopy(manifest)
    invalid_manifest["artifact_registry"]["markdown_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="digest mismatch"):
        _verify_registry_markdown(invalid_manifest)

    invalid_item = deepcopy(registry_item)
    invalid_item["data"]["content"] = "native table"
    with pytest.raises(ValueError, match="content mismatch"):
        _verify_registry_item(FakeClient(items=[invalid_item]), manifest, target=True)


def test_image_manifest_converts_top_left_targets_to_frame_center_coordinates():
    manifest = load_manifest(MANIFEST_PATH)
    image_manifest = _image_manifest(manifest)

    first = image_manifest["assets"][0]
    bmc = image_manifest["assets"][-1]
    assert first["target"]["position"]["x"] == pytest.approx(4250 - 58008.9 / 2)
    assert first["target"]["position"]["y"] == pytest.approx(3400 - 10144.3 / 2)
    assert bmc["target"]["position"] == {"x": 1800.0, "y": -500.0}
    assert image_manifest["diagnostic_only"] is False


def test_detect_board_state_accepts_only_uniform_before_or_target_state():
    manifest = load_manifest(MANIFEST_PATH)
    before_frames = {
        spec["id"]: frame(spec["id"], **{
            "x": spec["expected_current"]["x"],
            "y": spec["expected_current"]["y"],
            "width": spec["expected_current"]["width"],
            "height": spec["expected_current"]["height"],
        })
        for spec in manifest["frames"].values()
    }
    state, _ = detect_board_state(FakeClient(frames=before_frames), manifest)
    assert state == "before"

    mixed = deepcopy(before_frames)
    align = manifest["frames"]["align"]
    mixed[align["id"]] = frame(align["id"], **align["target"])
    with pytest.raises(ValueError, match="mixed or unexpected"):
        detect_board_state(FakeClient(frames=mixed), manifest)


def test_target_payload_preserves_semantics_and_sets_top_left_relative_position():
    remote = {
        "id": "shape-1",
        "type": "shape",
        "data": {"shape": "rectangle", "content": "old"},
        "style": {"fontSize": 18, "fillColor": "#fff"},
        "geometry": {"width": 100, "height": 50},
        "position": {"x": 10, "y": 20, "origin": "center", "relativeTo": "parent_top_left"},
        "parent": {"id": "frame-1"},
    }
    payload = _target_payload(
        remote,
        {"x": 500, "y": 600, "width": 300, "height": 200, "font_size": 80, "content": "new"},
        "frame-1",
    )

    assert payload["data"] == {"shape": "rectangle", "content": "new"}
    assert payload["style"]["fontSize"] == 80
    assert payload["geometry"] == {"width": 300.0, "height": 200.0}
    assert payload["position"] == {"x": 500.0, "y": 600.0, "origin": "center", "relativeTo": "parent_top_left"}
    assert _item_matches({**remote, **deepcopy(payload)}, payload)


def test_deletion_candidates_are_fail_closed_by_expected_counts():
    manifest = load_manifest(MANIFEST_PATH)
    control_id = manifest["frames"]["control"]["id"]
    journey_id = manifest["frames"]["journey"]["id"]
    items = [
        {
            "id": f"grid-{index}",
            "type": "shape",
            "data": {"content": "grid"},
            "position": {"x": index, "y": 6500},
            "parent": {"id": control_id},
        }
        for index in range(45)
    ]
    items += [
        {
            "id": f"inspiration-{index}",
            "type": "shape",
            "data": {"content": "<p>INSPIRACE PRO TEST</p>"},
            "position": {"x": index, "y": 12000},
            "parent": {"id": journey_id},
        }
        for index in range(8)
    ]
    candidates = _deletion_candidates(FakeClient(items=items), manifest, "before")
    assert len(candidates) == 45 + 8 + 5 + 1

    with pytest.raises(ValueError, match="control obsolete grid count mismatch"):
        _deletion_candidates(FakeClient(items=items[:-9]), manifest, "before")


def test_protected_snapshot_digest_changes_when_a_child_changes():
    frames = {"frame-20": frame("frame-20", 0, 0, 1000, 800)}
    items = [{"id": "child-1", "type": "text", "data": {"content": "A"}, "parent": {"id": "frame-20"}}]
    first = _protected_snapshot(FakeClient(frames=frames, items=items), "board", ["frame-20"])
    items[0]["data"]["content"] = "B"
    second = _protected_snapshot(FakeClient(frames=frames, items=items), "board", ["frame-20"])

    assert first["digest"] != second["digest"]


def test_anchor_overlap_check_accepts_target_gaps_and_rejects_collision():
    manifest = {
        "board_id": "board",
        "frames": {
            "control": {"id": "control"},
            "journey": {"id": "journey"},
            "align": {"id": "align"},
        },
        "protected_frames": ["frame-20"],
    }
    frames = {
        "control": frame("control", -16000, 0, 7000, 4900),
        "journey": frame("journey", 9000, -8500, 58000, 10100),
        "align": frame("align", -17000, 6000, 6000, 4800),
        "frame-20": frame("frame-20", -8500, 1000, 6500, 4800),
    }
    assert _verify_no_anchor_overlap(FakeClient(frames=frames), manifest)["collision_count"] == 0

    frames["align"] = frame("align", -12000, 1000, 6000, 4800)
    with pytest.raises(ValueError, match="overlap"):
        _verify_no_anchor_overlap(FakeClient(frames=frames), manifest)
