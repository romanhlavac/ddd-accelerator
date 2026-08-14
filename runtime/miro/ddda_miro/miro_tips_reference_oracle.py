from __future__ import annotations

import hashlib
from typing import Any

from . import image_transport
from . import miro_tips_hvr_fix as tips
from . import review_board_recovery as base


_ORIGINAL_ASSERT_REFERENCE_IDENTITY = tips.assert_reference_identity
_INSTALLED = False


def _color(value: Any) -> str:
    return str(value or "").casefold()


def assert_frozen_reference_identity(
    client: Any, source_board: str, source_frame_id: str, manifest: dict[str, Any]
) -> None:
    _ORIGINAL_ASSERT_REFERENCE_IDENTITY(client, source_board, source_frame_id, manifest)
    cfg = tips._config(manifest)
    raw = dict(manifest.get("miro_tips") or {})

    frame = base._get_frame(client, source_board, source_frame_id)
    geometry = frame.get("geometry") or {}
    expected_geometry = raw.get("reference_frame_geometry") or {}
    for key in ("width", "height"):
        if key not in expected_geometry or not base._close(geometry.get(key), expected_geometry[key]):
            raise ValueError(f"Miro Tips frozen reference frame geometry mismatch: {key}")

    state = tips._state(client, source_board, source_frame_id)
    text_items = [item for item in state["items"] if str(item.get("type") or "") == "text"]
    expected_font = float(raw.get("reference_text_font_size") or 0)
    if expected_font <= 0 or len(text_items) != 3:
        raise ValueError("Miro Tips frozen reference text contract is incomplete")
    if any(not base._close((item.get("style") or {}).get("fontSize"), expected_font) for item in text_items):
        raise ValueError("Miro Tips frozen reference text font size drifted")

    image_id = cfg["reference_source_image_id"]
    connectors = state["connectors"]
    for connector in connectors:
        if connector.get("shape") != "curved":
            raise ValueError("Miro Tips frozen reference connector shape drifted")
        style = connector.get("style") or {}
        if _color(style.get("strokeColor")) != "#000000":
            raise ValueError("Miro Tips frozen reference connector color drifted")
        if str(style.get("strokeStyle") or "normal") != "normal":
            raise ValueError("Miro Tips frozen reference connector stroke style drifted")
        if str(style.get("endStrokeCap") or "") != "stealth":
            raise ValueError("Miro Tips frozen reference connector end cap drifted")
        endpoint = connector.get("endItem") or {}
        if str(endpoint.get("id") or "") != image_id or endpoint.get("position") is None:
            raise ValueError("Miro Tips frozen reference arrowhead endpoint drifted")

    expected_background = str(raw.get("reference_background_sha256") or "")
    if len(expected_background) != 64:
        raise ValueError("Miro Tips frozen reference background hash is missing")
    image_bytes, _content_type, image = image_transport.source_image(client, source_board, image_id)
    if str(image.get("id") or "") != image_id:
        raise ValueError("Miro Tips frozen reference background identity mismatch")
    if hashlib.sha256(image_bytes).hexdigest() != expected_background:
        raise ValueError("Miro Tips frozen reference background bytes drifted")


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    tips.assert_reference_identity = assert_frozen_reference_identity
    _INSTALLED = True


def uninstall() -> None:
    global _INSTALLED
    if not _INSTALLED:
        return
    tips.assert_reference_identity = _ORIGINAL_ASSERT_REFERENCE_IDENTITY
    _INSTALLED = False
