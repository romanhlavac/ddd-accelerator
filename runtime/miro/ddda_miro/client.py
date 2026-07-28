from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .coordinates import frame_center_to_parent_position


# Miro REST API v2 accepts font sizes from the board toolbar scale rather than
# arbitrary integers. Keep the normalization at the API boundary so every
# renderer and sync path uses a value accepted by both text and shape endpoints.
MIRO_REST_FONT_SIZES: tuple[int, ...] = (10, 12, 14, 18, 24, 36, 48, 64, 80, 144, 288)


def normalize_miro_font_size(value: Any) -> int:
    try:
        requested = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Miro font size must be numeric, got {value!r}") from exc
    if requested <= 0:
        raise ValueError(f"Miro font size must be positive, got {value!r}")
    for supported in MIRO_REST_FONT_SIZES:
        if requested <= supported:
            return supported
    return MIRO_REST_FONT_SIZES[-1]


class MiroApiError(RuntimeError):
    def __init__(self, status: int, method: str, url: str, body: str):
        super().__init__(f"Miro API {method} {url} failed with HTTP {status}: {body}")
        self.status = status
        self.method = method
        self.url = url
        self.body = body


@dataclass(slots=True)
class MiroClient:
    access_token: str
    base_url: str = "https://api.miro.com/v2"
    timeout_seconds: int = 45
    max_retries: int = 4
    _frame_geometry_cache: dict[tuple[str, str], dict[str, Any]] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )

    def _request(self, method: str, path: str, *, query: dict[str, Any] | None = None, body: Any | None = None) -> Any:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        if query:
            clean = {key: value for key, value in query.items() if value is not None}
            url = f"{url}?{urllib.parse.urlencode(clean)}"
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "DDDA-Miro/0.2",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        for attempt in range(self.max_retries + 1):
            request = urllib.request.Request(url, data=payload, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    raw = response.read()
                    return None if not raw else json.loads(raw.decode("utf-8"))
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                if exc.code == 429 and attempt < self.max_retries:
                    retry_after = exc.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else min(2**attempt, 16))
                    continue
                raise MiroApiError(exc.code, method, url, raw) from exc
            except urllib.error.URLError as exc:
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 8))
                    continue
                raise RuntimeError(f"Miro API {method} {url} failed: {exc}") from exc
        raise AssertionError("unreachable")

    def _remember_frame_geometry(
        self,
        board_id: str,
        frame_id: str,
        remote: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        geometry = dict(remote.get("geometry") or payload.get("geometry") or {})
        if "width" in geometry and "height" in geometry:
            self._frame_geometry_cache[(board_id, frame_id)] = geometry

    def _frame_geometry(self, board_id: str, frame_id: str) -> dict[str, Any]:
        key = (board_id, frame_id)
        cached = self._frame_geometry_cache.get(key)
        if cached:
            return dict(cached)
        frame_segment = urllib.parse.quote(frame_id, safe="")
        remote = self._request("GET", f"boards/{board_id}/frames/{frame_segment}")
        geometry = dict((remote or {}).get("geometry") or {})
        if "width" not in geometry or "height" not in geometry:
            raise ValueError(f"Miro parent frame {frame_id} has no usable geometry")
        self._frame_geometry_cache[key] = geometry
        return dict(geometry)

    def _prepare_item_payload(
        self,
        board_id: str,
        item_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        prepared = deepcopy(payload)
        if item_type == "frame":
            return prepared
        style = prepared.get("style")
        if item_type in {"text", "shape"} and isinstance(style, dict) and "fontSize" in style:
            style["fontSize"] = normalize_miro_font_size(style["fontSize"])
        parent_id = str((prepared.get("parent") or {}).get("id") or "")
        position = prepared.get("position")
        if parent_id and position:
            prepared["position"] = frame_center_to_parent_position(
                dict(position),
                self._frame_geometry(board_id, parent_id),
                child_geometry=dict(prepared.get("geometry") or {}),
                label=f"{item_type} child of {parent_id}",
            )
        return prepared

    def get_board(self, board_id: str) -> dict[str, Any]:
        return self._request("GET", f"boards/{board_id}")

    def create_board(self, name: str, description: str, *, team_id: str | None = None, project_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "name": name[:60],
            "description": description[:300],
            "policy": {"sharingPolicy": {
                "access": "private",
                "teamAccess": "private",
                "organizationAccess": "private",
                "inviteToAccountAndBoardLinkAccess": "no_access",
            }},
        }
        if team_id:
            body["teamId"] = team_id
        if project_id:
            body["projectId"] = project_id
        return self._request("POST", "boards", body=body)

    def list_items(self, board_id: str, item_type: str | None = None) -> list[dict[str, Any]]:
        cursor: str | None = None
        result: list[dict[str, Any]] = []
        while True:
            page = self._request("GET", f"boards/{board_id}/items", query={"limit": 50, "type": item_type, "cursor": cursor})
            result.extend(page.get("data", []))
            cursor = page.get("cursor")
            if not cursor:
                return result

    def create_item(self, board_id: str, item_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        prepared = self._prepare_item_payload(board_id, item_type, payload)
        remote = self._request("POST", f"boards/{board_id}/{_endpoint(item_type)}", body=prepared)
        if item_type == "frame":
            self._remember_frame_geometry(board_id, str(remote["id"]), remote, prepared)
        return remote

    def update_item(self, board_id: str, item_type: str, item_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        prepared = self._prepare_item_payload(board_id, item_type, payload)
        remote = self._request("PATCH", f"boards/{board_id}/{_endpoint(item_type)}/{item_id}", body=prepared)
        if item_type == "frame":
            self._remember_frame_geometry(board_id, item_id, remote, prepared)
        return remote

    def delete_item(self, board_id: str, item_id: str) -> None:
        self._request("DELETE", f"boards/{board_id}/items/{item_id}")


def _endpoint(item_type: str) -> str:
    mapping = {"frame": "frames", "sticky_note": "sticky_notes", "shape": "shapes", "text": "texts"}
    if item_type not in mapping:
        raise ValueError(f"Unsupported Miro item type: {item_type}")
    return mapping[item_type]
