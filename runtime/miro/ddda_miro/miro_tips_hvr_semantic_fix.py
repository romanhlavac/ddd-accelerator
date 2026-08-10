from __future__ import annotations

from typing import Any

from . import review_board_recovery as base
from . import review_board_recovery_wirefix as visual
from . import miro_tips_hvr_fix as tips


_ORIGINAL_SAME_ITEM = visual.redline.same_item
_ORIGINAL_TIPS_RECONCILE: Any | None = None
_INSTALLED = False


def _same_color(left: Any, right: Any) -> bool:
    return str(left or "").casefold() == str(right or "").casefold()


def semantic_mismatches(remote: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    """Compare stable authored semantics and tolerate omitted/defaulted Miro wire fields."""
    mismatches: list[str] = []

    remote_data = remote.get("data") or {}
    expected_data = expected.get("data") or {}
    if visual.redline.canonical_miro_text(remote_data.get("content")) != visual.redline.canonical_miro_text(
        expected_data.get("content")
    ):
        mismatches.append("data.content")
    if expected_data.get("shape") and remote_data.get("shape") != expected_data.get("shape"):
        mismatches.append("data.shape")

    if str((remote.get("parent") or {}).get("id") or "") != str(
        (expected.get("parent") or {}).get("id") or ""
    ):
        mismatches.append("parent.id")

    for section in ("position", "geometry"):
        remote_section = remote.get(section) or {}
        for key, expected_value in (expected.get(section) or {}).items():
            if key == "origin":
                continue
            if not visual.redline._close(remote_section.get(key), expected_value):
                mismatches.append(f"{section}.{key}")

    remote_style = remote.get("style") or {}
    expected_style = expected.get("style") or {}

    # These are HVR-critical and must be observable on REST read-back.
    for key in ("fontSize", "fillColor", "color", "borderColor"):
        if key not in expected_style:
            continue
        actual = remote_style.get(key)
        authored = expected_style[key]
        if key == "fontSize":
            if not visual.redline._close(actual, authored):
                mismatches.append(f"style.{key}")
        elif not _same_color(actual, authored):
            mismatches.append(f"style.{key}")

    # Miro may omit/default these fields on list read-back. If returned, they must agree.
    for key in ("fontFamily", "textAlign", "textAlignVertical"):
        if key in expected_style and key in remote_style and remote_style.get(key) != expected_style.get(key):
            mismatches.append(f"style.{key}")
    if "borderWidth" in expected_style and "borderWidth" in remote_style:
        if not visual.redline._close(remote_style.get("borderWidth"), expected_style.get("borderWidth")):
            mismatches.append("style.borderWidth")

    return mismatches


def same_miro_tips_item(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    return not semantic_mismatches(remote, expected)


def reconcile_with_semantic_comparator(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    min_images: int,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    if _ORIGINAL_TIPS_RECONCILE is None:
        raise RuntimeError("Miro Tips semantic comparator is not installed")
    spec = tips._source_spec(manifest)
    if str(source_frame_id) != str(spec["id"]):
        return _ORIGINAL_TIPS_RECONCILE(
            client,
            source_board,
            source_frame_id,
            target_board,
            target_frame_id,
            min_images,
            manifest,
        )

    visual.redline.same_item = same_miro_tips_item
    try:
        return _ORIGINAL_TIPS_RECONCILE(
            client,
            source_board,
            source_frame_id,
            target_board,
            target_frame_id,
            min_images,
            manifest,
        )
    except ValueError as exc:
        # Improve evidence if an authored invariant still differs after wire normalization.
        if "did not converge" in str(exc):
            desired = tips.desired_miro_tips_items(target_frame_id, manifest)
            current = base._children(client, target_board, target_frame_id)
            diagnostics: list[str] = []
            for managed in desired:
                marker = str(managed["marker"])
                hits = [
                    item
                    for item in current
                    if marker in base._visible((item.get("data") or {}).get("content"))
                ]
                if len(hits) == 1:
                    diff = semantic_mismatches(hits[0], managed["payload"])
                    diagnostics.append(f"{managed['role']}={','.join(diff) if diff else 'semantic-match'}")
            raise ValueError(f"{exc}; semantic_diagnostics={';'.join(diagnostics)}") from exc
        raise
    finally:
        visual.redline.same_item = _ORIGINAL_SAME_ITEM


def install() -> None:
    global _INSTALLED, _ORIGINAL_TIPS_RECONCILE
    if _INSTALLED:
        return
    _ORIGINAL_TIPS_RECONCILE = visual._reconcile_companion_children
    visual._reconcile_companion_children = reconcile_with_semantic_comparator
    _INSTALLED = True


def uninstall() -> None:
    global _INSTALLED, _ORIGINAL_TIPS_RECONCILE
    if not _INSTALLED:
        return
    if _ORIGINAL_TIPS_RECONCILE is not None:
        visual._reconcile_companion_children = _ORIGINAL_TIPS_RECONCILE
    visual.redline.same_item = _ORIGINAL_SAME_ITEM
    _ORIGINAL_TIPS_RECONCILE = None
    _INSTALLED = False
