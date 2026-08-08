from __future__ import annotations

import argparse, html, json, os, re, sys, time, urllib.parse
from pathlib import Path
from typing import Any

from .anchor_contract import _close, _get_frame, _patch, _protected_snapshot
from .client import MiroClient
from .frame01_redline import reconcile as reconcile_frame01, same_item
from .yamlio import load_yaml

RID = "REM-PR8-HVA-CC-012.5"
EP = {"shape": "shapes", "text": "texts", "sticky_note": "sticky_notes"}
ROLE_MARKERS = {
    "project_identity": "00 — CONTROL CENTER",
    "decision_now": "ROZHODNUTÍ NYNÍ",
    "phase_gate_state": "FÁZE / GATE",
    "owner_next_action": "ROZHODUJE",
    "attention_blockers": "ATTENTION — 1",
    "artifact_status": "ARTIFACT HEALTH — CURRENT STATUS",
    "artifact_legend": "ARTIFACT LIFECYCLE / MATURITY",
}


def _seg(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def _visible(value: Any) -> str:
    raw = html.unescape(str(value or ""))
    return " ".join(re.sub(r"<[^>]*>", " ", raw).split())


def load_manifest(path: Path) -> dict[str, Any]:
    data = load_yaml(path.resolve())
    if not isinstance(data, dict) or str(data.get("remediation_id") or "") != RID:
        raise ValueError("invalid review-board recovery manifest")
    required = {
        "board_id", "frame_id", "frame00_id", "source_board_id", "source_frame_id",
        "source_frame_title", "protected_frames", "source_sentinels",
        "accepted_frame00_contract", "frame00_sticky_colors",
    }
    missing = sorted(required - set(data))
    if missing or len(data["protected_frames"]) != 16:
        raise ValueError(f"invalid recovery manifest fields/protected frames: {missing}")
    if str(data["frame_id"]) in {str(x) for x in data["protected_frames"]} or str(data["frame00_id"]) in {str(x) for x in data["protected_frames"]}:
        raise ValueError("Frame 00/01 cannot be protected during review-board recovery")
    data["_manifest_path"] = str(path.resolve())
    return data


def _children(client: MiroClient, board: str, frame_id: str) -> list[dict[str, Any]]:
    return [item for item in client.list_items(board) if str((item.get("parent") or {}).get("id") or "") == frame_id]


def _related_connectors(client: MiroClient, board: str, item_ids: set[str]) -> list[dict[str, Any]]:
    return [c for c in client.list_connectors(board) if str((c.get("startItem") or {}).get("id") or "") in item_ids or str((c.get("endItem") or {}).get("id") or "") in item_ids]


def _frame00_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    p = Path(manifest["_manifest_path"]).with_name(str(manifest["accepted_frame00_contract"]))
    data = load_yaml(p)
    if not isinstance(data, dict) or str(data.get("remediation_id") or "") != "REM-PR8-HVA-CC-012.4":
        raise ValueError("accepted Frame 00 contract is missing or invalid")
    if len(data.get("managed_updates") or []) != 8:
        raise ValueError("accepted Frame 00 contract must contain exactly eight managed items")
    return data


def _frame00_content(content: str, manifest: dict[str, Any]) -> str:
    old = "https://miro.com/app/board/uXjVH1phki0=/?moveToWidget=3458764679756478059"
    new = f"https://miro.com/app/board/{manifest['board_id']}/?moveToWidget={manifest['frame_id']}"
    return str(content).replace(old, new)


def frame00_payload(update: dict[str, Any], frame_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    item_type = str(update["type"])
    data: dict[str, Any] = {"content": _frame00_content(str(update.get("content") or ""), manifest)}
    style = dict(update.get("style") or {})
    if item_type == "shape":
        data["shape"] = "rectangle"
        style.setdefault("fontFamily", "arial")
        if update.get("font_size") is not None:
            style["fontSize"] = int(update["font_size"])
        geometry = {"width": float(update["width"]), "height": float(update["height"])}
    elif item_type == "text":
        style.setdefault("fontFamily", "arial")
        if update.get("font_size") is not None:
            style["fontSize"] = int(update["font_size"])
        geometry = {"width": float(update["width"])}
    elif item_type == "sticky_note":
        style = {
            "fillColor": str(manifest["frame00_sticky_colors"][str(update["role"])]),
            "textAlign": "center",
            "textAlignVertical": "middle",
        }
        geometry = {"width": float(update["width"])}
    else:
        raise ValueError(f"unsupported Frame 00 managed type: {item_type}")
    return {
        "data": data,
        "style": style,
        "geometry": geometry,
        "position": {"x": float(update["x"]), "y": float(update["y"]), "origin": "center", "relativeTo": "parent_top_left"},
        "parent": {"id": frame_id},
    }


def _role_match(item: dict[str, Any], update: dict[str, Any], expected: dict[str, Any]) -> bool:
    role = str(update["role"])
    if str(item.get("type") or "") != str(update["type"]):
        return False
    if role == "artifact_panel":
        return not _visible((item.get("data") or {}).get("content")) and _close((item.get("geometry") or {}).get("width"), expected["geometry"]["width"])
    return ROLE_MARKERS[role] in _visible((item.get("data") or {}).get("content"))


def frame00_state(client: MiroClient, manifest: dict[str, Any], contract: dict[str, Any]) -> tuple[bool, dict[str, str]]:
    board, frame_id = str(manifest["board_id"]), str(manifest["frame00_id"])
    frame = _get_frame(client, board, frame_id)
    if not (_close((frame.get("geometry") or {}).get("width"), contract["frame"]["width"]) and _close((frame.get("geometry") or {}).get("height"), contract["frame"]["height"])):
        return False, {}
    items = _children(client, board, frame_id)
    if len(items) != 8:
        return False, {}
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for update in contract["managed_updates"]:
        expected = frame00_payload(update, frame_id, manifest)
        hits = [item for item in items if str(item.get("id") or "") not in used and _role_match(item, update, expected)]
        if len(hits) != 1 or not same_item(hits[0], expected):
            return False, {}
        mapping[str(update["role"])] = str(hits[0]["id"])
        used.add(str(hits[0]["id"]))
    if _related_connectors(client, board, {str(item["id"]) for item in items}):
        return False, {}
    return True, mapping


def _wait_frame_empty(client: MiroClient, board: str, frame_id: str, *, attempts: int = 10, delay_seconds: float = 0.5) -> None:
    for attempt in range(attempts):
        if not _children(client, board, frame_id):
            return
        if attempt + 1 < attempts:
            time.sleep(delay_seconds)
    raise ValueError("Frame 00 children did not disappear after bounded delete wait")


def _resize_frame00(client: MiroClient, board: str, frame_id: str, contract: dict[str, Any]) -> None:
    target = {"width": float(contract["frame"]["width"]), "height": float(contract["frame"]["height"])}
    fresh = _get_frame(client, board, frame_id)
    if _close((fresh.get("geometry") or {}).get("width"), target["width"]) and _close((fresh.get("geometry") or {}).get("height"), target["height"]):
        return
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            _patch(client, board, "frame", frame_id, {"geometry": target})
            last_error = None
            break
        except Exception as exc:  # Miro may lag after child delete/create mutations.
            last_error = exc
            if "Child item cannot be placed outside the bounds of its parent" not in str(exc) or attempt == 4:
                raise
            time.sleep(1.0)
    if last_error is not None:
        raise last_error
    fresh = _get_frame(client, board, frame_id)
    if not (_close((fresh.get("geometry") or {}).get("width"), target["width"]) and _close((fresh.get("geometry") or {}).get("height"), target["height"])):
        raise ValueError("Frame 00 geometry did not converge to accepted contract")


def restore_frame00(client: MiroClient, manifest: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    board, frame_id = str(manifest["board_id"]), str(manifest["frame00_id"])
    ok, mapping = frame00_state(client, manifest, contract)
    if ok:
        return {"created": 0, "deleted": 0, "connectors_deleted": 0, "unchanged": 8, "role_ids": mapping}

    children = _children(client, board, frame_id)
    child_ids = {str(item["id"]) for item in children}
    related = _related_connectors(client, board, child_ids)
    for connector in related:
        client.delete_connector(board, str(connector["id"]))
    for item in children:
        client.delete_item(board, str(item["id"]))
    _wait_frame_empty(client, board, frame_id)

    # Important Miro ordering invariant: create accepted children while the current parent
    # is still large enough, then shrink the parent around children that already fit the
    # accepted 7000 × 4914.42 bounds. Shrinking an empty frame immediately after deletes
    # can transiently fail with 3.0204 because Miro's parent-bound index lags deletion.
    mapping: dict[str, str] = {}
    for update in contract["managed_updates"]:
        item_type = str(update["type"])
        payload = frame00_payload(update, frame_id, manifest)
        created = client._request("POST", f"boards/{_seg(board)}/{EP[item_type]}", body=payload)
        fresh = client._request("GET", f"boards/{_seg(board)}/items/{_seg(created['id'])}")
        if not same_item(fresh, payload):
            raise ValueError(f"recovered Frame 00 role {update['role']} read-back mismatch before parent resize")
        mapping[str(update["role"])] = str(created["id"])

    _resize_frame00(client, board, frame_id, contract)

    # Re-read and, if Miro normalized coordinates while the parent was resized, re-apply
    # the exact accepted relative geometry/content/style before final verification.
    for update in contract["managed_updates"]:
        item_id = mapping[str(update["role"])]
        payload = frame00_payload(update, frame_id, manifest)
        fresh = client._request("GET", f"boards/{_seg(board)}/items/{_seg(item_id)}")
        if not same_item(fresh, payload):
            client._request("PATCH", f"boards/{_seg(board)}/{EP[str(update['type'])]}/{_seg(item_id)}", body=payload)
            fresh = client._request("GET", f"boards/{_seg(board)}/items/{_seg(item_id)}")
            if not same_item(fresh, payload):
                raise ValueError(f"recovered Frame 00 role {update['role']} read-back mismatch after parent resize")

    ok, verified = frame00_state(client, manifest, contract)
    if not ok:
        raise ValueError("recovered Frame 00 did not reach accepted contract")
    return {"created": 8, "deleted": len(children), "connectors_deleted": len(related), "unchanged": 0, "role_ids": verified}


def _resize_frame01(client: MiroClient, manifest: dict[str, Any]) -> int:
    sb, sf, tb, tf = str(manifest["source_board_id"]), str(manifest["source_frame_id"]), str(manifest["board_id"]), str(manifest["frame_id"])
    source, target = _get_frame(client, sb, sf), _get_frame(client, tb, tf)
    sg, tg = source.get("geometry") or {}, target.get("geometry") or {}
    if _close(sg.get("width"), tg.get("width")) and _close(sg.get("height"), tg.get("height")):
        return 0
    _patch(client, tb, "frame", tf, {"geometry": {"width": float(sg["width"]), "height": float(sg["height"])}})
    fresh = _get_frame(client, tb, tf)
    if not (_close((fresh.get("geometry") or {}).get("width"), sg["width"]) and _close((fresh.get("geometry") or {}).get("height"), sg["height"])):
        raise ValueError("Frame 01 geometry did not converge to approved redline")
    return 1


def apply(client: MiroClient, manifest: dict[str, Any], source_sha: str) -> dict[str, Any]:
    board = str(manifest["board_id"])
    protected = [str(x) for x in manifest["protected_frames"]]
    before = _protected_snapshot(client, board, protected)
    contract = _frame00_contract(manifest)
    frame00_first = restore_frame00(client, manifest, contract)
    frame01_resized = _resize_frame01(client, manifest)
    frame01_first = reconcile_frame01(client, manifest)
    middle = _protected_snapshot(client, board, protected)
    if middle["digest"] != before["digest"]:
        raise ValueError("protected frames changed during review-board recovery")
    frame00_second = restore_frame00(client, manifest, contract)
    frame01_second = reconcile_frame01(client, manifest)
    if any(frame00_second[k] for k in ("created", "deleted", "connectors_deleted")) or frame00_second["unchanged"] != 8:
        raise ValueError("second Frame 00 recovery is not zero mutation")
    if any(frame01_second["items"][k] for k in ("created", "updated", "deleted")) or any(frame01_second["connectors"][k] for k in ("created", "updated", "deleted")):
        raise ValueError("second Frame 01 reconcile is not zero mutation")
    after = _protected_snapshot(client, board, protected)
    if after["digest"] != before["digest"]:
        raise ValueError("protected frames changed after recovery verification")
    ok, role_ids = frame00_state(client, manifest, contract)
    if not ok:
        raise ValueError("Frame 00 accepted contract verification failed")
    return {
        "status": "PASS", "remediation_id": RID, "source_sha": source_sha,
        "board_id": board, "frame00_id": str(manifest["frame00_id"]), "frame_id": str(manifest["frame_id"]),
        "source_board_id": str(manifest["source_board_id"]), "source_frame_id": str(manifest["source_frame_id"]),
        "frame00_recovery": {"first_run": frame00_first, "second_run": frame00_second, "accepted_role_ids": role_ids},
        "frame01_recovery": {"frame_resized": frame01_resized, "first_run": frame01_first, "second_run": frame01_second},
        "protected_frames": {"count": 16, "before_digest": before["digest"], "after_digest": after["digest"], "unchanged": True},
        "technical_status": "PASS", "human_review_status": "PENDING", "overall_status": "READY_FOR_HUMAN_REVIEW",
        "frame00_hvr_original_decision": "ACCEPTED", "frame00_visual_equivalence_spot_check": "PENDING",
        "merge_allowed": False, "promotion_allowed": False, "release_allowed": False, "gate_approval_allowed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        result = {"status": "PASS", "remediation_id": RID, "mode": "validate-only"} if not args.apply else apply(MiroClient(os.environ["MIRO_ACCESS_TOKEN"]), manifest, args.source_sha)
        code = 0
    except Exception as exc:  # noqa: BLE001
        result = {
            "status": "FAIL", "remediation_id": RID, "source_sha": args.source_sha,
            "technical_status": "FAIL", "human_review_status": "PENDING", "overall_status": "CHANGES_REQUIRED",
            "merge_allowed": False, "promotion_allowed": False, "release_allowed": False, "gate_approval_allowed": False,
            "error": str(exc),
        }
        code = 1
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stdout if code == 0 else sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
