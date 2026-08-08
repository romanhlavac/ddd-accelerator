from __future__ import annotations

from typing import Any

from . import frame00_resize_ordering_wirefix as recovery
from . import frame01_redline as redline
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
    """PATCH a connector, then verify against a fresh list read instead of the PATCH response."""
    remote = _ORIGINAL_UPDATE_CONNECTOR(self, board_id, connector_id, payload)
    resolved_id = str((remote or {}).get("id") or connector_id)
    return _fresh_connector(self, board_id, resolved_id)


def _same_color(left: Any, right: Any) -> bool:
    return str(left or "").casefold() == str(right or "").casefold()


def same_connector_canonical(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Compare authored connector semantics while tolerating Miro wire-format normalization."""
    for name in ("startItem", "endItem"):
        if str((remote.get(name) or {}).get("id") or "") != str(
            (expected.get(name) or {}).get("id") or ""
        ):
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
    try:
        return recovery.main(argv)
    finally:
        MiroClient.update_connector = _ORIGINAL_UPDATE_CONNECTOR
        redline.same_connector = _ORIGINAL_SAME_CONNECTOR


if __name__ == "__main__":
    raise SystemExit(main())
