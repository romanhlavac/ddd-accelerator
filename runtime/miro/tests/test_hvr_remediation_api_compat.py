from __future__ import annotations

from pathlib import Path

from ddda_miro.hvr_remediation_api_compat import (
    REPLACED_TEXT_ITEM_ID,
    _compat_load,
    _replacement_payload,
)

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "scaffolds" / "miro" / "rem-012-3-hvr-remediation.yaml"


def test_compat_contract_replaces_only_the_known_instruction_text():
    manifest = _compat_load(MANIFEST)
    matches = [item for item in manifest["updates"] if str(item.get("id") or "") == REPLACED_TEXT_ITEM_ID]
    assert len(matches) == 1
    assert matches[0]["replace_by_create"] is True
    assert manifest["cleanup_ids"].count(REPLACED_TEXT_ITEM_ID) == 1


def test_replacement_payload_is_readable_and_frame_scoped():
    manifest = _compat_load(MANIFEST)
    update = next(item for item in manifest["updates"] if str(item.get("id") or "") == REPLACED_TEXT_ITEM_ID)
    payload = _replacement_payload("control-frame", update)
    assert payload["parent"] == {"id": "control-frame"}
    assert payload["style"]["fontSize"] == 36
    assert payload["style"]["fontFamily"] == "arial"
    assert payload["geometry"] == {"width": 3000.0}
    assert payload["position"] == {"x": 5200.0, "y": 700.0, "origin": "center"}
    assert "Miro ani technický PASS gate neschvalují" in payload["data"]["content"]
