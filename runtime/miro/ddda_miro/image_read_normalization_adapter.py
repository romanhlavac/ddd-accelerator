from __future__ import annotations

import html
from typing import Any, Callable

from .client import MiroClient


def normalize_miro_image_titles(value: Any) -> Any:
    """Decode HTML entities in image titles returned by Miro without altering other fields."""
    if isinstance(value, list):
        return [normalize_miro_image_titles(item) for item in value]
    if not isinstance(value, dict):
        return value

    normalized = {key: normalize_miro_image_titles(item) for key, item in value.items()}
    if str(normalized.get("type") or "") == "image" and isinstance(normalized.get("data"), dict):
        data = dict(normalized["data"])
        if isinstance(data.get("title"), str):
            data["title"] = html.unescape(data["title"])
        normalized["data"] = data
    return normalized


def install_image_read_normalization_adapter() -> None:
    """Normalize image-title read-back values at the Miro client API boundary."""
    current: Callable[..., Any] = MiroClient._request
    if getattr(current, "_ddda_image_read_normalization_adapter", False):
        return

    def adapted_request(self: MiroClient, method: str, path: str, **kwargs: Any) -> Any:
        return normalize_miro_image_titles(current(self, method, path, **kwargs))

    adapted_request._ddda_image_read_normalization_adapter = True  # type: ignore[attr-defined]
    MiroClient._request = adapted_request  # type: ignore[method-assign]
