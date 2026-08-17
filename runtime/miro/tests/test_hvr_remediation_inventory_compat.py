from __future__ import annotations

from pathlib import Path

import pytest

import ddda_miro.hvr_remediation_inventory_compat as inventory

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "scaffolds" / "miro" / "rem-012-3-hvr-remediation.yaml"


def test_current_filled_bmc_inventory_is_normalized_to_120():
    manifest = inventory._inventory_load(MANIFEST)
    clones = {str(item["name"]): item for item in manifest["native_clones"]}

    assert int(clones["align-onboarding"]["expected_supported_count"]) == 7
    assert (
        int(clones[inventory.FILLED_BMC_CLONE_NAME]["expected_supported_count"])
        == inventory.FILLED_BMC_NATIVE_COUNT
        == 120
    )
    assert sum(
        int(item["expected_supported_count"])
        for item in manifest["native_clones"]
    ) == 127


def test_unexpected_filled_bmc_inventory_is_rejected(monkeypatch):
    def fake_load(path: Path):
        return {
            "native_clones": [
                {
                    "name": inventory.FILLED_BMC_CLONE_NAME,
                    "expected_supported_count": 119,
                }
            ]
        }

    monkeypatch.setattr(inventory, "_ORIGINAL_COMPAT_LOAD", fake_load)
    with pytest.raises(
        ValueError,
        match="unexpected filled BMC declared count: 119",
    ):
        inventory._inventory_load(MANIFEST)
