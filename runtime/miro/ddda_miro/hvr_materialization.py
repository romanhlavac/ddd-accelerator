from __future__ import annotations

"""Materialize the human-review board from a validated Platform Lab board.

This module deliberately has no Platform Lab write capability. The caller
reconciles DDDA_PLATFORM_LAB with its dedicated credential first; this module
uses only the HVR credential to replace the logical ``DDDA_HVR`` slot by a
Miro server-side board copy and then proves that the copied Miro Tips native
reference topology is mechanically identical to the validated Platform Lab
candidate. Human visual acceptance remains separate.
"""

import argparse
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from . import connector_readback_wirefix as connector_contract
from . import frame01_redline as redline
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


def _tips_frame(items: list[dict[str, Any]], label: str) -> dict[str, Any]:
    frames = [
        item
        for item in items
        if item.get("type") == "frame"
        and (item.get("data") or {}).get("title") == tips.MIRO_TIPS_TITLE
    ]
    if len(frames) != 1:
        raise ValueError(f"{label} must contain exactly one Miro Tips frame")
    return frames[0]


def _children(items: list[dict[str, Any]], frame_id: str) -> list[dict[str, Any]]:
    return [
        item
        for item in items
        if str((item.get("parent") or {}).get("id") or "") == str(frame_id)
    ]


def _assert_frame_copy(source: dict[str, Any], target: dict[str, Any]) -> None:
    for section, keys in (("geometry", ("width", "height")), ("position", ("x", "y"))):
        left = source.get(section) or {}
        right = target.get(section) or {}
        for key in keys:
            if key in left and not redline._close(right.get(key), left.get(key)):
                raise ValueError(f"HVR Miro Tips frame {section}.{key} differs from DDDA_PLATFORM_LAB")


def _copy_item_payload(source: dict[str, Any], target_frame_id: str) -> dict[str, Any]:
    """Build a comparison payload without normalizing exact reference font sizes."""
    item_type = str(source.get("type") or "")
    if item_type not in redline.NATIVE:
        raise ValueError(f"unsupported Miro Tips native item type during HVR copy: {item_type}")
    data = {
        key: deepcopy(value)
        for key, value in (source.get("data") or {}).items()
        if key in {"content", "shape"}
    }
    position = source.get("position") or {}
    geometry = source.get("geometry") or {}
    style = source.get("style") or {}
    allowed = {
        "shape": {
            "fillColor", "fillOpacity", "fontFamily", "fontSize", "textAlign",
            "textAlignVertical", "color", "borderColor", "borderOpacity",
            "borderStyle", "borderWidth",
        },
        "text": {"fillColor", "fillOpacity", "fontFamily", "fontSize", "textAlign", "color"},
        "sticky_note": {"fillColor", "textAlign", "textAlignVertical"},
    }[item_type]
    expected: dict[str, Any] = {
        "data": data,
        "position": {
            "x": float(position.get("x") or 0),
            "y": float(position.get("y") or 0),
            "origin": "center",
        },
        "parent": {"id": target_frame_id},
    }
    copied_style = {key: deepcopy(value) for key, value in style.items() if key in allowed}
    if copied_style:
        expected["style"] = copied_style
    if item_type == "shape":
        expected["geometry"] = {
            "width": float(geometry["width"]),
            "height": float(geometry["height"]),
        }
    else:
        expected["geometry"] = {"width": float(geometry["width"])}
    return expected


def _assert_native_copy(
    source_children: list[dict[str, Any]],
    target_children: list[dict[str, Any]],
    target_frame_id: str,
) -> dict[str, str]:
    source_native = [item for item in source_children if str(item.get("type") or "") in redline.NATIVE]
    target_native = [item for item in target_children if str(item.get("type") or "") in redline.NATIVE]
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for source in sorted(source_native, key=lambda item: (redline.identity(item), str(item.get("id") or ""))):
        match = redline.match(source, target_native, used)
        expected = _copy_item_payload(source, target_frame_id)
        if match is None or not redline.same_item(match, expected):
            raise ValueError(f"HVR Miro Tips native item differs from DDDA_PLATFORM_LAB: {source.get('id')}")
        source_id = str(source.get("id") or "")
        target_id = str(match.get("id") or "")
        mapping[source_id] = target_id
        used.add(target_id)
    if len(mapping) != 16 or len(used) != len(target_native):
        raise ValueError("HVR Miro Tips native item mapping is incomplete")
    return mapping


def _assert_image_copy(
    client: MiroClient,
    source_board_id: str,
    target_board_id: str,
    source_children: list[dict[str, Any]],
    target_children: list[dict[str, Any]],
    mapping: dict[str, str],
) -> dict[str, Any]:
    source_images = [item for item in source_children if str(item.get("type") or "") == "image"]
    target_images = [item for item in target_children if str(item.get("type") or "") == "image"]
    if len(source_images) != 1 or len(target_images) != 1:
        raise ValueError("HVR Miro Tips copy must preserve exactly one reference screenshot")
    source = source_images[0]
    target = target_images[0]
    for section, keys in (("geometry", ("width", "height")), ("position", ("x", "y"))):
        left = source.get(section) or {}
        right = target.get(section) or {}
        for key in keys:
            if key in left and not redline._close(right.get(key), left.get(key)):
                raise ValueError(f"HVR Miro Tips screenshot {section}.{key} differs from DDDA_PLATFORM_LAB")
    source_raw, source_type, source_fetched = image_transport.source_image(
        client, source_board_id, str(source.get("id") or "")
    )
    target_raw, target_type, target_fetched = image_transport.source_image(
        client, target_board_id, str(target.get("id") or "")
    )
    if str(source_fetched.get("id") or "") != str(source.get("id") or ""):
        raise ValueError("DDDA_PLATFORM_LAB Miro Tips screenshot read-back identity mismatch")
    if str(target_fetched.get("id") or "") != str(target.get("id") or ""):
        raise ValueError("HVR Miro Tips screenshot read-back identity mismatch")
    source_digest = hashlib.sha256(source_raw).hexdigest()
    target_digest = hashlib.sha256(target_raw).hexdigest()
    if source_digest != target_digest:
        raise ValueError("HVR Miro Tips screenshot bytes differ from DDDA_PLATFORM_LAB")
    mapping[str(source.get("id") or "")] = str(target.get("id") or "")
    return {
        "source_image_id": str(source.get("id") or ""),
        "target_image_id": str(target.get("id") or ""),
        "source_sha256": source_digest,
        "target_sha256": target_digest,
        "source_content_type": source_type,
        "target_content_type": target_type,
    }


def _mapped_connector(source: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    expected: dict[str, Any] = {}
    for endpoint_name in ("startItem", "endItem"):
        endpoint = source.get(endpoint_name) or {}
        mapped_id = mapping.get(str(endpoint.get("id") or ""))
        if not mapped_id:
            raise ValueError(f"HVR Miro Tips connector mapping is incomplete: {source.get('id')}")
        row: dict[str, Any] = {"id": mapped_id}
        for key in ("position", "snapTo"):
            if endpoint.get(key) is not None:
                row[key] = deepcopy(endpoint[key])
        expected[endpoint_name] = row
    if source.get("shape") is not None:
        expected["shape"] = source["shape"]
    if source.get("style"):
        expected["style"] = deepcopy(source["style"])
    if source.get("captions"):
        expected["captions"] = deepcopy(source["captions"])
    return expected


def _assert_connector_copy(
    source_connectors: list[dict[str, Any]],
    target_connectors: list[dict[str, Any]],
    mapping: dict[str, str],
) -> int:
    if len(source_connectors) != tips.EXPECTED_CONNECTOR_COUNT or len(target_connectors) != tips.EXPECTED_CONNECTOR_COUNT:
        raise ValueError("HVR Miro Tips connector count differs from DDDA_PLATFORM_LAB exact reference")
    used: set[str] = set()
    for source in source_connectors:
        expected = _mapped_connector(source, mapping)
        start_id = str((expected.get("startItem") or {}).get("id") or "")
        end_id = str((expected.get("endItem") or {}).get("id") or "")
        matches = [
            candidate
            for candidate in target_connectors
            if str(candidate.get("id") or "") not in used
            and str((candidate.get("startItem") or {}).get("id") or "") == start_id
            and str((candidate.get("endItem") or {}).get("id") or "") == end_id
        ]
        if len(matches) != 1 or not connector_contract.same_connector_canonical(matches[0], expected):
            raise ValueError(f"HVR Miro Tips connector differs from DDDA_PLATFORM_LAB: {source.get('id')}")
        used.add(str(matches[0].get("id") or ""))
    return len(used)


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

    source_frame = _tips_frame(source_items, "DDDA_PLATFORM_LAB")
    target_frame = _tips_frame(target_items, "DDDA_HVR")
    _assert_frame_copy(source_frame, target_frame)
    source_frame_id = str(source_frame.get("id") or "")
    target_frame_id = str(target_frame.get("id") or "")
    source_children = _children(source_items, source_frame_id)
    target_children = _children(target_items, target_frame_id)
    expected_types = Counter(tips.EXPECTED_ITEM_TYPE_COUNTS)
    if Counter(str(item.get("type") or "") for item in source_children) != expected_types:
        raise ValueError("DDDA_PLATFORM_LAB Miro Tips does not contain the exact native reference topology")
    if Counter(str(item.get("type") or "") for item in target_children) != expected_types:
        raise ValueError("HVR Miro Tips does not contain the exact native reference topology")

    mapping = _assert_native_copy(source_children, target_children, target_frame_id)
    image_evidence = _assert_image_copy(
        client, source_board_id, target_board_id, source_children, target_children, mapping
    )
    source_child_ids = {str(item.get("id") or "") for item in source_children}
    target_child_ids = {str(item.get("id") or "") for item in target_children}
    source_connectors = _related_connectors(client, source_board_id, source_child_ids)
    target_connectors = _related_connectors(client, target_board_id, target_child_ids)
    connector_count = _assert_connector_copy(source_connectors, target_connectors, mapping)

    return {
        "source_sha": source_sha,
        "source_board_id": source_board_id,
        "source_board_name": PLATFORM_LAB_NAME,
        "hvr_board_id": target_board_id,
        "hvr_board_name": HVR_NAME,
        "miro_tips": {
            "policy": tips.MIRO_TIPS_VISUAL_EQUIVALENCE_POLICY,
            "source_frame_id": source_frame_id,
            "frame_id": target_frame_id,
            "item_count": len(target_children),
            "item_type_counts": dict(tips.EXPECTED_ITEM_TYPE_COUNTS),
            "connector_count": connector_count,
            "image": image_evidence,
            "status": "PASS",
            "review_url": f"https://miro.com/app/board/{target_board_id}/?moveToWidget={target_frame_id}",
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
