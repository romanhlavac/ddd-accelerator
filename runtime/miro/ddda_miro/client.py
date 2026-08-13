from __future__ import annotations

import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable

from .coordinates import frame_center_to_parent_position


MIRO_REST_FONT_SIZES: tuple[int, ...] = (10, 12, 14, 18, 24, 36, 48, 64, 80, 144, 288)
RETRYABLE_HTTP_STATUSES: tuple[int, ...] = (429, 500, 502, 503, 504)


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


def normalize_miro_percentage(value: Any) -> str:
    """Normalize connector caption positions to Miro REST's percentage wire format."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.endswith("%"):
            numeric_text = stripped[:-1].strip()
            try:
                percentage = float(numeric_text)
            except ValueError as exc:
                raise ValueError(f"Miro percentage must be numeric, got {value!r}") from exc
        else:
            try:
                fraction = float(stripped)
            except ValueError as exc:
                raise ValueError(f"Miro percentage must be numeric, got {value!r}") from exc
            percentage = fraction * 100 if 0 <= fraction <= 1 else fraction
    else:
        try:
            fraction = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Miro percentage must be numeric, got {value!r}") from exc
        percentage = fraction * 100 if 0 <= fraction <= 1 else fraction

    if not 0 <= percentage <= 100:
        raise ValueError(f"Miro percentage must be between 0% and 100%, got {value!r}")
    return f"{percentage:g}%"


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
    max_retries: int = 5
    retry_base_seconds: float = 1.0
    retry_cap_seconds: float = 30.0
    _frame_geometry_cache: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict, init=False, repr=False)

    def _retry_delay(self, attempt: int, retry_after: str | None) -> float:
        if retry_after:
            try:
                return max(0.0, min(float(retry_after), self.retry_cap_seconds))
            except ValueError:
                pass
        exponential = min(self.retry_base_seconds * (2**attempt), self.retry_cap_seconds)
        return min(exponential + random.uniform(0.0, exponential * 0.25), self.retry_cap_seconds)

    def _log_retry(self, method: str, path: str, attempt: int, status: str, delay: float) -> None:
        print(
            "DDDA Miro retry: "
            f"method={method} endpoint={path} attempt={attempt + 1}/{self.max_retries + 1} "
            f"status={status} delay_seconds={delay:.3f}",
            file=sys.stderr,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
        reconcile: Callable[[], Any | None] | None = None,
    ) -> Any:
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

        idempotent_method = method in {"GET", "HEAD", "OPTIONS", "PUT", "PATCH", "DELETE"}
        retry_allowed = idempotent_method or reconcile is not None
        for attempt in range(self.max_retries + 1):
            request = urllib.request.Request(url, data=payload, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    raw = response.read()
                    return None if not raw else json.loads(raw.decode("utf-8"))
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                retryable = exc.code in RETRYABLE_HTTP_STATUSES and retry_allowed and attempt < self.max_retries
                if retryable:
                    if reconcile is not None:
                        recovered = reconcile()
                        if recovered is not None:
                            return recovered
                    delay = self._retry_delay(attempt, exc.headers.get("Retry-After"))
                    self._log_retry(method, path, attempt, str(exc.code), delay)
                    time.sleep(delay)
                    continue
                raise MiroApiError(exc.code, method, url, raw) from exc
            except urllib.error.URLError as exc:
                if retry_allowed and attempt < self.max_retries:
                    if reconcile is not None:
                        recovered = reconcile()
                        if recovered is not None:
                            return recovered
                    delay = self._retry_delay(attempt, None)
                    self._log_retry(method, path, attempt, "network", delay)
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"Miro API {method} {url} failed: {exc}") from exc
        raise AssertionError("unreachable")

    @staticmethod
    def _close_number(left: Any, right: Any, tolerance: float = 0.5) -> bool:
        try:
            return abs(float(left) - float(right)) <= tolerance
        except (TypeError, ValueError):
            return left == right

    def _equivalent_item(self, remote: dict[str, Any], payload: dict[str, Any]) -> bool:
        remote_data = remote.get("data") or {}
        authored_data = payload.get("data") or {}
        identities = [key for key in ("title", "content") if key in authored_data]
        if identities and not all(remote_data.get(key) == authored_data.get(key) for key in identities):
            return False
        if str((remote.get("parent") or {}).get("id") or "") != str((payload.get("parent") or {}).get("id") or ""):
            return False
        for section in ("position", "geometry"):
            authored = payload.get(section) or {}
            actual = remote.get(section) or {}
            for key in ("x", "y", "width", "height"):
                if key in authored and not self._close_number(actual.get(key), authored.get(key)):
                    return False
        return bool(identities)

    def _find_equivalent_item(self, board_id: str, item_type: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        for item in self.list_items(board_id, item_type):
            if self._equivalent_item(item, payload):
                return item
        return None

    def _remember_frame_geometry(self, board_id: str, frame_id: str, remote: dict[str, Any], payload: dict[str, Any]) -> None:
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

    def _prepare_item_payload(self, board_id: str, item_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        prepared = deepcopy(payload)
        bounds_geometry = dict(prepared.pop("_ddda_bounds_geometry", {}) or {})
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
                child_geometry=bounds_geometry or dict(prepared.get("geometry") or {}),
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
        remote = self._request(
            "POST",
            f"boards/{board_id}/{_endpoint(item_type)}",
            body=prepared,
            reconcile=lambda: self._find_equivalent_item(board_id, item_type, prepared),
        )
        if item_type == "frame":
            self._remember_frame_geometry(board_id, str(remote["id"]), remote, prepared)
        return remote

    def update_item(self, board_id: str, item_type: str, item_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        prepared = self._prepare_item_payload(board_id, item_type, payload)
        remote = self._request("PATCH", f"boards/{board_id}/{_endpoint(item_type)}/{item_id}", body=prepared)
        if item_type == "frame":
            self._remember_frame_geometry(board_id, item_id, remote, prepared)
        return remote

    def list_connectors(self, board_id: str) -> list[dict[str, Any]]:
        cursor: str | None = None
        result: list[dict[str, Any]] = []
        while True:
            page = self._request("GET", f"boards/{board_id}/connectors", query={"limit": 50, "cursor": cursor})
            result.extend(page.get("data", []))
            cursor = page.get("cursor")
            if not cursor:
                return result

    def _prepare_connector_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        prepared = deepcopy(payload)
        for caption in prepared.get("captions") or []:
            if isinstance(caption, dict) and "position" in caption:
                caption["position"] = normalize_miro_percentage(caption["position"])
        return prepared

    def _find_equivalent_connector(self, board_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        expected_start = str((payload.get("startItem") or {}).get("id") or "")
        expected_end = str((payload.get("endItem") or {}).get("id") or "")
        for connector in self.list_connectors(board_id):
            if str((connector.get("startItem") or {}).get("id") or "") == expected_start and str((connector.get("endItem") or {}).get("id") or "") == expected_end:
                return connector
        return None

    def create_connector(self, board_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        prepared = self._prepare_connector_payload(payload)
        return self._request(
            "POST",
            f"boards/{board_id}/connectors",
            body=prepared,
            reconcile=lambda: self._find_equivalent_connector(board_id, prepared),
        )

    def update_connector(self, board_id: str, connector_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        prepared = self._prepare_connector_payload(payload)
        return self._request("PATCH", f"boards/{board_id}/connectors/{connector_id}", body=prepared)

    def delete_connector(self, board_id: str, connector_id: str) -> None:
        self._request("DELETE", f"boards/{board_id}/connectors/{connector_id}")

    def delete_item(self, board_id: str, item_id: str) -> None:
        self._request("DELETE", f"boards/{board_id}/items/{item_id}")


def _endpoint(item_type: str) -> str:
    mapping = {"frame": "frames", "sticky_note": "sticky_notes", "shape": "shapes", "text": "texts"}
    if item_type not in mapping:
        raise ValueError(f"Unsupported Miro item type: {item_type}")
    return mapping[item_type]
