from __future__ import annotations

import json
from typing import Any

from . import frame00_resize_ordering_wirefix as recovery
from . import frame01_redline as redline
from . import miro_tips_anchor_payload_wirefix
from . import miro_tips_exact_font_wirefix
from . import miro_tips_full_arrow_fidelity_fix
from . import miro_tips_hvr_fix
from . import miro_tips_legacy_line_fidelity_fix
from . import miro_tips_reference_oracle
from . import miro_tips_render_fidelity_fix
from .client import MiroClient, normalize_miro_percentage


_ORIGINAL_UPDATE_CONNECTOR = MiroClient.update_connector
_ORIGINAL_PREPARE_CONNECTOR_PAYLOAD = MiroClient._prepare_connector_payload
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


def prepare_connector_payload_with_percentage_endpoints(
    self: MiroClient, payload: dict[str, Any]
) -> dict[str, Any]:
    """Serialize authored/read-back connector endpoint positions as Miro Percentage values."""
    prepared = _ORIGINAL_PREPARE_CONNECTOR_PAYLOAD(self, payload)
    for endpoint_name in ("startItem", "endItem"):
        endpoint = prepared.get(endpoint_name)
        if not isinstance(endpoint, dict):
            continue
        position = endpoint.get("position")
        if not isinstance(position, dict):
            continue
        for axis in ("x", "y"):
            if axis in position:
                position[axis] = normalize_miro_percentage(position[axis])
    return prepared


def update_connector_with_fresh_readback(
    self: MiroClient, board_id: str, connector_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """PATCH a connector, then verify against a fresh list read."""
    remote = _ORIGINAL_UPDATE_CONNECTOR(self, board_id, connector_id, payload)
    resolved_id = str((remote or {}).get("id") or connector_id)
    return _fresh_connector(self, board_id, resolved_id)


def _same_color(left: Any, right: Any) -> bool:
    return str(left or "").casefold() == str(right or "").casefold()


def _coordinate(value: Any) -> float:
    if isinstance(value, str) and value.strip().endswith("%"):
        return float(value.strip()[:-1]) / 100.0
    return float(value)


def _endpoint_view(endpoint: dict[str, Any]) -> dict[str, Any]:
    return {
        key: endpoint.get(key)
        for key in ("id", "position", "snapTo")
        if key in endpoint
    }


def connector_contract_mismatches(
    remote: dict[str, Any], expected: dict[str, Any]
) -> list[dict[str, Any]]:
    """Compare every authored endpoint attachment in the reference contract."""
    mismatches: list[dict[str, Any]] = []
    for name in ("startItem", "endItem"):
        actual = remote.get(name) or {}
        authored = expected.get(name) or {}
        valid = str(actual.get("id") or "") == str(authored.get("id") or "")
        if valid and authored.get("position") is not None:
            position = actual.get("position") or {}
            source_position = authored.get("position") or {}
            try:
                valid = all(
                    axis in position
                    and axis in source_position
                    and abs(_coordinate(position[axis]) - _coordinate(source_position[axis])) <= 0.001
                    for axis in ("x", "y")
                )
            except (TypeError, ValueError):
                valid = False
        if valid and authored.get("snapTo") is not None:
            valid = actual.get("snapTo") == authored.get("snapTo")
        if valid:
            authored_explicit = authored.get("position") is not None or authored.get("snapTo") is not None
            actual_explicit = actual.get("position") is not None or actual.get("snapTo") is not None
            valid = authored_explicit == actual_explicit
        if not valid:
            mismatches.append(
                {
                    "endpoint": name,
                    "expected": _endpoint_view(authored),
                    "actual": _endpoint_view(actual),
                }
            )
    return mismatches


def same_connector_canonical(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Compare connector semantics and authored reference attachment points."""
    if connector_contract_mismatches(remote, expected):
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


def connector_contract_error(
    connector_id: str, remote: dict[str, Any], expected: dict[str, Any]
) -> str:
    mismatches = connector_contract_mismatches(remote, expected)
    if not mismatches:
        return f"companion connector {connector_id} read-back mismatch"
    return (
        f"companion connector {connector_id} endpoint read-back mismatch: "
        + json.dumps(mismatches, sort_keys=True, separators=(",", ":"))
    )


def main(argv: list[str] | None = None) -> int:
    MiroClient._prepare_connector_payload = prepare_connector_payload_with_percentage_endpoints
    MiroClient.update_connector = update_connector_with_fresh_readback
    redline.same_connector = same_connector_canonical
    miro_tips_exact_font_wirefix.install()
    miro_tips_reference_oracle.install()
    miro_tips_hvr_fix.install()
    miro_tips_render_fidelity_fix.install()
    miro_tips_anchor_payload_wirefix.install()
    miro_tips_full_arrow_fidelity_fix.install()
    miro_tips_legacy_line_fidelity_fix.install()
    try:
        return recovery.main(argv)
    finally:
        miro_tips_legacy_line_fidelity_fix.uninstall()
        miro_tips_full_arrow_fidelity_fix.uninstall()
        miro_tips_anchor_payload_wirefix.uninstall()
        miro_tips_render_fidelity_fix.uninstall()
        miro_tips_hvr_fix.uninstall()
        miro_tips_reference_oracle.uninstall()
        miro_tips_exact_font_wirefix.uninstall()
        MiroClient._prepare_connector_payload = _ORIGINAL_PREPARE_CONNECTOR_PAYLOAD
        MiroClient.update_connector = _ORIGINAL_UPDATE_CONNECTOR
        redline.same_connector = _ORIGINAL_SAME_CONNECTOR


if __name__ == "__main__":
    raise SystemExit(main())
