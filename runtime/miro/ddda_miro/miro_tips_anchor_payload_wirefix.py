from __future__ import annotations

"""Compatibility guard for Miro technical-anchor shape payloads.

Miro REST v2 currently rejects ``style.fontSize=8`` on the transparent control
anchor shape used by the PR8 Miro Tips render-fidelity repair.  The anchor is a
pure routing primitive and does not require a text font size.  This wirefix
removes that non-semantic field at the runtime boundary while preserving the
versioned render-fidelity contract.
"""

from typing import Any

from . import miro_tips_render_fidelity_fix as fidelity


_ORIGINAL_ANCHOR_PAYLOAD = fidelity._anchor_payload
_INSTALLED = False


def anchor_payload_without_illegal_font_size(
    frame_id: str, x: float, y: float
) -> dict[str, Any]:
    payload = _ORIGINAL_ANCHOR_PAYLOAD(frame_id, x, y)
    style = dict(payload.get("style") or {})
    style.pop("fontSize", None)
    payload["style"] = style
    return payload


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    fidelity._anchor_payload = anchor_payload_without_illegal_font_size
    _INSTALLED = True


def uninstall() -> None:
    global _INSTALLED
    if not _INSTALLED:
        return
    fidelity._anchor_payload = _ORIGINAL_ANCHOR_PAYLOAD
    _INSTALLED = False
