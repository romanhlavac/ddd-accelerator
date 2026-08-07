from __future__ import annotations

from typing import Any

from . import review_board_recovery as base

_ORIGINAL_FRAME00_PAYLOAD = base.frame00_payload


def frame00_payload(update: dict[str, Any], frame_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    """Return the REM-012.5 Frame-00 payload without Miro read-only position metadata."""
    payload = _ORIGINAL_FRAME00_PAYLOAD(update, frame_id, manifest)
    position = dict(payload.get("position") or {})
    position.pop("relativeTo", None)
    payload["position"] = position
    return payload


def main(argv: list[str] | None = None) -> int:
    original = base.frame00_payload
    base.frame00_payload = frame00_payload
    try:
        return base.main(argv)
    finally:
        base.frame00_payload = original


if __name__ == "__main__":
    raise SystemExit(main())
