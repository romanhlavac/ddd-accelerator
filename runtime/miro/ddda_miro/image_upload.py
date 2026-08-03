from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from copy import deepcopy
from typing import Any, Callable

from .client import MiroApiError, MiroClient, RETRYABLE_HTTP_STATUSES

MAX_IMAGE_BYTES = 6_000_000
ALLOWED_IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/bmp",
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/svg+xml",
        "image/vnd.adobe.photoshop",
    }
)

_SUFFIX_BY_TYPE = {
    "image/bmp": ".bmp",
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/vnd.adobe.photoshop": ".psd",
}


def upload_image_resource(
    client: MiroClient,
    board_id: str,
    prepared_payload: dict[str, Any],
    resource: bytes,
    content_type: str,
    *,
    item_id: str | None = None,
    reconcile: Callable[[], Any | None] | None = None,
) -> dict[str, Any]:
    """Create or update a Miro image through the official multipart resource contract."""
    if len(resource) > MAX_IMAGE_BYTES:
        raise ValueError("Miro image resource exceeds the 6 MB upload limit")
    normalized_type = content_type.split(";", 1)[0].strip().lower()
    if normalized_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValueError(f"Unsupported Miro image content type: {content_type!r}")

    data = deepcopy(prepared_payload)
    image_data = dict(data.pop("data", {}) or {})
    image_data.pop("url", None)
    title = str(image_data.pop("title", "") or "")
    if image_data:
        raise ValueError(f"Unsupported Miro multipart image data fields: {sorted(image_data)}")
    if title:
        data["title"] = title

    boundary = f"ddda-miro-{uuid.uuid4().hex}"
    filename = f"managed-image{_SUFFIX_BY_TYPE[normalized_type]}"
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    body = b"".join(
        [
            f"--{boundary}\r\n".encode("ascii"),
            b'Content-Disposition: form-data; name="data"\r\n',
            b"Content-Type: application/json; charset=utf-8\r\n\r\n",
            data_json,
            b"\r\n",
            f"--{boundary}\r\n".encode("ascii"),
            f'Content-Disposition: form-data; name="resource"; filename="{filename}"\r\n'.encode("ascii"),
            f"Content-Type: {normalized_type}\r\n\r\n".encode("ascii"),
            resource,
            b"\r\n",
            f"--{boundary}--\r\n".encode("ascii"),
        ]
    )

    method = "PATCH" if item_id else "POST"
    path = f"boards/{board_id}/images" + (f"/{item_id}" if item_id else "")
    url = f"{client.base_url.rstrip('/')}/{path}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {client.access_token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "DDDA-Miro/0.2",
    }
    retry_allowed = method == "PATCH" or reconcile is not None

    for attempt in range(client.max_retries + 1):
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=client.timeout_seconds) as response:
                raw = response.read()
                return {} if not raw else json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            retryable = exc.code in RETRYABLE_HTTP_STATUSES and retry_allowed and attempt < client.max_retries
            if retryable:
                if reconcile is not None:
                    recovered = reconcile()
                    if recovered is not None:
                        return recovered
                delay = client._retry_delay(attempt, exc.headers.get("Retry-After"))
                client._log_retry(method, path, attempt, str(exc.code), delay)
                time.sleep(delay)
                continue
            raise MiroApiError(exc.code, method, url, raw) from exc
        except urllib.error.URLError as exc:
            if retry_allowed and attempt < client.max_retries:
                if reconcile is not None:
                    recovered = reconcile()
                    if recovered is not None:
                        return recovered
                delay = client._retry_delay(attempt, None)
                client._log_retry(method, path, attempt, "network", delay)
                time.sleep(delay)
                continue
            raise RuntimeError(f"Miro API {method} {url} failed: {exc}") from exc
    raise AssertionError("unreachable")
