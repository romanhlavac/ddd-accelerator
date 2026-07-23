from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


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
        return self._request("POST", f"boards/{board_id}/{_endpoint(item_type)}", body=payload)

    def update_item(self, board_id: str, item_type: str, item_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", f"boards/{board_id}/{_endpoint(item_type)}/{item_id}", body=payload)

    def delete_item(self, board_id: str, item_id: str) -> None:
        self._request("DELETE", f"boards/{board_id}/items/{item_id}")


def _endpoint(item_type: str) -> str:
    mapping = {"frame": "frames", "sticky_note": "sticky_notes", "shape": "shapes", "text": "texts"}
    if item_type not in mapping:
        raise ValueError(f"Unsupported Miro item type: {item_type}")
    return mapping[item_type]
