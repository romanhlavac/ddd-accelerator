from __future__ import annotations

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
    detect_board_state,
    load_manifest,
)


MANIFEST_PATH = Path(__file__).resolve().parents[3] / "scaffolds" / "miro" / "rem-012-2-anchor-frames.yaml"


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
