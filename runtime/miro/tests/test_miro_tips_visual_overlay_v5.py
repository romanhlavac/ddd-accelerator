from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

import pytest

from ddda_miro import miro_tips_visual_overlay_v5 as v5


def _overlay(spec: dict, frame_id: str = "frame") -> dict:
    return {
        "id": f"overlay-{spec['key']}",
        "type": "image",
        "parent": {"id": frame_id},
        "data": {"title": v5.overlay_title(spec)},
        "position": {"x": spec["x"], "y": spec["y"]},
        "geometry": {"width": spec["width"], "height": spec["height"]},
    }


def test_v5_forbids_native_curved_target_router_and_uses_eight_frozen_visual_assets():
    assert v5.VISUAL_ARROW_COUNT == 8
    assert v5.PHYSICAL_CONNECTOR_COUNT == 3
    assert v5.DIRECT_IMAGE_TARGET_CONNECTOR_COUNT == 0
    assert v5.VISUAL_ARROW_OVERLAY_POLICY == "frozen_reference_raster_arrow_overlays_v5"
    assert len({spec["key"] for spec in v5.ARROW_SPECS}) == 8


def test_all_visual_arrow_assets_match_versioned_sha256_contract():
    asset_root = Path(v5.__file__).resolve().parent / "assets"
    for spec in v5.ARROW_SPECS:
        payload = (asset_root / spec["asset"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == spec["sha256"]
        assert len(payload) > 100


def test_overlay_evidence_accepts_exact_8_of_8_geometry():
    rows = [_overlay(spec) for spec in v5.ARROW_SPECS]
    evidence = v5.overlay_evidence(rows, "frame")
    assert evidence["status"] == "PASS"
    assert evidence["count"] == 8
    assert all(row["status"] == "PASS" for row in evidence["arrows"])


def test_overlay_evidence_rejects_shift_that_old_endpoint_metadata_gate_cannot_see():
    rows = [_overlay(spec) for spec in v5.ARROW_SPECS]
    rows[0] = deepcopy(rows[0])
    rows[0]["position"]["x"] += 5.0
    with pytest.raises(ValueError, match="visual arrow overlay shortcut mismatch"):
        v5.overlay_evidence(rows, "frame")


def test_overlay_evidence_rejects_missing_or_duplicate_visual_arrow():
    rows = [_overlay(spec) for spec in v5.ARROW_SPECS]
    with pytest.raises(ValueError, match="zoom_100 mismatch"):
        v5.overlay_evidence(rows[:-1], "frame")
    duplicate = rows + [deepcopy(rows[0]) | {"id": "duplicate"}]
    with pytest.raises(ValueError, match="shortcut mismatch"):
        v5.overlay_evidence(duplicate, "frame")
