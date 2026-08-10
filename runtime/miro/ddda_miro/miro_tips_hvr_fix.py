from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import review_board_recovery as base
from . import review_board_recovery_wirefix as visual
from .client import normalize_miro_font_size


MIRO_TIPS_TITLE = "Miro Tips"
MIRO_TIPS_MODE = "ddda_owned_hvr_correction"
DEFAULT_WIDTH = 4600.0
DEFAULT_HEIGHT = 2600.0
DEFAULT_MIN_FONT_SIZE = 48
DEFAULT_REQUIRED_SECTIONS = (
    "MIRO QUICK START",
    "1 · NAVIGACE",
    "2 · POZNÁMKY A VÝBĚR",
    "3 · SPOLUPRÁCE",
    "4 · DDDA PRAVIDLA",
)

_ORIGINAL_COMPANION_FRAME_PAYLOAD = visual.companion_frame_payload
_ORIGINAL_RECONCILE_COMPANION_CHILDREN = visual._reconcile_companion_children
_INSTALLED = False


def _config(manifest: dict[str, Any]) -> dict[str, Any]:
    raw = dict(manifest.get("miro_tips") or {})
    width = float(raw.get("width") or DEFAULT_WIDTH)
    height = float(raw.get("height") or DEFAULT_HEIGHT)
    min_font_size = int(raw.get("min_font_size") or DEFAULT_MIN_FONT_SIZE)
    required = tuple(str(value) for value in (raw.get("required_sections") or DEFAULT_REQUIRED_SECTIONS))
    if width < 4200 or height < 2300:
        raise ValueError("Miro Tips frame is below the HVR-2 readable geometry contract")
    if min_font_size < DEFAULT_MIN_FONT_SIZE:
        raise ValueError("Miro Tips minimum font size is below the HVR-2 readability contract")
    if len(required) < len(DEFAULT_REQUIRED_SECTIONS):
        raise ValueError("Miro Tips required-section contract is incomplete")
    for marker in DEFAULT_REQUIRED_SECTIONS:
        if marker not in required:
            raise ValueError(f"Miro Tips required-section contract is missing: {marker}")
    return {
        "width": width,
        "height": height,
        "min_font_size": min_font_size,
        "required_sections": required,
    }


def _source_spec(manifest: dict[str, Any]) -> dict[str, Any]:
    hits = [
        spec
        for spec in (manifest.get("source_companion_frames") or [])
        if str(spec.get("title") or "") == MIRO_TIPS_TITLE
    ]
    if len(hits) != 1:
        raise ValueError(f"expected exactly one {MIRO_TIPS_TITLE!r} companion spec, got {len(hits)}")
    if str(hits[0].get("mode") or "") != MIRO_TIPS_MODE:
        raise ValueError("Miro Tips companion must opt in to the DDDA-owned HVR correction mode")
    return hits[0]


def _shape_payload(
    frame_id: str,
    *,
    content: str,
    x: float,
    y: float,
    width: float,
    height: float,
    font_size: int,
    fill_color: str,
    border_color: str = "#4b79a1",
) -> dict[str, Any]:
    return {
        "data": {"content": content, "shape": "round_rectangle"},
        "style": {
            "fillColor": fill_color,
            "fontFamily": "arial",
            "fontSize": normalize_miro_font_size(font_size),
            "textAlign": "left",
            "textAlignVertical": "top",
            "color": "#102a43",
            "borderColor": border_color,
            "borderWidth": 2,
        },
        "geometry": {"width": float(width), "height": float(height)},
        "position": {"x": float(x), "y": float(y), "origin": "center"},
        "parent": {"id": frame_id},
    }


def _text_payload(
    frame_id: str,
    *,
    content: str,
    x: float,
    y: float,
    width: float,
    font_size: int,
    color: str,
) -> dict[str, Any]:
    return {
        "data": {"content": content},
        "style": {
            "fontFamily": "arial",
            "fontSize": normalize_miro_font_size(font_size),
            "textAlign": "left",
            "color": color,
        },
        "geometry": {"width": float(width)},
        "position": {"x": float(x), "y": float(y), "origin": "center"},
        "parent": {"id": frame_id},
    }


def desired_miro_tips_items(frame_id: str, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    cfg = _config(manifest)
    body_font = max(cfg["min_font_size"], 64)
    return [
        {
            "role": "title",
            "marker": "MIRO QUICK START",
            "payload": _text_payload(
                frame_id,
                content="<p><strong>MIRO QUICK START — DDDA WORKSHOP</strong></p>",
                x=2300,
                y=150,
                width=4200,
                font_size=80,
                color="#1f3b64",
            ),
        },
        {
            "role": "purpose",
            "marker": "2 MINUTY PŘED WORKSHOPEM",
            "payload": _text_payload(
                frame_id,
                content=(
                    "<p><strong>2 MINUTY PŘED WORKSHOPEM:</strong> "
                    "naviguj bezpečně, zapisuj rychle a neměň managed části boardu.</p>"
                ),
                x=2300,
                y=350,
                width=4200,
                font_size=cfg["min_font_size"],
                color="#365a8c",
            ),
        },
        {
            "role": "navigation",
            "marker": "1 · NAVIGACE",
            "payload": _shape_payload(
                frame_id,
                content=(
                    "<p><strong>1 · NAVIGACE</strong></p>"
                    "<p><strong>V</strong> = přepnout navigaci / editaci</p>"
                    "<p><strong>Pravé tlačítko + drag</strong> = posun boardu</p>"
                    "<p><strong>Kolečko / trackpad</strong> = zoom</p>"
                    "<p><strong>Frames / mapa</strong> = rychlý skok mezi oblastmi</p>"
                ),
                x=1200,
                y=950,
                width=2100,
                height=900,
                font_size=body_font,
                fill_color="#e0f2fe",
            ),
        },
        {
            "role": "editing",
            "marker": "2 · POZNÁMKY A VÝBĚR",
            "payload": _shape_payload(
                frame_id,
                content=(
                    "<p><strong>2 · POZNÁMKY A VÝBĚR</strong></p>"
                    "<p><strong>Dvojklik</strong> = nový sticky · <strong>Tab</strong> = další sticky</p>"
                    "<p><strong>Shift + drag</strong> = vybrat více položek</p>"
                    "<p><strong>Alt + drag</strong> = kopie vybraného prvku</p>"
                    "<p><strong>Ctrl+Z</strong> = vrátit nechtěnou změnu</p>"
                ),
                x=3400,
                y=950,
                width=2100,
                height=900,
                font_size=body_font,
                fill_color="#fef3c7",
                border_color="#b45309",
            ),
        },
        {
            "role": "collaboration",
            "marker": "3 · SPOLUPRÁCE",
            "payload": _shape_payload(
                frame_id,
                content=(
                    "<p><strong>3 · SPOLUPRÁCE</strong></p>"
                    "<p><strong>Klikni na avatar facilitátora</strong> = Follow jeho pohledu</p>"
                    "<p>Kurzory ostatních můžeš podle potřeby skrýt / zobrazit.</p>"
                    "<p>Pracuj v právě otevřené workshopové oblasti.</p>"
                    "<p>Nejasnost označ podle legendy jako <strong>HOTSPOT</strong> nebo <strong>OTÁZKA?</strong></p>"
                ),
                x=1200,
                y=1950,
                width=2100,
                height=900,
                font_size=body_font,
                fill_color="#dcfce7",
                border_color="#3f7d4a",
            ),
        },
        {
            "role": "ddda_rules",
            "marker": "4 · DDDA PRAVIDLA",
            "payload": _shape_payload(
                frame_id,
                content=(
                    "<p><strong>4 · DDDA PRAVIDLA</strong></p>"
                    "<p><strong>Neupravuj 00 Control Center ani 01 Journey.</strong></p>"
                    "<p>Managed části jsou projekce Git/YAML; edituj jen plochy určené účastníkům.</p>"
                    "<p>Barvy a notaci určuje legenda aktuálního workshopu.</p>"
                    "<p>Gate a architektonické rozhodnutí je vždy explicitní lidský krok.</p>"
                ),
                x=3400,
                y=1950,
                width=2100,
                height=900,
                font_size=body_font,
                fill_color="#ede9fe",
                border_color="#6d5aa8",
            ),
        },
    ]


def miro_tips_companion_frame_payload(
    source_frame: dict[str, Any],
    source_main: dict[str, Any],
    target_main: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    payload = _ORIGINAL_COMPANION_FRAME_PAYLOAD(source_frame, source_main, target_main)
    if str((source_frame.get("data") or {}).get("title") or "") != MIRO_TIPS_TITLE:
        return payload
    cfg = _config(manifest)
    payload["geometry"] = {"width": cfg["width"], "height": cfg["height"]}
    return payload


def companion_frame_payload_with_miro_tips(
    source_frame: dict[str, Any],
    source_main: dict[str, Any],
    target_main: dict[str, Any],
) -> dict[str, Any]:
    manifest = visual._ACTIVE_MANIFEST
    return miro_tips_companion_frame_payload(source_frame, source_main, target_main, manifest)


def _fresh_item(client: Any, board: str, item_id: str) -> dict[str, Any]:
    return client._request("GET", f"boards/{base._seg(board)}/items/{base._seg(item_id)}")


def reconcile_miro_tips_children(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    cfg = _config(manifest)
    desired = desired_miro_tips_items(target_frame_id, manifest)
    target_items = base._children(client, target_board, target_frame_id)
    original_target_ids = {str(item["id"]) for item in target_items}

    source_items = base._children(client, source_board, source_frame_id)
    source_images = [item for item in source_items if str(item.get("type") or "") == "image"]
    source_connectors = visual._companion_source_connectors(
        client, source_board, {str(item["id"]) for item in source_items}
    )

    target_connectors = base._related_connectors(client, target_board, original_target_ids)
    connector_counts = {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0}
    for connector in target_connectors:
        client.delete_connector(target_board, str(connector["id"]))
        connector_counts["deleted"] += 1

    used: set[str] = set()
    counts = {"created": 0, "updated": 0, "unchanged": 0, "deleted": 0}
    for managed in desired:
        marker = str(managed["marker"])
        payload = deepcopy(managed["payload"])
        item_type = "shape" if "shape" in (payload.get("data") or {}) else "text"
        hits = [
            item
            for item in target_items
            if str(item.get("id") or "") not in used
            and str(item.get("type") or "") == item_type
            and marker in base._visible((item.get("data") or {}).get("content"))
        ]
        if len(hits) > 1:
            raise ValueError(f"multiple Miro Tips items match managed marker {marker!r}")
        if not hits:
            endpoint = base.EP[item_type]
            created = client._request(
                "POST",
                f"boards/{base._seg(target_board)}/{endpoint}",
                body=payload,
            )
            item = _fresh_item(client, target_board, str(created["id"]))
            target_items.append(item)
            counts["created"] += 1
        else:
            item = hits[0]
            if visual.redline.same_item(item, payload):
                counts["unchanged"] += 1
            else:
                endpoint = base.EP[item_type]
                client._request(
                    "PATCH",
                    f"boards/{base._seg(target_board)}/{endpoint}/{base._seg(str(item['id']))}",
                    body=payload,
                )
                item = _fresh_item(client, target_board, str(item["id"]))
                counts["updated"] += 1
        if not visual.redline.same_item(item, payload):
            raise ValueError(f"Miro Tips managed item {managed['role']} did not converge")
        used.add(str(item["id"]))

    extras = [item for item in target_items if str(item.get("id") or "") not in used]
    for item in extras:
        client.delete_item(target_board, str(item["id"]))
        counts["deleted"] += 1

    final_items = base._children(client, target_board, target_frame_id)
    if len(final_items) != len(desired):
        raise ValueError(
            f"Miro Tips final item count mismatch: {len(final_items)} != {len(desired)}"
        )
    if any(str(item.get("type") or "") == "image" for item in final_items):
        raise ValueError("Miro Tips must not depend on screenshot/image content")

    final_text = " ".join(
        base._visible((item.get("data") or {}).get("content")) for item in final_items
    )
    for marker in cfg["required_sections"]:
        if marker not in final_text:
            raise ValueError(f"Miro Tips final content missing required section: {marker}")

    for managed in desired:
        payload = managed["payload"]
        style = payload.get("style") or {}
        if int(style.get("fontSize") or 0) < cfg["min_font_size"]:
            raise ValueError(f"Miro Tips managed item below minimum font size: {managed['role']}")

    return {
        "mode": MIRO_TIPS_MODE,
        "source_item_count": len(source_items),
        "source_image_count": len(source_images),
        "source_connector_count": len(source_connectors),
        "target_image_count": 0,
        "min_font_size": cfg["min_font_size"],
        "required_sections_count": len(cfg["required_sections"]),
        "managed_item_count": len(desired),
        "items": counts,
        "connectors": connector_counts,
    }


def reconcile_companion_children_with_miro_tips(
    client: Any,
    source_board: str,
    source_frame_id: str,
    target_board: str,
    target_frame_id: str,
    min_images: int,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    spec = _source_spec(manifest)
    if str(source_frame_id) != str(spec["id"]):
        return _ORIGINAL_RECONCILE_COMPANION_CHILDREN(
            client,
            source_board,
            source_frame_id,
            target_board,
            target_frame_id,
            min_images,
            manifest,
        )
    return reconcile_miro_tips_children(
        client,
        source_board,
        source_frame_id,
        target_board,
        target_frame_id,
        manifest,
    )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    visual.companion_frame_payload = companion_frame_payload_with_miro_tips
    visual._reconcile_companion_children = reconcile_companion_children_with_miro_tips
    _INSTALLED = True


def uninstall() -> None:
    global _INSTALLED
    if not _INSTALLED:
        return
    visual.companion_frame_payload = _ORIGINAL_COMPANION_FRAME_PAYLOAD
    visual._reconcile_companion_children = _ORIGINAL_RECONCILE_COMPANION_CHILDREN
    _INSTALLED = False
