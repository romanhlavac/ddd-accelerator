from __future__ import annotations

from typing import Any


def frame_center_to_parent_position(
    position: dict[str, Any],
    frame_geometry: dict[str, Any],
    *,
    child_geometry: dict[str, Any] | None = None,
    label: str = "child item",
) -> dict[str, Any]:
    """Convert DDDA frame-center coordinates to Miro parent top-left coordinates.

    DDDA authors child layouts around the visual center of a frame. Miro REST API v2,
    however, interprets x/y of an item with ``parent.id`` relative to the parent's
    top-left corner. Keeping the conversion at the API boundary preserves readable
    scaffold coordinates while preventing children from being rejected as outside
    parent boundaries.
    """
    if "width" not in frame_geometry or "height" not in frame_geometry:
        raise ValueError(f"{label}: parent frame geometry requires width and height")

    frame_width = float(frame_geometry["width"])
    frame_height = float(frame_geometry["height"])
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError(f"{label}: parent frame geometry must be positive")

    converted = dict(position)
    converted["x"] = frame_width / 2 + float(position.get("x", 0))
    converted["y"] = frame_height / 2 + float(position.get("y", 0))
    converted.setdefault("origin", "center")

    _assert_child_inside_parent(
        converted,
        frame_geometry,
        child_geometry or {},
        label=label,
    )
    return converted


def _assert_child_inside_parent(
    position: dict[str, Any],
    frame_geometry: dict[str, Any],
    child_geometry: dict[str, Any],
    *,
    label: str,
) -> None:
    frame_width = float(frame_geometry["width"])
    frame_height = float(frame_geometry["height"])
    x = float(position["x"])
    y = float(position["y"])

    if not 0 <= x <= frame_width or not 0 <= y <= frame_height:
        raise ValueError(
            f"{label}: converted child center ({x}, {y}) is outside parent "
            f"boundaries ({frame_width}, {frame_height})"
        )

    width = child_geometry.get("width")
    if width is not None:
        half_width = float(width) / 2
        if x - half_width < 0 or x + half_width > frame_width:
            raise ValueError(
                f"{label}: child width {width} at x={x} exceeds parent width {frame_width}"
            )

    height = child_geometry.get("height")
    if height is not None:
        half_height = float(height) / 2
        if y - half_height < 0 or y + half_height > frame_height:
            raise ValueError(
                f"{label}: child height {height} at y={y} exceeds parent height {frame_height}"
            )
