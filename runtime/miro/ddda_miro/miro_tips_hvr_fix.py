from __future__ import annotations

import time
from typing import Any

from . import review_board_recovery as base
from . import review_board_recovery_wirefix as visual


MIRO_TIPS_TITLE = "Miro Tips"
MIRO_TIPS_MODE = "reference_ui_tutorial"
DEFAULT_READBACK_ATTEMPTS = 20
DEFAULT_READBACK_DELAY_SECONDS = 0.5
DEFAULT_MIN_IMAGES = 1
DEFAULT_MIN_CONNECTORS = 8
DEFAULT_REQUIRED_MARKERS = (
    "toggle between navigation mode & edit mode",
    "stickies / post-its",
    "arrows / connection lines",
    "press tab after typing a sticky",
    "alt-drag copies whatever you selected",
    "shift-drag to select multiple items at once",
    "right-click-drag to drag the board around",
    "moved something by accident",
    "an overview of all frames",
    "enable or disable seeing the mouse pointers of others",
    "click on the avator of the facilitator",
    "consult a map of the board",
    "zoom to a 100%",
    "add your own tips here",
)

_ORIGINAL_COMPANION_FRAME_PAYLOAD = visual.companion_frame_payload
_ORIGINAL_SAME_FRAME = visual._same_frame
_ORIGINAL_RECONCILE_COMPANION_CHILDREN = visual._reconcile_companion_children
_INSTALLED = False


def _config(manifest: dict[str, Any]) -> dict[str, Any]:
    raw = dict(manifest.get("miro_tips") or {})
    attempts = int(raw.get("readback_attempts") or DEFAULT_READBACK_ATTEMPTS)
    delay = float(
        raw.get("readback_delay_seconds")
        if raw.get("readback_delay_seconds") is not None
        else DEFAULT_READBACK_DELAY_SECONDS
    )
    min_images = int(raw.get("min_images") or DEFAULT_MIN_IMAGES)
    min_connectors = int(raw.get("min_connectors") or DEFAULT_MIN_CONNECTORS)
    required = tuple(str(value).casefold() for value in (raw.get("required_markers") or DEFAULT_REQUIRED_MARKERS))
    if not 2 <= attempts <= 60:
        raise ValueError("Miro Tips read-back attempts must be between 2 and 60")
    if not 0 <= delay <= 2:
        raise ValueError("Miro Tips read-back delay must be between 0 and 2 seconds")
    if min_images < DEFAULT_MIN_IMAGES:
        raise ValueError("Miro Tips visual tutorial requires at least one Miro UI image")
    if min_connectors < DEFAULT_MIN_CONNECTORS:
        raise ValueError("Miro Tips visual tutorial requires at least eight callout connectors")
    for marker in DEFAULT_REQUIRED_MARKERS:
        if marker.casefold() not in required:
            raise ValueError(f"Miro Tips required-marker contract is missing: {marker}")
    return {
        "readback_attempts": attempts,
        "readback_delay_seconds": delay,
        "min_images": min_images,
        "min_connectors": min_connectors,
        "required_markers": required,
    }


def _source_spec(manifest: dict[str, Any]) -> dict[str, Any]:
    hits = [
        spec
        for spec in (manifest.get("source_companion_frames") or [])
        if str(spec.get("title") or "") == MIRO_TIPS_TITLE
    ]
    if len(hits) != 1:
        raise ValueError(f"expected exactly one {MIRO_TIPS_TITLE!r} companion spec, got {len(hits)}")
    if str(hits[0].get("mode") or "") != MIRO_TIPS_MODE:
        raise ValueError("Miro Tips companion must opt in to the reference UI tutorial mode")
    return hits[0]


def desired_miro_tips_items(frame_id: str, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Compatibility surface: HVR-2 no longer authors a parallel card-only tutorial."""
    _ = frame_id
    _config(manifest)
    return []


def miro_tips_companion_frame_payload(
    source_frame: dict[str, Any],
    source_main: dict[str, Any],
    target_main: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    _config(manifest)
    return _ORIGINAL_COMPANION_FRAME_PAYLOAD(source_frame, source_main, target_main)


def companion_frame_payload_with_miro_tips(
    source_frame: dict[str, Any],
    source_main: dict[str, Any],
    target_main: dict[str, Any],
) -> dict[str, Any]:
    manifest = visual._ACTIVE_MANIFEST
    if str((source_frame.get("data") or {}).get("title") or "") != MIRO_TIPS_TITLE:
        return _ORIGINAL_COMPANION_FRAME_PAYLOAD(source_frame, source_main, target_main)
    return miro_tips_companion_frame_payload(source_frame, source_main, target_main, manifest)


def same_frame_defer_miro_tips(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Defer a Miro Tips shrink/move until its old oversized children are removed."""
    title = str((expected.get("data") or {}).get("title") or "")
    if title == MIRO_TIPS_TITLE and str((remote.get("data") or {}).get("title") or "") == title:
        return True
    return _ORIGINAL_SAME_FRAME(remote, expected)


def _frame_equal(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    return _ORIGINAL_SAME_FRAME(remote, expected)


def _children_text(items: list[dict[str, Any]]) -> str:
    return " ".join(
        base._visible((item.get("data") or {}).get("content")).casefold()
        for item in items
    )


def _image_anchor_connector_count(
    connectors: list[dict[str, Any]], image_ids: set[str]
) -> int:
    return sum(
        1
        for connector in connectors
        if str((connector.get("startItem") or {}).get("id") or "") in image_ids
        or str((connector.get("endItem") or {}).get("id") or "") in image_ids
    )


def _tutorial_state(
    client: Any,
    board: str,
    frame_id: str,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    items = base._children(client, board, frame_id)
    images = [item for item in items if str(item.get("type") or "") == "image"]
    ids = {str(item["id"]) for item in items}
    connectors = visual._companion_source_connectors(client, board, ids)
    text = _children_text(items)
    missing = [marker for marker in cfg["required_markers"] if marker not in text]
    image_ids = {str(item["id"]) for item in images}
    anchors = _image_anchor_connector_count(connectors, image_ids)
    return {
        "items": items,
        "images": images,
        "connectors": connectors,
        "missing_markers": missing,
        "image_anchor_connector_count": anchors,
    }


def _wait_for_empty_frame(
    client: Any,
    board: str,
    frame_id: str,
    old_item_ids: set[str],
    cfg: dict[str, Any],
) -> None:
    for attempt in range(cfg["readback_attempts"]):
        children = base._children(client, board, frame_id)
        related = base._related_connectors(client, board, old_item_ids) if old_item_ids else []
        if not children and not related:
            return
        if attempt + 1 < cfg["readback_attempts"] and cfg["readback_delay_seconds"]:
            time.sleep(cfg["readback_delay_seconds"])
    raise ValueError("Miro Tips did not become empty before reference-geometry restore")


def _wait_for_frame_geometry(
    client: Any,
    board: str,
    frame_id: str,
    expected: dict[str, Any],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    last: dict[str, Any] | None = None
    for attempt in range(cfg["readback_attempts"]):
        last = base._get_frame(client, board, frame_id)
        if _frame_equal(last, expected):
            return last
        if attempt + 1 < cfg["readback_attempts"] and cfg["readback_delay_seconds"]:
            time.sleep(cfg["readback_delay_seconds"])
    raise ValueError("Miro Tips frame did not converge to reference geometry and placement")


def _reset_frame_to_reference(
    client: Any,
    target_board: str,
    target_frame_id: str,
    expected_frame: dict[str, Any],
    cfg: dict[str, Any],
) -> bool:
    current = base._get_frame(client, target_board, target_frame_id)
    if _frame_equal(current, expected_frame):
        return False

    children = base._children(client, target_board, target_frame_id)
    old_item_ids = {str(item["id"]) for item in children}
    for connector in base._related_connectors(client, target_board, old_item_ids):
        client.delete_connector(target_board, str(connector["id"]))
    for item in children:
        client.delete_item(target_board, str(item["id"]))
    _wait_for_empty_frame(client, target_board, target_frame_id, old_item_ids, cfg)

    client.update_item(target_board, "frame", target_frame_id, expected_frame)
    _wait_for_frame_geometry(client, target_board, target_frame_id, expected_frame, cfg)
    return True


def reconcile_miro_tips_children(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    cfg = _config(manifest)
    source_main = base._get_frame(client, source_board, str(manifest["source_frame_id"]))
    target_main = base._get_frame(client, target_board, str(manifest["frame_id"]))
    source_frame = base._get_frame(client, source_board, source_frame_id)
    expected_frame = miro_tips_companion_frame_payload(source_frame, source_main, target_main, manifest)

    source_state = _tutorial_state(client, source_board, source_frame_id, cfg)
    if len(source_state["images"]) < cfg["min_images"]:
        raise ValueError(
            f"Miro Tips source has {len(source_state['images'])} images; expected at least {cfg['min_images']}"
        )
    if len(source_state["connectors"]) < cfg["min_connectors"]:
        raise ValueError(
            f"Miro Tips source has {len(source_state['connectors'])} connectors; expected at least {cfg['min_connectors']}"
        )
    if source_state["image_anchor_connector_count"] < cfg["min_connectors"]:
        raise ValueError("Miro Tips source callouts are not anchored to the Miro UI image")
    if source_state["missing_markers"]:
        raise ValueError(f"Miro Tips source is missing required tutorial markers: {source_state['missing_markers']}")

    frame_reinitialized = _reset_frame_to_reference(
        client, target_board, target_frame_id, expected_frame, cfg
    )

    child_result = _ORIGINAL_RECONCILE_COMPANION_CHILDREN(
        client,
        source_board,
        source_frame_id,
        target_board,
        target_frame_id,
        cfg["min_images"],
        manifest,
    )

    target_frame = _wait_for_frame_geometry(
        client, target_board, target_frame_id, expected_frame, cfg
    )
    target_state = _tutorial_state(client, target_board, target_frame_id, cfg)
    if len(target_state["images"]) < cfg["min_images"]:
        raise ValueError("Miro Tips target is missing the Miro UI tutorial image")
    if len(target_state["connectors"]) < cfg["min_connectors"]:
        raise ValueError("Miro Tips target is missing callout connectors")
    if target_state["image_anchor_connector_count"] < cfg["min_connectors"]:
        raise ValueError("Miro Tips target callouts are not anchored to the Miro UI image")
    if target_state["missing_markers"]:
        raise ValueError(f"Miro Tips target is missing required tutorial markers: {target_state['missing_markers']}")

    return {
        "mode": MIRO_TIPS_MODE,
        **child_result,
        "target_image_count": len(target_state["images"]),
        "target_connector_count": len(target_state["connectors"]),
        "source_image_anchor_connector_count": source_state["image_anchor_connector_count"],
        "target_image_anchor_connector_count": target_state["image_anchor_connector_count"],
        "required_marker_count": len(cfg["required_markers"]),
        "frame_reinitialized": int(frame_reinitialized),
        "reference_geometry": dict(expected_frame.get("geometry") or {}),
        "target_geometry": dict(target_frame.get("geometry") or {}),
        "reference_position": dict(expected_frame.get("position") or {}),
        "target_position": dict(target_frame.get("position") or {}),
        "readback_attempts": cfg["readback_attempts"],
    }


def reconcile_companion_children_with_miro_tips(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    min_images: int,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    spec = _source_spec(manifest)
    if str(source_frame_id) != str(spec["id"]):
        return _ORIGINAL_RECONCILE_COMPANION_CHILDREN(
            client,
            source_board,
            source_frame_id,
            target_board,
            target_frame_id,
            min_images,
            manifest,
        )
    return reconcile_miro_tips_children(
        client,
        source_board,
        source_frame_id,
        target_board,
        target_frame_id,
        manifest,
    )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    visual.companion_frame_payload = companion_frame_payload_with_miro_tips
    visual._same_frame = same_frame_defer_miro_tips
    visual._reconcile_companion_children = reconcile_companion_children_with_miro_tips
    _INSTALLED = True


def uninstall() -> None:
    global _INSTALLED
    if not _INSTALLED:
        return
    visual.companion_frame_payload = _ORIGINAL_COMPANION_FRAME_PAYLOAD
    visual._same_frame = _ORIGINAL_SAME_FRAME
    visual._reconcile_companion_children = _ORIGINAL_RECONCILE_COMPANION_CHILDREN
    _INSTALLED = False
