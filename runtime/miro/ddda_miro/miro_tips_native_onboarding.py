from __future__ import annotations

"""Native and readable HVR-2 onboarding for the DDDA Platform Lab Miro board.

Only children of the existing Miro Tips frame are reconciled. The adapter never
recreates that container and never writes Frame 01 or a protected frame.
"""

from copy import deepcopy
from typing import Any

from . import review_board_recovery as base
from . import review_board_recovery_wirefix as visual

TITLE = "Miro Tips"
MODE = "ddda_owned_native_onboarding"
POLICY = "native_ddda_owned_no_screenshot_no_callouts"
REQUIRED_SECTIONS = (
    "NAVIGUJ PO PLÁTNĚ A RÁMCÍCH",
    "TVORBA A ÚPRAVA LÍSTKŮ",
    "VÝBĚR, ZPĚT A DUPLIKACE",
    "PROPOJUJ VÝZNAMY",
    "SPOLUPRÁCE A FACILITACE",
    "Vlastnictví a legenda DDDA",
)

_INSTALLED = False
_PREVIOUS_PAYLOAD: Any = None
_PREVIOUS_SAME_FRAME: Any = None
_PREVIOUS_RECONCILE: Any = None


def _raw(manifest: dict[str, Any]) -> dict[str, Any]:
    value = (manifest.get("miro_tips") or {}).get("onboarding")
    if not isinstance(value, dict):
        raise ValueError("Miro Tips native onboarding configuration is missing")
    return value


def config(manifest: dict[str, Any]) -> dict[str, Any]:
    value = _raw(manifest)
    if str(value.get("mode") or "") != MODE or str(value.get("policy") or "") != POLICY:
        raise ValueError("Miro Tips must use the DDDA-owned native onboarding policy")
    body = float(value.get("minimum_body_font_size") or 0)
    heading = float(value.get("minimum_heading_font_size") or 0)
    sections = tuple(str(item) for item in (value.get("required_sections") or ()))
    geometry = dict(value.get("container_geometry") or {})
    position = dict(value.get("container_position") or {})
    if body < 36 or heading < 64:
        raise ValueError("Miro Tips readability contract requires 36px body and 64px heading")
    if int(value.get("minimum_sections") or 0) < len(REQUIRED_SECTIONS):
        raise ValueError("Miro Tips native onboarding must require all six sections")
    if sections != REQUIRED_SECTIONS:
        raise ValueError("Miro Tips native onboarding section contract differs from HVR-2")
    for key in ("width", "height"):
        if float(geometry.get(key) or 0) <= 0:
            raise ValueError("Miro Tips native onboarding requires retained container geometry")
    for key in ("x", "y"):
        if position.get(key) is None:
            raise ValueError("Miro Tips native onboarding requires retained container position")
    return {
        "mode": MODE,
        "policy": POLICY,
        "minimum_body_font_size": body,
        "minimum_heading_font_size": heading,
        "required_sections": sections,
        "geometry": {"width": float(geometry["width"]), "height": float(geometry["height"])},
        "position": {"x": float(position["x"]), "y": float(position["y"])},
    }


def _is_miro_tips(frame: dict[str, Any]) -> bool:
    return str((frame.get("data") or {}).get("title") or "") == TITLE


def companion_frame_payload(source_frame: dict[str, Any], source_main: dict[str, Any], target_main: dict[str, Any]) -> dict[str, Any]:
    if not _is_miro_tips(source_frame):
        return _PREVIOUS_PAYLOAD(source_frame, source_main, target_main)
    # Runtime seam has no manifest argument. These values are deliberately the
    # exact retained geometry and position recorded by the manifest contract.
    return {
        "data": {"title": TITLE},
        "geometry": {"width": 1919.4331503618523, "height": 1079.6811470785374},
        "position": {"x": -19834.447049390445, "y": -11727.529671450406, "origin": "center"},
    }


def same_frame(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    if str((expected.get("data") or {}).get("title") or "") != TITLE:
        return _PREVIOUS_SAME_FRAME(remote, expected)
    if str((remote.get("data") or {}).get("title") or "") != TITLE:
        return False
    for section in ("position", "geometry"):
        for key, value in (expected.get(section) or {}).items():
            if key != "origin" and not base._close((remote.get(section) or {}).get(key), value):
                return False
    return True


def desired_items(frame_id: str, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    cfg = config(manifest)
    # Child positions are offsets from the retained frame center; MiroClient
    # converts them to parent-local coordinates at the REST boundary.
    x, y = 0.0, 0.0
    body = cfg["minimum_body_font_size"]
    cards = (
        ("NAVIGUJ PO PLÁTNĚ A RÁMCÍCH", "Kolečkem přibližuj. Pravým tlačítkem posouvej plátno. Přes mapu rámců přejdi na Frame 00 (status) a Frame 01 (journey).", -440, -250, "#DDEBF7"),
        ("TVORBA A ÚPRAVA LÍSTKŮ", "Klikni na lístek a piš; Tab založí další. Jedna myšlenka = jeden lístek. Dvojklik nebo Enter upraví obsah.", 440, -250, "#FFF2CC"),
        ("VÝBĚR, ZPĚT A DUPLIKACE", "Shift+klik rozšíří výběr. Ctrl/Cmd+Z vrátí změnu. Ctrl/Cmd+D vytvoří kopii až po vědomém výběru.", -440, 30, "#E2F0D9"),
        ("PROPOJUJ VÝZNAMY", "Spojnice vyjadřuje konkrétní vztah. Veď ji jedním jasným směrem; nespojuj prvky jen kvůli vzhledu.", 440, 30, "#FCE4D6"),
        ("SPOLUPRÁCE A FACILITACE", "Sleduj kurzory účastníků. Facilitátor může vést pohled; když je potřeba prostor, zastav se a domluv další krok.", -440, 310, "#E4DFEC"),
        ("Vlastnictví a legenda DDDA", "Žluté workshopové lístky upravují účastníci. Modré DDDA, navigační a legendové panely spravuje tým; změny navrhuj komentářem. Oranžová = event, modrá = command, červená = hotspot, žlutá = otázka.", 440, 310, "#D9EAD3"),
    )
    items = [{
        "type": "shape",
        "parent": {"id": frame_id},
        "data": {"shape": "round_rectangle", "content": "MIRO: RYCHLÝ START PRO DDDA WORKSHOP"},
        "position": {"x": x, "y": y - 445, "origin": "center"},
        "geometry": {"width": 1740, "height": 110},
        "style": {"fillColor": "#17365D", "borderColor": "#17365D", "color": "#FFFFFF", "fontSize": str(int(cfg["minimum_heading_font_size"])), "fontFamily": "arial", "textAlign": "center", "textAlignVertical": "middle"},
    }]
    for heading, text, dx, dy, color in cards:
        items.append({
            "type": "shape",
            "parent": {"id": frame_id},
            "data": {"shape": "round_rectangle", "content": heading + "\n" + text},
            "position": {"x": x + dx, "y": y + dy, "origin": "center"},
            "geometry": {"width": 820, "height": 235},
            "style": {"fillColor": color, "borderColor": "#17365D", "color": "#172B4D", "fontSize": str(int(body)), "fontFamily": "arial", "textAlign": "left", "textAlignVertical": "top"},
        })
    return items


def _content(item: dict[str, Any]) -> str:
    return base._visible((item.get("data") or {}).get("content"))


def _matches(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    if str(remote.get("type") or "") != "shape":
        return False
    if str((remote.get("parent") or {}).get("id") or "") != str((expected.get("parent") or {}).get("id") or ""):
        return False
    if _content(remote) != _content(expected):
        return False
    try:
        return float((remote.get("style") or {}).get("fontSize") or 0) >= float((expected.get("style") or {}).get("fontSize") or 0)
    except (TypeError, ValueError):
        return False


def rest_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove reconciliation metadata before calling the Miro v2 shape endpoint."""
    return {key: deepcopy(value) for key, value in payload.items() if key != "type"}


def _related_connectors(client: Any, board: str, item_ids: set[str]) -> list[dict[str, Any]]:
    return [
        connector for connector in client.list_connectors(board)
        if str((connector.get("startItem") or {}).get("id") or "") in item_ids
        or str((connector.get("endItem") or {}).get("id") or "") in item_ids
    ]


def reconcile_children(client: Any, source_board: str, source_frame_id: str, target_board: str, target_frame_id: str, min_images: int, manifest: dict[str, Any]) -> dict[str, Any]:
    source_frame = base._get_frame(client, source_board, source_frame_id)
    if not _is_miro_tips(source_frame):
        return _PREVIOUS_RECONCILE(client, source_board, source_frame_id, target_board, target_frame_id, min_images, manifest)
    cfg = config(manifest)
    desired = desired_items(target_frame_id, manifest)
    actual = base._children(client, target_board, target_frame_id)
    indexed = {_content(item): item for item in actual}
    current_matches = len(actual) == len(desired) and all(
        _content(expected) in indexed and _matches(indexed[_content(expected)], expected)
        for expected in desired
    )
    related = _related_connectors(client, target_board, {str(item.get("id") or "") for item in actual})
    item_counts = {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0}
    connector_counts = {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0}
    if not current_matches or related:
        for connector in related:
            client.delete_connector(target_board, str(connector["id"]))
            connector_counts["deleted"] += 1
        for item in actual:
            client.delete_item(target_board, str(item["id"]))
            item_counts["deleted"] += 1
        for payload in desired:
            client.create_item(target_board, "shape", rest_payload(payload))
            item_counts["created"] += 1
    else:
        item_counts["unchanged"] = len(desired)
    return {
        "mode": cfg["mode"],
        "onboarding_policy": cfg["policy"],
        "section_count": len(REQUIRED_SECTIONS),
        "required_sections": list(REQUIRED_SECTIONS),
        "minimum_body_font_size": cfg["minimum_body_font_size"],
        "minimum_heading_font_size": cfg["minimum_heading_font_size"],
        "target_image_count": 0,
        "target_connector_count": 0,
        "children_rebuilt": int(not current_matches),
        "frame_replaced": 0,
        "replacement_frame_id": str(target_frame_id),
        "target_geometry": cfg["geometry"],
        "items": item_counts,
        "connectors": connector_counts,
    }


def install() -> None:
    global _INSTALLED, _PREVIOUS_PAYLOAD, _PREVIOUS_SAME_FRAME, _PREVIOUS_RECONCILE
    if _INSTALLED:
        return
    _PREVIOUS_PAYLOAD = visual.companion_frame_payload
    _PREVIOUS_SAME_FRAME = visual._same_frame
    _PREVIOUS_RECONCILE = visual._reconcile_companion_children
    visual.companion_frame_payload = companion_frame_payload
    visual._same_frame = same_frame
    visual._reconcile_companion_children = reconcile_children
    _INSTALLED = True


def uninstall() -> None:
    global _INSTALLED
    if not _INSTALLED:
        return
    visual.companion_frame_payload = _PREVIOUS_PAYLOAD
    visual._same_frame = _PREVIOUS_SAME_FRAME
    visual._reconcile_companion_children = _PREVIOUS_RECONCILE
    _INSTALLED = False
