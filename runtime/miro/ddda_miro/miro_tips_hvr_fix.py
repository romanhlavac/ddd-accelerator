from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from . import review_board_recovery as base
from . import review_board_recovery_wirefix as visual


MIRO_TIPS_TITLE = "Miro Tips"
MIRO_TIPS_MODE = "exact_reference_clone"
MIRO_TIPS_CONTAINER_POLICY = "retained_verified_target_container"
MIRO_TIPS_VISUAL_EQUIVALENCE_POLICY = "exact_reference_child_snapshot"
EXPECTED_ITEM_TYPE_COUNTS = {"image": 1, "sticky_note": 13, "text": 3}
EXPECTED_ITEM_COUNT = sum(EXPECTED_ITEM_TYPE_COUNTS.values())
EXPECTED_CONNECTOR_COUNT = 0
DEFAULT_READBACK_ATTEMPTS = 20
DEFAULT_READBACK_DELAY_SECONDS = 0.5
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
    mode = str(raw.get("mode") or "")
    container_policy = str(raw.get("container_policy") or "")
    visual_policy = str(raw.get("visual_equivalence_policy") or "")
    reference_source_board_id = str(raw.get("reference_source_board_id") or "")
    reference_source_frame_id = str(raw.get("reference_source_frame_id") or "")
    reference_source_image_id = str(raw.get("reference_source_image_id") or "")
    target_position = dict(raw.get("target_position") or {})
    expected_types = {
        str(kind): int(count)
        for kind, count in dict(raw.get("expected_item_type_counts") or {}).items()
    }
    required_markers = tuple(
        str(marker).casefold()
        for marker in (raw.get("required_markers") or DEFAULT_REQUIRED_MARKERS)
    )
    attempts = int(raw.get("readback_attempts") or DEFAULT_READBACK_ATTEMPTS)
    delay = float(
        raw.get("readback_delay_seconds")
        if raw.get("readback_delay_seconds") is not None
        else DEFAULT_READBACK_DELAY_SECONDS
    )

    if mode != MIRO_TIPS_MODE:
        raise ValueError("Miro Tips must use the exact-reference-clone mode")
    if container_policy != MIRO_TIPS_CONTAINER_POLICY:
        raise ValueError("Miro Tips must retain its verified target container")
    if visual_policy != MIRO_TIPS_VISUAL_EQUIVALENCE_POLICY:
        raise ValueError("Miro Tips must use the exact reference-child snapshot policy")
    if not reference_source_board_id or not reference_source_frame_id or not reference_source_image_id:
        raise ValueError("Miro Tips requires the exact reference board, frame and image identity")
    if int(raw.get("expected_item_count") or 0) != EXPECTED_ITEM_COUNT:
        raise ValueError(f"Miro Tips must declare exactly {EXPECTED_ITEM_COUNT} reference child items")
    if expected_types != EXPECTED_ITEM_TYPE_COUNTS:
        raise ValueError(
            "Miro Tips expected item types must be image=1, sticky_note=13 and text=3"
        )
    connector_count = raw.get("expected_connector_count")
    if connector_count is None or int(connector_count) != EXPECTED_CONNECTOR_COUNT:
        raise ValueError("Miro Tips exact reference has zero connectors")
    if not 2 <= attempts <= 60 or not 0 <= delay <= 2:
        raise ValueError("Miro Tips read-back policy is out of range")
    for key in ("x", "y"):
        if key not in target_position:
            raise ValueError(f"Miro Tips target position is missing {key}")
    for marker in DEFAULT_REQUIRED_MARKERS:
        if marker.casefold() not in required_markers:
            raise ValueError(f"Miro Tips required-marker contract is missing: {marker}")
    for retired in (
        "onboarding",
        "control_anchor_policy",
        "control_anchor_size",
        "endpoint_position_policy",
        "layer_policy",
        "legacy_frame_ids",
        "min_connectors",
    ):
        if raw.get(retired) is not None:
            raise ValueError(f"Miro Tips retired topology field remains: {retired}")

    return {
        "reference_source_board_id": reference_source_board_id,
        "reference_source_frame_id": reference_source_frame_id,
        "reference_source_image_id": reference_source_image_id,
        "target_position": {
            "x": float(target_position["x"]),
            "y": float(target_position["y"]),
        },
        "required_markers": required_markers,
        "readback_attempts": attempts,
        "readback_delay_seconds": delay,
        "expected_item_count": EXPECTED_ITEM_COUNT,
        "expected_item_type_counts": dict(EXPECTED_ITEM_TYPE_COUNTS),
        "expected_connector_count": EXPECTED_CONNECTOR_COUNT,
        "container_policy": container_policy,
        "visual_equivalence_policy": visual_policy,
    }


def _source_spec(manifest: dict[str, Any]) -> dict[str, Any]:
    matches = [
        spec
        for spec in (manifest.get("source_companion_frames") or [])
        if str(spec.get("title") or "") == MIRO_TIPS_TITLE
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {MIRO_TIPS_TITLE!r} companion spec, got {len(matches)}")
    cfg = _config(manifest)
    spec = matches[0]
    if str(spec.get("mode") or "") != MIRO_TIPS_MODE:
        raise ValueError("Miro Tips source companion is not an exact-reference clone")
    if str(spec.get("id") or "") != cfg["reference_source_frame_id"]:
        raise ValueError("Miro Tips source frame differs from the approved reference")
    if str(spec.get("source_board_id") or "") != cfg["reference_source_board_id"]:
        raise ValueError("Miro Tips source board differs from the approved reference")
    return spec


def _visible(value: Any) -> str:
    return base._visible(value).casefold()


def _state(client: Any, board: str, frame_id: str) -> dict[str, Any]:
    items = base._children(client, board, frame_id)
    item_ids = {str(item.get("id") or "") for item in items}
    return {
        "items": items,
        "item_type_counts": dict(Counter(str(item.get("type") or "") for item in items)),
        "connectors": visual._companion_source_connectors(client, board, item_ids),
        "text": " ".join(_visible((item.get("data") or {}).get("content")) for item in items),
    }


def _assert_snapshot(
    state: dict[str, Any], cfg: dict[str, Any], label: str, *, require_reference_image: bool
) -> None:
    if len(state["items"]) != cfg["expected_item_count"]:
        raise ValueError(f"{label} has {len(state['items'])} child items, expected {cfg['expected_item_count']}")
    if state["item_type_counts"] != cfg["expected_item_type_counts"]:
        raise ValueError(
            f"{label} item types differ from exact reference: {state['item_type_counts']}"
        )
    if len(state["connectors"]) != cfg["expected_connector_count"]:
        raise ValueError(f"{label} has connectors; the exact reference has none")
    missing = [marker for marker in cfg["required_markers"] if marker not in state["text"]]
    if missing:
        raise ValueError(f"{label} is missing required reference markers: {missing}")
    if require_reference_image:
        image_ids = [
            str(item.get("id") or "")
            for item in state["items"]
            if str(item.get("type") or "") == "image"
        ]
        if image_ids != [cfg["reference_source_image_id"]]:
            raise ValueError("Miro Tips reference screenshot differs from the approved source image")


def assert_reference_identity(
    client: Any, source_board: str, source_frame_id: str, manifest: dict[str, Any]
) -> None:
    cfg = _config(manifest)
    if str(source_board) != cfg["reference_source_board_id"]:
        raise ValueError("Miro Tips source board differs from the approved reference board")
    if str(source_frame_id) != cfg["reference_source_frame_id"]:
        raise ValueError("Miro Tips source frame differs from the approved reference frame")
    _assert_snapshot(
        _state(client, source_board, source_frame_id),
        cfg,
        "Miro Tips source",
        require_reference_image=True,
    )


def miro_tips_companion_frame_payload(
    source_frame: dict[str, Any],
    source_main: dict[str, Any],
    target_main: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    _ = source_main
    _ = target_main
    cfg = _config(manifest)
    payload: dict[str, Any] = {
        "data": {"title": MIRO_TIPS_TITLE},
        "geometry": deepcopy(source_frame.get("geometry") or {}),
        "position": {**cfg["target_position"], "origin": "center"},
    }
    style = deepcopy(source_frame.get("style") or {})
    if style:
        payload["style"] = style
    return payload


def companion_frame_payload_with_miro_tips(
    source_frame: dict[str, Any],
    source_main: dict[str, Any],
    target_main: dict[str, Any],
) -> dict[str, Any]:
    if str((source_frame.get("data") or {}).get("title") or "") != MIRO_TIPS_TITLE:
        return _ORIGINAL_COMPANION_FRAME_PAYLOAD(source_frame, source_main, target_main)
    return miro_tips_companion_frame_payload(
        source_frame, source_main, target_main, visual._ACTIVE_MANIFEST
    )


def same_frame_defer_miro_tips(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    """The Miro Tips container is an existing protected child frame.

    Its position and geometry are fail-closed verified by
    _assert_target_container before child cloning.  Returning true here avoids
    a destructive PATCH of that valid container.
    """
    if (
        str((remote.get("data") or {}).get("title") or "") == MIRO_TIPS_TITLE
        and str((expected.get("data") or {}).get("title") or "") == MIRO_TIPS_TITLE
    ):
        return True
    return _ORIGINAL_SAME_FRAME(remote, expected)


def _assert_target_container(
    client: Any,
    target_board: str,
    target_frame_id: str,
    source_frame: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    expected = miro_tips_companion_frame_payload(source_frame, {}, {}, manifest)
    target = base._get_frame(client, target_board, target_frame_id)
    if str((target.get("data") or {}).get("title") or "") != MIRO_TIPS_TITLE:
        raise ValueError("Miro Tips target container title mismatch")
    for key, value in (expected.get("geometry") or {}).items():
        if not base._close((target.get("geometry") or {}).get(key), value):
            raise ValueError(f"Miro Tips target container geometry mismatch: {key}")
    for key, value in (expected.get("position") or {}).items():
        if key != "origin" and not base._close((target.get("position") or {}).get(key), value):
            raise ValueError(f"Miro Tips target container position mismatch: {key}")


def _exact_clone_readback(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    cfg = _config(manifest)
    source = _state(client, source_board, source_frame_id)
    target = _state(client, target_board, target_frame_id)
    _assert_snapshot(source, cfg, "Miro Tips source", require_reference_image=True)
    _assert_snapshot(target, cfg, "Miro Tips target", require_reference_image=False)

    used: set[str] = set()
    native_count = 0
    for item in sorted(
        [entry for entry in source["items"] if str(entry.get("type") or "") in visual.NATIVE_TYPES],
        key=lambda entry: (visual.redline.identity(entry), str(entry.get("id") or "")),
    ):
        match = visual.redline.match(item, target["items"], used)
        expected = visual._ORIGINAL_ITEM_PAYLOAD(item, target_frame_id)
        if match is None or not visual.redline.same_item(match, expected):
            raise ValueError(f"Miro Tips target item differs from reference: {item.get('id')}")
        used.add(str(match.get("id") or ""))
        native_count += 1

    source_image = next(
        item for item in source["items"] if str(item.get("type") or "") == "image"
    )
    image_matches = [
        item
        for item in target["items"]
        if visual._same_image(item, source_image, target_frame_id)
    ]
    if len(image_matches) != 1:
        raise ValueError("Miro Tips target screenshot does not match the reference geometry")
    return {
        "policy": MIRO_TIPS_VISUAL_EQUIVALENCE_POLICY,
        "source_item_count": len(source["items"]),
        "target_item_count": len(target["items"]),
        "item_type_counts": dict(EXPECTED_ITEM_TYPE_COUNTS),
        "source_connector_count": len(source["connectors"]),
        "target_connector_count": len(target["connectors"]),
        "native_item_count": native_count,
        "source_image_id": str(source_image.get("id") or ""),
        "target_image_id": str(image_matches[0].get("id") or ""),
        "status": "PASS",
    }


def reconcile_miro_tips_children(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    min_images: int,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    _ = min_images
    _source_spec(manifest)
    assert_reference_identity(client, source_board, source_frame_id, manifest)
    source_frame = base._get_frame(client, source_board, source_frame_id)
    _assert_target_container(client, target_board, target_frame_id, source_frame, manifest)
    result = _ORIGINAL_RECONCILE_COMPANION_CHILDREN(
        client,
        source_board,
        source_frame_id,
        target_board,
        target_frame_id,
        1,
        manifest,
    )
    return {
        "mode": MIRO_TIPS_MODE,
        "container_policy": MIRO_TIPS_CONTAINER_POLICY,
        "visual_equivalence_policy": MIRO_TIPS_VISUAL_EQUIVALENCE_POLICY,
        "reference_source_board_id": _config(manifest)["reference_source_board_id"],
        "reference_source_frame_id": _config(manifest)["reference_source_frame_id"],
        "reference_source_image_id": _config(manifest)["reference_source_image_id"],
        **result,
        "reference_clone": _exact_clone_readback(
            client,
            source_board,
            source_frame_id,
            target_board,
            target_frame_id,
            manifest,
        ),
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
        min_images,
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
