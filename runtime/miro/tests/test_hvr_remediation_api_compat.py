from __future__ import annotations

from pathlib import Path

import pytest

import ddda_miro.hvr_remediation_api_compat as compat
from ddda_miro.hvr_remediation_api_compat import (
    ALIGN_ONBOARDING_NATIVE_COUNT,
    ALIGN_ONBOARDING_PINNED_IMAGE_ID,
    ALIGN_ONBOARDING_PINNED_SOURCE_ITEM_ID,
    REPLACED_ITEM_TYPES,
    REPLACED_STICKY_ITEM_TOKENS,
    REPLACED_TEXT_ITEM_ID,
    _compat_clone_native_set,
    _compat_load,
    _compat_same_item,
    _replacement_payload,
    _sticky_replacement_matches,
)

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "scaffolds" / "miro" / "rem-012-3-hvr-remediation.yaml"


def test_compat_contract_replaces_only_known_incompatible_items():
    manifest = _compat_load(MANIFEST)
    updates = {str(item.get("id") or ""): item for item in manifest["updates"]}
    assert set(REPLACED_ITEM_TYPES) == {
        REPLACED_TEXT_ITEM_ID,
        *REPLACED_STICKY_ITEM_TOKENS,
    }
    for item_id, item_type in REPLACED_ITEM_TYPES.items():
        assert updates[item_id]["type"] == item_type
        assert updates[item_id]["replace_by_create"] is True
        assert manifest["cleanup_ids"].count(item_id) == 1


def test_effective_onboarding_contract_is_seven_native_plus_one_pinned_image():
    manifest = _compat_load(MANIFEST)
    clones = {str(item["name"]): item for item in manifest["native_clones"]}
    assert int(clones["align-onboarding"]["expected_supported_count"]) == ALIGN_ONBOARDING_NATIVE_COUNT == 7
    assert int(clones["filled-bmc-example"]["expected_supported_count"]) == 121
    assert sum(int(item["expected_supported_count"]) for item in manifest["native_clones"]) == 128

    images = {str(item["id"]): item for item in manifest["images"]["assets"]}
    pinned = images[ALIGN_ONBOARDING_PINNED_IMAGE_ID]
    assert pinned["source_item_id"] == ALIGN_ONBOARDING_PINNED_SOURCE_ITEM_ID
    assert pinned["source_frame_id"] == clones["align-onboarding"]["source_frame_id"]
    assert pinned["target_frame"] == "align"


def test_native_clone_readback_normalizes_numeric_style_wire_values():
    expected = {
        "data": {"shape": "rectangle", "content": ""},
        "style": {
            "fillColor": "#ffffff",
            "fillOpacity": 1.0,
            "fontFamily": "open_sans",
            "fontSize": 10,
            "borderColor": "#1a1a1a",
            "borderWidth": 2.0,
            "borderOpacity": 1.0,
            "borderStyle": "normal",
            "textAlign": "center",
            "textAlignVertical": "middle",
            "color": "#1a1a1a",
        },
        "geometry": {"width": 443.647385164374, "height": 127.0344010467848},
        "position": {"x": 1016.9127484844867, "y": 1092.502978996201, "origin": "center"},
        "parent": {"id": "align-frame"},
    }
    remote = {
        "data": {"shape": "rectangle", "content": ""},
        "style": {
            **expected["style"],
            "fillOpacity": "1.0",
            "fontSize": "10",
            "borderWidth": "2.0",
            "borderOpacity": "1.0",
        },
        "geometry": expected["geometry"],
        "position": {
            **expected["position"],
            "relativeTo": "parent_top_left",
        },
        "parent": {"id": "align-frame"},
    }
    assert _compat_same_item(remote, expected)
    remote["style"]["borderWidth"] = "3.0"
    assert not _compat_same_item(remote, expected)


def test_failed_native_clone_removes_items_created_before_verification(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.read_count = 0
            self.deleted: list[tuple[str, str]] = []

        def list_items(self, board: str):
            self.read_count += 1
            original = {
                "id": "existing",
                "type": "shape",
                "parent": {"id": "align-frame"},
            }
            orphan = {
                "id": "orphan",
                "type": "shape",
                "parent": {"id": "align-frame"},
            }
            return [original] if self.read_count == 1 else [original, orphan]

        def delete_item(self, board: str, item_id: str):
            self.deleted.append((board, item_id))

    def fail_after_create(client, manifest, clone):
        raise ValueError("created item did not reach target")

    monkeypatch.setattr(compat, "_ORIGINAL_CLONE_NATIVE_SET", fail_after_create)
    client = FakeClient()
    manifest = {
        "board_id": "target-board",
        "frames": {"align": {"id": "align-frame"}},
        "cleanup_ids": [],
    }
    clone = {"target_frame": "align"}
    with pytest.raises(ValueError, match="did not reach target"):
        _compat_clone_native_set(client, manifest, clone)
    assert client.deleted == [("target-board", "orphan")]


def test_text_replacement_payload_is_readable_and_frame_scoped():
    manifest = _compat_load(MANIFEST)
    update = next(item for item in manifest["updates"] if str(item.get("id") or "") == REPLACED_TEXT_ITEM_ID)
    payload = _replacement_payload("control-frame", update)
    assert payload["parent"] == {"id": "control-frame"}
    assert payload["style"]["fontSize"] == 36
    assert payload["style"]["fontFamily"] == "arial"
    assert payload["geometry"] == {"width": 3000.0}
    assert payload["position"] == {"x": 5200.0, "y": 700.0, "origin": "center"}
    assert "Miro ani technický PASS gate neschvalují" in payload["data"]["content"]


def test_sticky_replacement_payload_preserves_content_and_uses_target_geometry():
    manifest = _compat_load(MANIFEST)
    item_id = "3458764679756548469"
    update = next(item for item in manifest["updates"] if str(item.get("id") or "") == item_id)
    original = {
        "id": item_id,
        "type": "sticky_note",
        "data": {
            "content": "<p>DDDA:acceptance-claims-modernization:acceptance-claims-modernization.project-charter</p>",
            "shape": "rectangle",
        },
        "style": {
            "fillColor": "light_yellow",
            "textAlign": "center",
            "textAlignVertical": "middle",
        },
        "geometry": {"width": 1050.0, "height": 684.0},
        "position": {"x": 1800.0, "y": 1500.0, "origin": "center", "relativeTo": "parent_top_left"},
        "parent": {"id": "control-frame"},
    }
    payload = _replacement_payload("control-frame", update, original)
    assert payload["data"] == original["data"]
    assert payload["style"] == original["style"]
    assert payload["parent"] == {"id": "control-frame"}
    assert payload["geometry"] == {"width": 1900.0}
    assert payload["position"] == {"x": 1200.0, "y": 1850.0, "origin": "center"}


def test_sticky_replacement_identity_requires_target_geometry_and_project_token():
    update = {"x": 1200, "y": 1850, "width": 1900}
    remote = {
        "type": "sticky_note",
        "data": {"content": "<p>DDDA:acceptance-claims-modernization:acceptance-claims-modernization.project-charter</p>"},
        "geometry": {"width": 1900.0},
        "position": {"x": 1200.0, "y": 1850.0},
        "parent": {"id": "control-frame"},
    }
    token = REPLACED_STICKY_ITEM_TOKENS["3458764679756548469"]
    assert _sticky_replacement_matches(remote, "control-frame", update, token)
    remote["geometry"]["width"] = 1050.0
    assert not _sticky_replacement_matches(remote, "control-frame", update, token)
    remote["geometry"]["width"] = 1900.0
    remote["data"]["content"] = "<p>wrong project artifact</p>"
    assert not _sticky_replacement_matches(remote, "control-frame", update, token)
