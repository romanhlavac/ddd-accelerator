from __future__ import annotations

import urllib.parse
from copy import deepcopy
from typing import Any

from .anchor_contract import ENDPOINT, _get_item, _patch, _writable
from .client import MiroApiError, MiroClient
from .frame00_contract import _matches, _selector_matches, _target_payload


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
            _patch(client, board, str(snapshot["type"]), item_id, _writable(snapshot))
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
            patched = _patch(client, board, str(update["type"]), item_id, payload)
            if not _matches(patched, payload):
                raise ValueError(f"managed role {update['role']} did not reach target")
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
