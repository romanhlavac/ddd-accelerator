from __future__ import annotations

import json
import time
import urllib.parse
from copy import deepcopy
from typing import Any

from .anchor_contract import ENDPOINT, _get_item, _patch, _writable
from .client import MiroApiError, MiroClient
from .frame00_contract import _matches, _selector_matches, _target_payload


_STICKY_GEOMETRY_ATTEMPTS = 4
_STICKY_GEOMETRY_DELAY_SECONDS = 0.5


def _sticky_geometry_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    geometry = payload.get("geometry")
    if not isinstance(geometry, dict) or geometry.get("width") is None:
        return None
    return {"geometry": {"width": float(geometry["width"])}}


def _sticky_width_matches(readback: dict[str, Any], geometry_payload: dict[str, Any]) -> bool:
    actual = (readback.get("geometry") or {}).get("width")
    expected = (geometry_payload.get("geometry") or {}).get("width")
    try:
        return abs(float(actual) - float(expected)) <= 0.75
    except (TypeError, ValueError):
        return actual == expected


def _finish_sticky_geometry(
    client: MiroClient,
    board: str,
    item_id: str,
    geometry_payload: dict[str, Any],
    target_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    readback: dict[str, Any] = {}
    for _ in range(_STICKY_GEOMETRY_ATTEMPTS):
        # Miro may persist content/position from a combined sticky-note PATCH while
        # retaining the previous geometry. Finish width through a dedicated PATCH,
        # then verify fresh server state. Repeated writes are bounded and idempotent.
        _patch(client, board, "sticky_note", item_id, geometry_payload)
        if _STICKY_GEOMETRY_DELAY_SECONDS > 0:
            time.sleep(_STICKY_GEOMETRY_DELAY_SECONDS)
        readback = _get_item(client, board, item_id)
        if target_payload is not None:
            if _matches(readback, target_payload):
                return readback
        elif _sticky_width_matches(readback, geometry_payload):
            return readback
    return readback


def _restore_deleted(client: MiroClient, board: str, snapshot: dict[str, Any]) -> None:
    item_type = str(snapshot["type"])
    payload = _writable(snapshot)
    if isinstance(payload.get("position"), dict):
        payload["position"].pop("relativeTo", None)
    if item_type == "sticky_note" and isinstance(payload.get("geometry"), dict):
        payload["geometry"] = {"width": payload["geometry"]["width"]}
    segment = urllib.parse.quote(board, safe="")
    client._request("POST", f"boards/{segment}/{ENDPOINT[item_type]}", body=payload)


def rollback(client: MiroClient, board: str, original: dict[str, dict[str, Any]], deleted: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    for item_id, snapshot in reversed(list(original.items())):
        try:
            item_type = str(snapshot["type"])
            payload = _writable(snapshot)
            _patch(client, board, item_type, item_id, payload)
            if item_type == "sticky_note":
                geometry_payload = _sticky_geometry_payload(payload)
                if geometry_payload is not None:
                    readback = _finish_sticky_geometry(client, board, item_id, geometry_payload)
                    if not _sticky_width_matches(readback, geometry_payload):
                        raise ValueError(f"sticky geometry rollback did not converge for {item_id}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"managed {item_id}: {exc}")
    for snapshot in deleted:
        try:
            _restore_deleted(client, board, snapshot)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"deleted {snapshot.get('id')}: {exc}")
    return {"status": "PASS" if not errors else "PARTIAL", "errors": errors}


def reconcile_once(
    client: MiroClient,
    contract: dict[str, Any],
    original: dict[str, dict[str, Any]],
    deleted: list[dict[str, Any]],
) -> dict[str, Any]:
    board, frame_id = str(contract["board_id"]), str(contract["frame"]["id"])
    managed_ids = {str(item["id"]) for item in contract["managed_updates"]}
    result = {"updated": 0, "unchanged": 0, "deleted": 0, "cleanup_absent": 0}
    for update in contract["managed_updates"]:
        item_id = str(update["id"])
        remote = _get_item(client, board, item_id)
        original.setdefault(item_id, deepcopy(remote))
        payload = _target_payload(remote, update, frame_id)
        if _matches(remote, payload):
            result["unchanged"] += 1
        else:
            # PATCH responses are not a stable read-back contract across Miro item
            # types. Verify persisted state with a fresh GET. For sticky notes,
            # Miro can accept content/position while retaining the previous width;
            # finish geometry separately and require bounded convergence.
            item_type = str(update["type"])
            _patch(client, board, item_type, item_id, payload)
            readback = _get_item(client, board, item_id)
            if not _matches(readback, payload) and item_type == "sticky_note":
                geometry_payload = _sticky_geometry_payload(payload)
                if geometry_payload is not None:
                    readback = _finish_sticky_geometry(
                        client,
                        board,
                        item_id,
                        geometry_payload,
                        target_payload=payload,
                    )
            if not _matches(readback, payload):
                fields = ("parent", "data", "style", "geometry", "position")
                actual = {key: readback.get(key) for key in fields if key in readback}
                expected = {key: payload.get(key) for key in fields if key in payload}
                raise ValueError(
                    f"managed role {update['role']} did not reach target; "
                    f"actual={json.dumps(actual, ensure_ascii=False, sort_keys=True)}; "
                    f"expected={json.dumps(expected, ensure_ascii=False, sort_keys=True)}"
                )
            result["updated"] += 1

    for raw_id in contract["cleanup"].get("explicit_item_ids") or []:
        item_id = str(raw_id)
        try:
            remote = _get_item(client, board, item_id)
        except MiroApiError as exc:
            if exc.status == 404:
                result["cleanup_absent"] += 1
                continue
            raise
        if item_id in managed_ids or str((remote.get("parent") or {}).get("id") or "") != frame_id:
            raise ValueError(f"cleanup item {item_id} is outside generated frame-00 scope")
        deleted.append(deepcopy(remote))
        client.delete_item(board, item_id)
        result["deleted"] += 1

    current = [
        item for item in client.list_items(board)
        if str((item.get("parent") or {}).get("id") or "") == frame_id and str(item.get("id") or "") not in managed_ids
    ]
    gone: set[str] = set()
    for selector in contract["cleanup"].get("selectors") or []:
        matches = [item for item in current if str(item.get("id") or "") not in gone and _selector_matches(item, selector)]
        if len(matches) > int(selector.get("max_matches") or 1):
            raise ValueError(f"ambiguous cleanup selector: {selector}")
        for remote in matches:
            item_id = str(remote["id"])
            deleted.append(deepcopy(remote))
            client.delete_item(board, item_id)
            gone.add(item_id)
            result["deleted"] += 1
    return result
