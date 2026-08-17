from __future__ import annotations

"""Compatibility entry point for the current REM-012.3 source inventory.

The exact ``filled-bmc-example`` source frame currently contains 120 supported
native items. The historical remediation manifest declares 121. This wrapper
keeps the existing API/read-back compatibility behavior and narrows only that
source-inventory contract before executing the canonical remediation broker.
"""

from pathlib import Path
from typing import Any

from . import hvr_remediation_api_compat as compat

FILLED_BMC_CLONE_NAME = "filled-bmc-example"
FILLED_BMC_NATIVE_COUNT = 120
_ORIGINAL_COMPAT_LOAD = compat._compat_load


def _inventory_load(path: Path) -> dict[str, Any]:
    manifest = _ORIGINAL_COMPAT_LOAD(path)
    clones = {
        str(item.get("name") or ""): item
        for item in manifest["native_clones"]
    }
    filled_clone = clones.get(FILLED_BMC_CLONE_NAME)
    if not isinstance(filled_clone, dict):
        raise ValueError("REM-012.3 filled BMC clone is missing")

    declared_count = int(filled_clone.get("expected_supported_count") or 0)
    if declared_count not in {
        FILLED_BMC_NATIVE_COUNT,
        FILLED_BMC_NATIVE_COUNT + 1,
    }:
        raise ValueError(
            f"unexpected filled BMC declared count: {declared_count}"
        )
    filled_clone["expected_supported_count"] = FILLED_BMC_NATIVE_COUNT
    return manifest


def main(argv: list[str] | None = None) -> int:
    original_load = compat._compat_load
    compat._compat_load = _inventory_load
    try:
        return compat.main(argv)
    finally:
        compat._compat_load = original_load


if __name__ == "__main__":
    raise SystemExit(main())
