from __future__ import annotations

"""Normalize multipart image upload read-back through the canonical Miro image adapter."""

from typing import Any

from . import image_upload
from .image_read_normalization_adapter import normalize_miro_image_titles


def install_multipart_image_read_normalization_adapter() -> None:
    """Apply the same image-title normalization to multipart upload responses as to MiroClient reads."""
    current = image_upload.upload_image_resource
    if getattr(current, "_ddda_multipart_image_read_normalization_adapter", False):
        return

    def adapted_upload_image_resource(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return normalize_miro_image_titles(current(*args, **kwargs))

    adapted_upload_image_resource._ddda_multipart_image_read_normalization_adapter = True  # type: ignore[attr-defined]
    image_upload.upload_image_resource = adapted_upload_image_resource
