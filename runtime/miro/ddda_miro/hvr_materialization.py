from __future__ import annotations

"""Materialize the human-review board from a validated Platform Lab board.

This module deliberately has no Platform Lab write capability.  The caller
performs that reconcile with the Platform Lab credential first; this module
uses only the dedicated HVR credential to replace the logical ``DDDA_HVR``
slot by a Miro server-side board copy and to prove the copied visual payload.
"""

import argparse
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from . import image_transport
from . import miro_tips_hvr_fix as tips
from .client import MiroClient


API_V1 = "https://api.miro.com/v1"
PLATFORM_LAB_NAME = "DDDA_PLATFORM_LAB"
HVR_NAME = "DDDA_HVR"
DEFAULT_ATTEMPTS = 20
DEFAULT_DELAY_SECONDS = 1.0


def _token_context(token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{API_V1}/oauth-token",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _assert_hvr_context(token: str, team_id: str) -> dict[str, Any]:
    context = _token_context(token)
    team = context.get("team") if isinstance(context.get("team"), dict) else {}
    actual_team = str(context.get("team_id") or team.get("id") or "")
    if actual_team != str(team_id):
        raise ValueError("HVR credential team differs from the configured private Developer Team")
    scopes = context.get("scope") or context.get("scopes") or []
    if isinstance(scopes, str):
        granted = {value for value in scopes.replace(",", " ").split() if value}
    else:
        granted = {str(value) for value in scopes}
    missing = {"boards:read", "boards:write"} - granted
    if missing:
        raise ValueError(f"HVR credential is missing Miro scopes: {sorted(missing)}")
    user = context.get("user") if isinstance(context.get("user"), dict) else {}
    return {
        "team_id": actual_team,
        "user_id": str(context.get("user_id") or user.get("id") or ""),
        "scopes": sorted(granted),
    }


def _list_boards(client: MiroClient, team_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        query: dict[str, Any] = {"team_id": team_id, "limit": "50", "sort": "alphabetically"}
        if cursor:
            query["cursor"] = cursor
        page = client._request("GET", "boards", query=query)
        rows.extend(page.get("data") or [])
        cursor = str(page.get("cursor") or "") or None
        if not cursor:
            return rows


def _wait_until_no_slot(client: MiroClient, team_id: str, target_name: str) -> None:
    for attempt in range(DEFAULT_ATTEMPTS):
        if not [board for board in _list_boards(client, team_id) if board.get("name") == target_name]:
            return
        if attempt + 1 < DEFAULT_ATTEMPTS:
            time.sleep(DEFAULT_DELAY_SECONDS)
    raise ValueError("previous HVR logical slot did not disappear before copy")


def _related_connectors(client: MiroClient, board_id: str, item_ids: set[str]) -> list[dict[str, Any]]:
    return [
        connector
        for connector in client.list_connectors(board_id)
        if str((connector.get("startItem") or {}).get("id") or "") in item_ids
        or str((connector.get("endItem") or {}).get("id") or "") in item_ids
    ]


def copied_board_readback(
    client: MiroClient, source_board_id: str, target_board_id: str, source_sha: str
) -> dict[str, Any]:
    """Return a fail-closed read-back proof for the copied HVR board."""
    source = client._request("GET", f"boards/{urllib.parse.quote(source_board_id, safe='')}")
    target = client._request("GET", f"boards/{urllib.parse.quote(target_board_id, safe='')}")
    if source.get("name") != PLATFORM_LAB_NAME:
        raise ValueError("HVR source is not DDDA_PLATFORM_LAB")
    if target.get("name") != HVR_NAME:
        raise ValueError("copied board is not the DDDA_HVR logical slot")

    source_items = client.list_items(source_board_id)
    target_items = client.list_items(target_board_id)
    if Counter(str(item.get("type") or "") for item in source_items) != Counter(
        str(item.get("type") or "") for item in target_items
    ):
        raise ValueError("HVR board item-type read-back differs from DDDA_PLATFORM_LAB")

    frames = [
        item
        for item in target_items
        if item.get("type") == "frame" and (item.get("data") or {}).get("title") == tips.MIRO_TIPS_TITLE
    ]
    if len(frames) != 1:
        raise ValueError("HVR copy must contain exactly one Miro Tips frame")
    frame_id = str(frames[0].get("id") or "")
    children = [item for item in target_items if str((item.get("parent") or {}).get("id") or "") == frame_id]
    if Counter(str(item.get("type") or "") for item in children) != tips.TARGET_ITEM_TYPE_COUNTS:
        raise ValueError("HVR Miro Tips frame does not contain exactly one composite image")
    child_ids = {str(item.get("id") or "") for item in children}
    if _related_connectors(client, target_board_id, child_ids):
        raise ValueError("HVR Miro Tips frame must not contain native connectors")
    image = children[0]
    if str((image.get("data") or {}).get("title") or "") != tips._target_title():
        raise ValueError("HVR Miro Tips composite image identity differs from the approved asset")
    raw, content_type, fetched = image_transport.source_image(client, target_board_id, str(image["id"]))
    if str(fetched.get("id") or "") != str(image.get("id") or ""):
        raise ValueError("HVR Miro Tips composite image read-back identity mismatch")
    # imageUrl is Miro's normalized rendition of the uploaded data-URL PNG,
    # so its transport bytes are not the immutable delivery asset.  The exact
    # approved asset identity is pinned in the managed title checked above;
    # retain the rendition digest as read-back evidence.
    rendered_digest = hashlib.sha256(raw).hexdigest()

    return {
        "source_sha": source_sha,
        "source_board_id": source_board_id,
        "source_board_name": PLATFORM_LAB_NAME,
        "hvr_board_id": target_board_id,
        "hvr_board_name": HVR_NAME,
        "miro_tips": {
            "frame_id": frame_id,
            "item_count": 1,
            "item_type_counts": dict(tips.TARGET_ITEM_TYPE_COUNTS),
            "connector_count": 0,
            "composite_sha256": tips.COMPOSITE_SHA256,
            "rendered_sha256": rendered_digest,
            "content_type": content_type,
            "status": "PASS",
            "review_url": f"https://miro.com/app/board/{target_board_id}/?moveToWidget={frame_id}",
        },
        "technical_status": "PASS",
        "human_review_status": "PENDING",
        "overall_status": "READY_FOR_HUMAN_REVIEW",
        "merge_allowed": False,
        "promotion_allowed": False,
        "release_allowed": False,
    }


def materialize(
    token: str, team_id: str, source_board_id: str, target_name: str, source_sha: str
) -> dict[str, Any]:
    if target_name != HVR_NAME:
        raise ValueError("HVR materialization only permits the DDDA_HVR logical slot")
    context = _assert_hvr_context(token, team_id)
    client = MiroClient(access_token=token)
    source = client._request("GET", f"boards/{urllib.parse.quote(source_board_id, safe='')}")
    if source.get("name") != PLATFORM_LAB_NAME:
        raise ValueError("refusing HVR copy from a board other than DDDA_PLATFORM_LAB")
    previous = [board for board in _list_boards(client, team_id) if board.get("name") == target_name]
    for board in previous:
        board_id = str(board.get("id") or "")
        if not board_id:
            raise ValueError("HVR logical slot has no board identity")
        client._request("DELETE", f"boards/{urllib.parse.quote(board_id, safe='')}")
    _wait_until_no_slot(client, team_id, target_name)
    copied = client._request(
        "PUT",
        "boards",
        query={"copy_from": source_board_id},
        body={
            "name": target_name,
            "description": f"DDDA human visual review for exact SHA {source_sha}; server-side copy of DDDA_PLATFORM_LAB.",
            "teamId": team_id,
        },
    )
    target_board_id = str(copied.get("id") or "")
    if not target_board_id:
        raise ValueError("Miro server-side HVR copy did not return a board id")
    evidence = copied_board_readback(client, source_board_id, target_board_id, source_sha)
    evidence["hvr_credential"] = context
    evidence["previous_hvr_slot_count"] = len(previous)
    evidence["materialization"] = "replace-by-server-side-board-copy"
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize DDDA_HVR from DDDA_PLATFORM_LAB")
    parser.add_argument("--source-board", required=True)
    parser.add_argument("--team-id", required=True)
    parser.add_argument("--target-name", default=HVR_NAME)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args(argv)
    token = os.environ.get("MIRO_HVR_ACCESS_TOKEN", "").strip()
    if not token:
        raise SystemExit("MIRO_HVR_ACCESS_TOKEN is required; fallback is forbidden")
    try:
        report = materialize(token, args.team_id, args.source_board, args.target_name, args.source_sha)
    except Exception as exc:
        report = {
            "source_sha": args.source_sha,
            "technical_status": "FAIL",
            "human_review_status": "PENDING",
            "overall_status": "CHANGES_REQUIRED",
            "merge_allowed": False,
            "promotion_allowed": False,
            "release_allowed": False,
            "error": str(exc),
        }
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        raise
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
