from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import review_board_recovery_wirefix as visual


_ORIGINAL_READABLE_CONNECTOR_PAYLOAD = visual.readable_connector_payload
_INSTALLED = False


def _is_miro_tips_callout(src: dict[str, Any]) -> bool:
    """Identify the black, captionless Miro Tips tutorial callouts."""
    style = src.get("style") or {}
    stroke = str(style.get("strokeColor") or "").casefold()
    return stroke in {"#000000", "#000"} and not (src.get("captions") or [])


def _copy_endpoint_location(
    source_endpoint: dict[str, Any], target_endpoint: dict[str, Any]
) -> None:
    position = source_endpoint.get("position")
    snap_to = source_endpoint.get("snapTo")
    if (
        isinstance(position, dict)
        and position.get("x") is not None
        and position.get("y") is not None
    ):
        target_endpoint.pop("snapTo", None)
        target_endpoint["position"] = deepcopy(position)
    elif snap_to is not None:
        target_endpoint.pop("position", None)
        target_endpoint["snapTo"] = deepcopy(snap_to)


def readable_connector_payload_preserve_endpoint(
    src: dict[str, Any], start: str, end: str, manifest: dict[str, Any]
) -> dict[str, Any]:
    """Preserve the screenshot-side arrowhead target for Miro Tips callouts.

    HVR-2 requires the arrowhead to land on the intended visible Miro control.
    The sticky-side start attachment only affects routing and may be normalized by
    Miro, so it is deliberately not promoted to a precise visual contract.
    """
    payload = _ORIGINAL_READABLE_CONNECTOR_PAYLOAD(src, start, end, manifest)
    if not _is_miro_tips_callout(src):
        return payload

    source_end = src.get("endItem") or {}
    target_end = payload.setdefault("endItem", {})
    _copy_endpoint_location(source_end, target_end)

    source_start = src.get("startItem") or {}
    target_start = payload.setdefault("startItem", {})
    if source_start.get("snapTo") is not None:
        target_start.pop("position", None)
        target_start["snapTo"] = deepcopy(source_start["snapTo"])
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
