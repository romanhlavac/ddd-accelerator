from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import review_board_recovery_wirefix as visual


REFERENCE_FRAME_ID = "3458764679531043366"
_ORIGINAL_ITEM_PAYLOAD = visual._ORIGINAL_ITEM_PAYLOAD
_INSTALLED = False


def exact_reference_item_payload(source: dict[str, Any], target_frame_id: str) -> dict[str, Any]:
    """Preserve the authored source font size for the frozen Miro Tips reference.

    The generic redline path normalizes font sizes for compatibility. That is
    not valid for an artifact whose acceptance contract is exact visual
    equivalence. Miro Tips therefore keeps the source font size verbatim.
    """
    payload = _ORIGINAL_ITEM_PAYLOAD(source, target_frame_id)
    source_parent = str((source.get("parent") or {}).get("id") or "")
    source_type = str(source.get("type") or "")
    source_style = source.get("style") or {}
    if (
        source_parent == REFERENCE_FRAME_ID
        and source_type in {"shape", "text"}
        and source_style.get("fontSize") is not None
    ):
        payload.setdefault("style", {})["fontSize"] = deepcopy(source_style["fontSize"])
    return payload


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    visual._ORIGINAL_ITEM_PAYLOAD = exact_reference_item_payload
    _INSTALLED = True


def uninstall() -> None:
    global _INSTALLED
    if not _INSTALLED:
        return
    visual._ORIGINAL_ITEM_PAYLOAD = _ORIGINAL_ITEM_PAYLOAD
    _INSTALLED = False
