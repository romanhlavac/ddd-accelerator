from __future__ import annotations

from typing import Any

from . import frame00_resize_ordering_wirefix as recovery
from . import frame01_redline as redline
from . import miro_tips_endpoint_wirefix
from . import miro_tips_hvr_fix
from . import miro_tips_hvr_semantic_fix
from .client import MiroClient, normalize_miro_percentage


_ORIGINAL_UPDATE_CONNECTOR = MiroClient.update_connector
_ORIGINAL_SAME_CONNECTOR = redline.same_connector


def _fresh_connector(client: MiroClient, board_id: str, connector_id: str) -> dict[str, Any]:
    hits = [
        connector
        for connector in client.list_connectors(board_id)
        if str(connector.get("id") or "") == str(connector_id)
    ]
    if len(hits) != 1:
        raise ValueError(
            f"connector {connector_id} fresh read expected exactly one result, got {len(hits)}"
        )
    return hits[0]


def update_connector_with_fresh_readback(
    self: MiroClient, board_id: str, connector_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """PATCH a connector, then verify against a fresh list read."""
    remote = _ORIGINAL_UPDATE_CONNECTOR(self, board_id, connector_id, payload)
    resolved_id = str((remote or {}).get("id") or connector_id)
    return _fresh_connector(self, board_id, resolved_id)


def _same_color(left: Any, right: Any) -> bool:
    return str(left or "").casefold() == str(right or "").casefold()


def _same_endpoint_contract(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Compare a Miro Tips endpoint with a pixel-meaningful tolerance.

    Endpoint coordinates are relative to the tutorial screenshot.  A tolerance
    of 0.01 is at most about fourteen pixels on the 1364 px reference image;
    it permits REST float serialization noise, but cannot turn a different
    toolbar control into a passing result.
    """
    if str(remote.get("id") or "") != str(expected.get("id") or ""):
        return False
    for key in ("position", "snapTo"):
        authored = expected.get(key)
        actual = remote.get(key)
        if authored is None:
            if actual is not None:
                return False
            continue
        if key == "snapTo":
            if actual != authored:
                return False
            continue
        if not isinstance(authored, dict) or not isinstance(actual, dict):
            return False
        for axis in ("x", "y"):
            if axis not in authored or axis not in actual:
                return False
            try:
                if abs(float(actual[axis]) - float(authored[axis])) > 0.01:
                    return False
            except (TypeError, ValueError):
                return False
    return True


def _is_miro_tips_callout(connector: dict[str, Any]) -> bool:
    style = connector.get("style") or {}
    return (
        str(style.get("strokeColor") or "").casefold() in {"#000000", "#000"}
        and not (connector.get("captions") or [])
    )


def same_connector_canonical(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Compare connector semantics, including all Miro Tips attachment points."""
    for name in ("startItem", "endItem"):
        remote_endpoint = remote.get(name) or {}
        expected_endpoint = expected.get(name) or {}
        if _is_miro_tips_callout(expected):
            if not _same_endpoint_contract(remote_endpoint, expected_endpoint):
                return False
        elif str(remote_endpoint.get("id") or "") != str(expected_endpoint.get("id") or ""):
            return False

    if expected.get("shape") and remote.get("shape") != expected["shape"]:
        return False

    remote_style = remote.get("style") or {}
    for key, value in (expected.get("style") or {}).items():
        actual = remote_style.get(key)
        if key in {"strokeColor", "color"} and isinstance(value, str) and value.startswith("#"):
            if not _same_color(actual, value):
                return False
        elif key == "fontSize":
            if not redline._close(actual, value):
                return False
        elif actual != value:
            return False

    actual_captions = remote.get("captions") or []
    expected_captions = expected.get("captions") or []
    if len(actual_captions) != len(expected_captions):
        return False
    for actual, authored in zip(actual_captions, expected_captions):
        if redline.canonical_miro_text(actual.get("content")) != redline.canonical_miro_text(
            authored.get("content")
        ):
            return False
        if "position" in authored:
            try:
                if normalize_miro_percentage(actual.get("position")) != normalize_miro_percentage(
                    authored.get("position")
                ):
                    return False
            except (TypeError, ValueError):
                return False
    return True


def main(argv: list[str] | None = None) -> int:
    MiroClient.update_connector = update_connector_with_fresh_readback
    redline.same_connector = same_connector_canonical
    miro_tips_endpoint_wirefix.install()
    miro_tips_hvr_fix.install()
    miro_tips_hvr_semantic_fix.install()
    try:
        return recovery.main(argv)
    finally:
        miro_tips_hvr_semantic_fix.uninstall()
        miro_tips_hvr_fix.uninstall()
        miro_tips_endpoint_wirefix.uninstall()
        MiroClient.update_connector = _ORIGINAL_UPDATE_CONNECTOR
        redline.same_connector = _ORIGINAL_SAME_CONNECTOR


if __name__ == "__main__":
    raise SystemExit(main())
