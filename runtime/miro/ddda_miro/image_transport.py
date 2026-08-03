from __future__ import annotations

import base64
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .client import MiroClient

_MAX_BYTES = 6_000_000


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
        return None


def _read(url: str, token: str | None, timeout: int) -> tuple[bytes, str]:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or (token and host != "api.miro.com"):
        raise ValueError(f"unsafe Miro image resource URL: {url}")
    if not token and host not in {"api.miro.com", "r.miro.com"} and not host.endswith(".miro.com"):
        raise ValueError(f"untrusted Miro image host: {host}")
    headers = {"Accept": "application/json,image/*", "User-Agent": "DDDA-Miro/0.2"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    opener = urllib.request.build_opener(_NoRedirect()) if token else urllib.request.build_opener()
    try:
        response = opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if token and exc.code in {301, 302, 303, 307, 308}:
            location = str(exc.headers.get("Location") or "")
            if not location:
                raise ValueError("Miro image redirect has no Location") from exc
            return _read(location, None, timeout)
        raise
    with response:
        raw = response.read(_MAX_BYTES + 1)
        if len(raw) > _MAX_BYTES:
            raise ValueError("Miro image exceeds 6 MB")
        content_type = str(response.headers.get("Content-Type") or "").split(";", 1)[0].lower()
        return raw, content_type


def source_image(client: MiroClient, board: str, item_id: str) -> tuple[bytes, str, dict[str, Any]]:
    item = client._request("GET", f"boards/{board}/items/{item_id}")
    if str(item.get("type") or "") != "image":
        raise ValueError(f"source item {item_id} is not an image")
    url = str((item.get("data") or {}).get("imageUrl") or "")
    if not url:
        raise ValueError(f"source image {item_id} has no imageUrl")
    raw, content_type = _read(url, client.access_token, client.timeout_seconds)
    if content_type == "application/json" or (not content_type and raw.lstrip().startswith(b"{")):
        resource = json.loads(raw.decode("utf-8"))
        url = str(resource.get("url") or resource.get("downloadUrl") or resource.get("imageUrl") or "")
        if not url:
            raise ValueError(f"source image {item_id} resource has no download URL")
        raw, content_type = _read(url, None, client.timeout_seconds)
    if not content_type.startswith("image/"):
        raise ValueError(f"source image {item_id} returned {content_type!r}")
    return raw, content_type, item


def _same(remote: dict[str, Any], payload: dict[str, Any]) -> bool:
    if (remote.get("data") or {}).get("title") != (payload.get("data") or {}).get("title"):
        return False
    if str((remote.get("parent") or {}).get("id") or "") != str((payload.get("parent") or {}).get("id") or ""):
        return False
    for section in ("position", "geometry"):
        actual, expected = remote.get(section) or {}, payload.get(section) or {}
        for key in ("x", "y", "width", "height"):
            if key in expected and abs(float(actual.get(key)) - float(expected[key])) > 0.5:
                return False
    return True


def reconcile(client: MiroClient, board: str, frame_ids: dict[str, str], manifest: dict[str, Any]) -> dict[str, Any]:
    images = client.list_items(board, "image")
    result = {"created": 0, "updated": 0, "unchanged": 0, "assets": []}
    for asset in manifest["assets"]:
        source, target = asset["source"], asset["target"]
        raw, content_type, item = source_image(client, source["board_id"], str(source["item_id"]))
        if str((item.get("parent") or {}).get("id") or "") != str(source["frame_id"]):
            raise ValueError(f"source parent mismatch for {asset['id']}")
        digest = hashlib.sha256(raw).hexdigest()
        expected = str(source.get("expected_sha256") or "")
        if expected and expected != digest:
            raise ValueError(f"digest mismatch for {asset['id']}")
        if not manifest.get("diagnostic_only") and not expected:
            raise ValueError(f"production asset {asset['id']} must pin expected_sha256")
        width = float(target["width"])
        source_geometry = item.get("geometry") or {}
        height = width * float(source_geometry["height"]) / float(source_geometry["width"])
        title = f"DDDA-IMAGE:{manifest['manifest_id']}:{asset['id']}:sha256={digest}"
        payload = {
            "data": {"title": title, "url": f"data:{content_type};base64,{base64.b64encode(raw).decode('ascii')}"},
            "position": {"x": float(target["position"]["x"]), "y": float(target["position"]["y"]), "origin": "center"},
            "geometry": {"width": width},
            "_ddda_bounds_geometry": {"width": width, "height": height},
            "parent": {"id": frame_ids[target["frame_id"]]},
        }
        prepared = client._prepare_item_payload(board, "text", payload)
        prefix = title.rsplit("sha256=", 1)[0]
        found = [i for i in images if str((i.get("data") or {}).get("title") or "").startswith(prefix)]
        if len(found) > 1:
            raise ValueError(f"duplicate managed images for {asset['id']}")
        if not found:
            remote = client._request("POST", f"boards/{board}/images", body=prepared)
            result["created"] += 1
            images.append(remote)
            action = "created"
        elif _same(found[0], prepared):
            remote, action = found[0], "unchanged"
            result["unchanged"] += 1
        else:
            remote = client._request("PATCH", f"boards/{board}/images/{found[0]['id']}", body=prepared)
            result["updated"] += 1
            images[images.index(found[0])] = remote
            action = "updated"
        result["assets"].append({"asset_id": asset["id"], "action": action, "target_item_id": str(remote["id"]), "sha256": digest, "source_board_id": source["board_id"], "source_frame_id": str(source["frame_id"]), "source_item_id": str(source["item_id"])})
    return result
