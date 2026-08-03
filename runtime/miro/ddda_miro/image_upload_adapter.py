from __future__ import annotations

import base64
from typing import Any, Callable

from .client import MiroClient
from .image_upload import upload_image_resource


def install_image_upload_adapter() -> None:
    """Route existing data-URL image requests through multipart upload without changing callers."""
    current = MiroClient._request
    if getattr(current, "_ddda_multipart_image_adapter", False):
        return

    def adapted_request(
        self: MiroClient,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
        reconcile: Callable[[], Any | None] | None = None,
    ) -> Any:
        clean_path = path.strip("/")
        parts = clean_path.split("/")
        is_image_write = (
            method in {"POST", "PATCH"}
            and len(parts) in {3, 4}
            and parts[0] == "boards"
            and parts[2] == "images"
            and isinstance(body, dict)
        )
        data_url = str(((body or {}).get("data") or {}).get("url") or "")
        if is_image_write and data_url.startswith("data:"):
            metadata, separator, encoded = data_url.partition(",")
            if not separator or ";base64" not in metadata:
                raise ValueError("Managed Miro image data URL must use base64 encoding")
            content_type = metadata[5:].split(";", 1)[0]
            try:
                resource = base64.b64decode(encoded, validate=True)
            except ValueError as exc:
                raise ValueError("Managed Miro image data URL contains invalid base64") from exc
            return upload_image_resource(
                self,
                parts[1],
                body,
                resource,
                content_type,
                item_id=parts[3] if len(parts) == 4 else None,
                reconcile=reconcile,
            )
        return current(self, method, path, query=query, body=body, reconcile=reconcile)

    adapted_request._ddda_multipart_image_adapter = True  # type: ignore[attr-defined]
    MiroClient._request = adapted_request  # type: ignore[method-assign]
