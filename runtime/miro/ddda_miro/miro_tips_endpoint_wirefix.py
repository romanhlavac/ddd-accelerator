from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import review_board_recovery_wirefix as visual


_ORIGINAL_READABLE_CONNECTOR_PAYLOAD = visual.readable_connector_payload
_INSTALLED = False


def _is_miro_tips_callout(src: dict[str, Any]) -> bool:
    """Bound precise endpoint semantics to the black, captionless Miro Tips callouts."""
    style = src.get("style") or {}
    stroke = str(style.get("strokeColor") or "").casefold()
    return stroke in {"#000000", "#000"} and not (src.get("captions") or [])


def readable_connector_payload_preserve_endpoint(
    src: dict[str, Any], start: str, end: str, manifest: dict[str, Any]
) -> dict[str, Any]:
    """Preserve one precise endpoint-location contract for Miro Tips callouts only."""
    payload = _ORIGINAL_READABLE_CONNECTOR_PAYLOAD(src, start, end, manifest)
    if not _is_miro_tips_callout(src):
        return payload

    for name in ("startItem", "endItem"):
        source_endpoint = src.get(name) or {}
        target_endpoint = payload.setdefault(name, {})
        position = source_endpoint.get("position")
        snap_to = source_endpoint.get("snapTo")
        if (
            isinstance(position, dict)
            and position.get("x") is not None
            and position.get("y") is not None
        ):
            # Miro accepts a precise normalized position OR snapTo. For the
            # tutorial callouts, the source position is the visual redline.
            target_endpoint.pop("snapTo", None)
            target_endpoint["position"] = deepcopy(position)
        elif snap_to is not None:
            target_endpoint.pop("position", None)
            target_endpoint["snapTo"] = deepcopy(snap_to)
    return payload


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    visual.readable_connector_payload = readable_connector_payload_preserve_endpoint
    _INSTALLED = True


def uninstall() -> None:
    global _INSTALLED
    if not _INSTALLED:
        return
    visual.readable_connector_payload = _ORIGINAL_READABLE_CONNECTOR_PAYLOAD
    _INSTALLED = False
