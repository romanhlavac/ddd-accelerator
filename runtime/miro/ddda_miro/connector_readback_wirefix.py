from __future__ import annotations

import json
from typing import Any

from . import frame00_resize_ordering_wirefix as recovery
from . import frame01_redline as redline
from . import miro_tips_endpoint_wirefix
from . import miro_tips_control_anchor_fix
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


def _endpoint_coordinate(value: Any) -> float:
    """Normalize Miro's fractional and percent endpoint coordinate forms."""
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("%"):
            return float(text[:-1].strip()) / 100.0
        return float(text)
    return float(value)


def _same_endpoint_contract(
    remote: dict[str, Any], expected: dict[str, Any], *, allow_anchor_attachment: bool = False
) -> bool:
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
            # Miro is free to serialize a side/edge attachment for the tiny
            # transparent target shape.  The anchor id and its independently
            # verified geometry are the visual contract; a returned edge value
            # must not turn that precise control-targeting into false churn.
            if allow_anchor_attachment and key in {"position", "snapTo"}:
                continue
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
                if abs(_endpoint_coordinate(actual[axis]) - _endpoint_coordinate(authored[axis])) > 0.01:
                    return False
            except (TypeError, ValueError):
                return False
    return True


def _endpoint_contract_view(endpoint: dict[str, Any]) -> dict[str, Any]:
    """Return the complete endpoint fields that affect tutorial arrow routing."""
    return {
        key: endpoint.get(key)
        for key in ("id", "position", "snapTo")
        if key in endpoint
    }


def connector_contract_mismatches(
    remote: dict[str, Any], expected: dict[str, Any]
) -> list[dict[str, Any]]:
    """Expose REST read-back drift without weakening the visual contract.

    The field-level record is intentionally machine-readable: the remediation
    workflow must distinguish a rejected endpoint payload from an incorrect
    reference mapping before it chooses the next corrective payload.
    """
    if not _is_miro_tips_callout(expected):
        return []
    mismatches: list[dict[str, Any]] = []
    for name in ("startItem", "endItem"):
        actual = remote.get(name) or {}
        authored = expected.get(name) or {}
        allow_anchor_attachment = (
            name == "endItem"
            and _is_miro_tips_callout(expected)
            and "position" not in authored
            and "snapTo" not in authored
        )
        if not _same_endpoint_contract(
            actual, authored, allow_anchor_attachment=allow_anchor_attachment
        ):
            mismatches.append(
                {
                    "endpoint": name,
                    "expected": _endpoint_contract_view(authored),
                    "actual": _endpoint_contract_view(actual),
                }
            )
    return mismatches


def _is_miro_tips_callout(connector: dict[str, Any]) -> bool:
    style = connector.get("style") or {}
    return (
        str(style.get("strokeColor") or "").casefold() in {"#000000", "#000"}
        and not (connector.get("captions") or [])
    )


def same_connector_canonical(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Compare connector semantics, including all Miro Tips attachment points."""
    if connector_contract_mismatches(remote, expected):
        return False
    for name in ("startItem", "endItem"):
        remote_endpoint = remote.get(name) or {}
        expected_endpoint = expected.get(name) or {}
        if not _is_miro_tips_callout(expected) and str(remote_endpoint.get("id") or "") != str(expected_endpoint.get("id") or ""):
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


def connector_contract_error(connector_id: str, remote: dict[str, Any], expected: dict[str, Any]) -> str:
    """Produce an actionable exact endpoint diff for the authoritative log."""
    mismatches = connector_contract_mismatches(remote, expected)
    if not mismatches:
        return f"companion connector {connector_id} read-back mismatch"
    return (
        f"companion connector {connector_id} endpoint read-back mismatch: "
        + json.dumps(mismatches, sort_keys=True, separators=(",", ":"))
    )


def main(argv: list[str] | None = None) -> int:
    MiroClient.update_connector = update_connector_with_fresh_readback
    redline.same_connector = same_connector_canonical
    miro_tips_endpoint_wirefix.install()
    miro_tips_hvr_fix.install()
    miro_tips_hvr_semantic_fix.install()
    miro_tips_control_anchor_fix.install()
    try:
        return recovery.main(argv)
    finally:
        miro_tips_control_anchor_fix.uninstall()
        miro_tips_hvr_semantic_fix.uninstall()
        miro_tips_hvr_fix.uninstall()
        miro_tips_endpoint_wirefix.uninstall()
        MiroClient.update_connector = _ORIGINAL_UPDATE_CONNECTOR
        redline.same_connector = _ORIGINAL_SAME_CONNECTOR


if __name__ == "__main__":
    raise SystemExit(main())
