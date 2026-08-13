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


def _copy_endpoint_contract(
    source_endpoint: dict[str, Any], target_endpoint: dict[str, Any]
) -> None:
    """Copy the reference attachment verbatim, except for the target item id.

    The screenshot and all its callout items have identical parent-relative
    geometry on Platform Lab.  Removing either ``position`` or ``snapTo``
    changes Miro's curve routing and can visibly detach the arrowhead from the
    intended UI control.  Both fields are therefore part of the authored HVR-2
    contract whenever the source supplied them.
    """
    for key in ("position", "snapTo"):
        if key in source_endpoint and source_endpoint[key] is not None:
            target_endpoint[key] = deepcopy(source_endpoint[key])
        else:
            target_endpoint.pop(key, None)


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

    _copy_endpoint_contract(src.get("startItem") or {}, payload.setdefault("startItem", {}))
    _copy_endpoint_contract(src.get("endItem") or {}, payload.setdefault("endItem", {}))
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
