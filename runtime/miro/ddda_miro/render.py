from __future__ import annotations

import html
import time
from pathlib import Path
from typing import Any

from .client import MiroClient
from .config import ProjectConfig
from .state import load_map, save_map, utc_now
from .yamlio import load_yaml

MOJIBAKE_MARKERS = ("â€“", "â€”", "Ă", "Ĺ", "Ä", "�")
GATE_IDS = [f"G{index}" for index in range(1, 9)]
GATE_STATUS_IDS = ["not_ready", "ready_for_review", "conditional", "rejected", "passed"]
EXPECTED_STAGES = ["align", "discover", "decompose", "strategize", "connect", "organize", "define", "code"]


def _walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def assert_utf8_contract(value: Any, *, label: str) -> None:
    failures: list[str] = []
    for text in _walk_strings(value):
        marker = next((item for item in MOJIBAKE_MARKERS if item in text), None)
        if marker:
            failures.append(f"{marker!r} in {text[:100]!r}")
    if failures:
        raise ValueError(f"UTF-8 contract failed for {label}: {'; '.join(failures[:10])}")


def _bounds(item: dict[str, Any]) -> tuple[float, float, float, float]:
    position = item.get("position") or item
    geometry = item.get("geometry") or item
    x = float(position.get("x", item.get("x", 0)))
    y = float(position.get("y", item.get("y", 0)))
    width = float(geometry.get("width", item.get("width", 0)))
    height = float(geometry.get("height", item.get("height", 0)))
    return x - width / 2, y - height / 2, x + width / 2, y + height / 2


def _overlaps(left: dict[str, Any], right: dict[str, Any], *, gap: float = 0) -> bool:
    ll, lt, lr, lb = _bounds(left)
    rl, rt, rr, rb = _bounds(right)
    return not (
        lr + gap <= rl
        or rr + gap <= ll
        or lb + gap <= rt
        or rb + gap <= lt
    )


def _inside(inner: dict[str, Any], outer: dict[str, Any], *, margin: float = 0) -> bool:
    il, it, ir, ib = _bounds(inner)
    ol, ot, or_, ob = _bounds(outer)
    return il >= ol + margin and it >= ot + margin and ir <= or_ - margin and ib <= ob - margin


def validate_layout_contract(scaffold: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    method_flow = scaffold.get("method_flow") or {}
    stages = method_flow.get("stages") or []
    gates = scaffold.get("gates") or []
    frames = scaffold.get("frames") or []
    states = scaffold.get("gate_states") or []
    traceability = scaffold.get("traceability") or []
    placements = scaffold.get("managed_placements") or {}
    zones = scaffold.get("zones") or []
    transitions = scaffold.get("method_transitions") or []
    stage_templates = scaffold.get("stage_visual_templates") or {}
    example_templates = scaffold.get("example_templates") or {}
    contract = scaffold.get("visual_contract") or {}
    coordinate = scaffold.get("coordinate_system") or {}
    minimum_fonts = coordinate.get("minimum_font_size") or {}

    stage_ids = [str(item.get("id") or "") for item in stages]
    gate_ids = [str(item.get("id") or "") for item in gates]
    frame_ids = {str(item.get("id") or "") for item in frames}
    state_ids = [str(item.get("id") or "") for item in states]
    traced_gates = [str(item.get("gate") or "") for item in traceability]

    if stage_ids != EXPECTED_STAGES:
        failures.append(f"method_flow stages must be {EXPECTED_STAGES}, got {stage_ids}")
    if gate_ids != GATE_IDS:
        failures.append(f"gates must be {GATE_IDS}, got {gate_ids}")
    if state_ids != GATE_STATUS_IDS:
        failures.append(f"gate states must be {GATE_STATUS_IDS}, got {state_ids}")
    if "control-center" not in frame_ids:
        failures.append("control-center frame is missing")
    overview_id = str(contract.get("overview_frame") or "method-overview")
    if overview_id not in frame_ids:
        failures.append(f"overview frame {overview_id} is missing")
    if sorted(traced_gates) != sorted(GATE_IDS):
        failures.append("traceability must cover G1–G8 exactly once")

    frame_by_id = {str(item.get("id") or ""): item for item in frames}
    overview = frame_by_id.get(overview_id) or {}
    stage_card = coordinate.get("stage_card") or {}
    stage_width = float(stage_card.get("width", 0))
    stage_height = float(stage_card.get("height", 0))
    minimum_stage_width = float(contract.get("minimum_stage_card_width", 0))
    minimum_stage_height = float(contract.get("minimum_stage_card_height", 0))
    if stage_width < minimum_stage_width or stage_height < minimum_stage_height:
        failures.append(
            f"stage cards must be at least {minimum_stage_width}x{minimum_stage_height}, "
            f"got {stage_width}x{stage_height}"
        )

    stage_boxes: list[dict[str, Any]] = []
    for stage in stages:
        stage_id = str(stage.get("id") or "")
        work_frame = str(stage.get("work_frame") or "")
        if not work_frame or work_frame not in frame_ids:
            failures.append(f"stage {stage_id} does not reference an existing work frame")
        template_id = str(stage.get("visual_template") or "")
        template = stage_templates.get(template_id) or {}
        minimum_stage_visuals = int(contract.get("minimum_stage_visual_items", 4))
        if len(template.get("items") or []) < minimum_stage_visuals:
            failures.append(f"stage {stage_id} must reference a visual template with at least {minimum_stage_visuals} items")
        for link_name in ("cookbook_url", "method_url", "starter_reference_url"):
            if not str(stage.get(link_name) or "").startswith("https://"):
                failures.append(f"stage {stage_id} has no usable {link_name}")
        box = {
            "id": stage_id,
            "x": float(stage.get("x", 0)),
            "y": float(stage.get("y", 0)),
            "width": stage_width,
            "height": stage_height,
        }
        stage_boxes.append(box)
        if overview and not _inside(box, overview, margin=300):
            failures.append(f"stage card {stage_id} is outside overview frame {overview_id}")

    for index, left in enumerate(stage_boxes):
        for right in stage_boxes[index + 1 :]:
            if _overlaps(left, right, gap=250):
                failures.append(f"stage cards {left['id']} and {right['id']} overlap or are too close")

    required_placements = {
        "project-charter": "control-center",
        "ddda.current-status": "control-center",
        "ddda.next-actions": "control-center",
    }
    for artifact_id, expected_frame in required_placements.items():
        placement = placements.get(artifact_id) or {}
        if placement.get("frame_id") != expected_frame:
            failures.append(f"managed placement {artifact_id} must use frame_id={expected_frame}")
        position = placement.get("position") or {}
        if "x" not in position or "y" not in position:
            failures.append(f"managed placement {artifact_id} must have deterministic x/y")

    minimum_frame_width = float(contract.get("minimum_work_frame_width", 0))
    minimum_frame_height = float(contract.get("minimum_work_frame_height", 0))
    minimum_gap = float(contract.get("minimum_frame_gap", 0))
    work_frames = [frame for frame in frames if str(frame.get("role") or "work") != "overview"]
    for frame in work_frames:
        frame_id = str(frame.get("id") or "")
        if not frame.get("purpose_cs"):
            failures.append(f"frame {frame_id} has no purpose")
        if not frame.get("scaffold"):
            failures.append(f"frame {frame_id} has no workshop structure")
        if float(frame.get("width", 0)) < minimum_frame_width:
            failures.append(f"frame {frame_id} is narrower than {minimum_frame_width}")
        if float(frame.get("height", 0)) < minimum_frame_height:
            failures.append(f"frame {frame_id} is shorter than {minimum_frame_height}")
        if frame_id != "control-center":
            guide = frame.get("guide") or {}
            for field in ("start_cs", "outputs_cs", "cookbook_url", "method_url", "starter_reference_url"):
                if not guide.get(field):
                    failures.append(f"frame {frame_id} guide is missing {field}")
            template_id = str(frame.get("example_template") or "")
            template = example_templates.get(template_id) or {}
            if len(template.get("items") or []) < int(contract.get("minimum_example_items", 3)):
                failures.append(f"frame {frame_id} has no useful mini-example template")
            else:
                example_layout, _title = _template_layout(frame, template)
                local_frame = {"x": 0, "y": 0, "width": frame.get("width", 0), "height": frame.get("height", 0)}
                for example_id, (x, y, width, height) in example_layout.items():
                    if not _inside({"x": x, "y": y, "width": width, "height": height}, local_frame, margin=120):
                        failures.append(f"frame {frame_id} mini-example {example_id} is outside parent boundaries")

    for index, left in enumerate(work_frames):
        for right in work_frames[index + 1 :]:
            if _overlaps(left, right, gap=minimum_gap):
                failures.append(f"work frames {left.get('id')} and {right.get('id')} overlap or violate minimum gap")

    zone_stage_ids = [str(stage_id) for zone in zones for stage_id in (zone.get("stages") or [])]
    if sorted(zone_stage_ids) != sorted(EXPECTED_STAGES):
        failures.append("zone headers must cover every stage exactly once")
    if len(zones) != 4:
        failures.append("exactly four high-level methodological zones are required")

    forward_pairs = {(str(item.get("from")), str(item.get("to"))) for item in transitions if item.get("kind") == "forward"}
    required_forward = {
        ("align", "discover"),
        ("discover", "decompose"),
        ("decompose", "strategize"),
        ("strategize", "connect"),
        ("connect", "organize"),
        ("organize", "define"),
        ("define", "code"),
    }
    if not required_forward.issubset(forward_pairs):
        failures.append("method transitions do not cover the full G1–G8 forward journey")
    feedback_count = len([item for item in transitions if item.get("kind") == "feedback"])
    if feedback_count < int(contract.get("require_iteration_transitions", 2)):
        failures.append("method overview must show at least two explicit feedback/iteration transitions")

    for overlay in scaffold.get("overlays") or []:
        if str(overlay.get("role") or "").lower() in {"watermark", "branding_overlay", "developer_team"}:
            for frame in work_frames:
                if _overlaps(overlay, frame):
                    failures.append(f"overlay {overlay.get('id')} overlaps work frame {frame.get('id')}")

    for font_role in ("journey", "stage_example", "gate_legend", "workshop_guide", "workshop_example", "zone_header"):
        if float(minimum_fonts.get(font_role, 0)) < 18:
            failures.append(f"minimum font size for {font_role} must be at least 18")

    assert_utf8_contract(scaffold, label="Miro scaffold")
    if failures:
        raise ValueError("Miro layout contract failed: " + "; ".join(failures))
    return {
        "status": "PASS",
        "stage_count": len(stages),
        "gate_count": len(gates),
        "frame_count": len(frames),
        "traceability_count": len(traceability),
        "required_placements": sorted(required_placements),
        "stage_visual_count": sum(len((stage_templates.get(str(stage.get('visual_template'))) or {}).get("items") or []) for stage in stages),
        "workshop_example_count": sum(len((example_templates.get(str(frame.get('example_template'))) or {}).get("items") or []) for frame in work_frames if frame.get("id") != "control-center"),
        "transition_count": len(transitions),
        "feedback_transition_count": feedback_count,
    }


def _project_context(config: ProjectConfig) -> dict[str, Any]:
    project = load_yaml(config.root / "project.yaml") or {}
    status_doc = load_yaml(config.root / "artifacts" / "status" / "current-status.yaml") or {}
    next_doc = load_yaml(config.root / "artifacts" / "status" / "next-actions.yaml") or {}
    sync_state = load_yaml(config.root / "miro" / "sync-state.yaml") or {}
    status = status_doc.get("artifact") or status_doc
    next_actions = next_doc.get("artifact") or next_doc
    gates = {str(item.get("gate")): item for item in (status.get("gates") or []) if isinstance(item, dict)}
    current_gate = str(status.get("next_gate") or "G1")
    current_gate_data = gates.get(current_gate) or {}
    owners = project.get("owners") or {}
    return {
        "project": project,
        "status": status,
        "next_actions": next_actions,
        "gates": gates,
        "current_gate": current_gate,
        "current_stage": str(status.get("current_stage") or "align"),
        "current_gate_data": current_gate_data,
        "decision_owner": str(
            status.get("decision_owner")
            or owners.get("business_owner")
            or owners.get("architecture_owner")
            or "NEURČENO"
        ),
        "last_sync_at": str(sync_state.get("last_sync_at") or "NOT_SYNCED"),
    }


def _status_definitions(scaffold: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("id")): item for item in scaffold.get("gate_states") or []}


def _system_entry(mapping: dict[str, Any], item_id: str) -> dict[str, Any]:
    return mapping.setdefault("items", {}).get(item_id) or {}


def _upsert_system_item(
    *,
    mapping: dict[str, Any],
    operations: list[dict[str, Any]],
    client: MiroClient | None,
    board_id: str | None,
    dry_run: bool,
    item_id: str,
    item_type: str,
    payload: dict[str, Any],
    frame_id: str | None = None,
    role: str,
) -> str | None:
    entry = _system_entry(mapping, item_id)
    action = "update_system_item" if entry.get("miro_item_id") else "create_system_item"
    operations.append({"action": action, "item_id": item_id, "item_type": item_type, "role": role, "frame_id": frame_id})
    if dry_run:
        return None
    assert client is not None and board_id is not None
    if entry.get("miro_item_id"):
        remote = client.update_item(board_id, item_type, str(entry["miro_item_id"]), payload)
    else:
        remote = client.create_item(board_id, item_type, payload)
    remote_id = str(remote["id"])
    mapping["items"][item_id] = {
        "miro_item_id": remote_id,
        "item_type": item_type,
        "frame_id": frame_id,
        "managed": True,
        "system_item": True,
        "role": role,
        "position": dict(payload.get("position") or {}),
        "geometry": dict(payload.get("geometry") or {}),
        "style": dict(payload.get("style") or {}),
        "updated_at": utc_now(),
    }
    return remote_id


def _frame_payload(frame: dict[str, Any], palette: dict[str, Any]) -> dict[str, Any]:
    fill = "#FFFFFF" if str(frame.get("role") or "") == "overview" else str(palette.get("frame_background") or "#F8FAFC")
    return {
        "data": {"title": str(frame.get("title_cs") or frame["id"])},
        "style": {"fillColor": fill},
        "position": {"x": float(frame.get("x", 0)), "y": float(frame.get("y", 0)), "origin": "center"},
        "geometry": {"width": float(frame.get("width", 3000)), "height": float(frame.get("height", 2200))},
    }


def _link(label: str, url: str) -> str:
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'


def _frame_guide_content(frame: dict[str, Any], project_id: str) -> str:
    guide = frame.get("guide") or {}
    scaffold_names = ", ".join(str(item).replace("_", " ") for item in (frame.get("scaffold") or [])[:6])
    if len(frame.get("scaffold") or []) > 6:
        scaffold_names += ", …"
    return "".join(
        [
            f"<p><strong>ÚČEL</strong><br>{html.escape(str(frame.get('purpose_cs') or 'Řízená pracovní oblast.'))}</p>",
            f"<p><strong>JAK ZAČÍT</strong><br>{html.escape(str(guide.get('start_cs') or 'Začni fakty, hypotézami a otevřenými otázkami.'))}</p>",
            f"<p><strong>VÝSTUP</strong><br>{html.escape(str(guide.get('outputs_cs') or scaffold_names))}</p>",
            f"<p><strong>ARTEFAKTY</strong><br>{html.escape(scaffold_names)}</p>",
            f"<p>{_link('DDDA kuchařka', str(guide.get('cookbook_url') or ''))} · {_link('Metodika DDDA', str(guide.get('method_url') or ''))}</p>",
            f"<p>{_link('DDD Starter Modelling Process', str(guide.get('starter_reference_url') or ''))}</p>",
            f"<p>DDDA-SCAFFOLD:{project_id}:{frame['id']}:guide</p>",
        ]
    )


def _control_usage_content(frame: dict[str, Any], project_id: str) -> str:
    guide = frame.get("guide") or {}
    return "".join(
        [
            "<p><strong>JAK BOARD POUŽÍVAT</strong></p>",
            "<p>1. Najdi aktuální fázi a gate.</p>",
            "<p>2. Otevři uvedenou pracovní oblast.</p>",
            "<p>3. Doplň evidence podle mini-vzoru a kuchařky.</p>",
            "<p>4. Gate schvaluje pouze oprávněný člověk.</p>",
            f"<p>{_link('Status, gates a další krok', str(guide.get('cookbook_url') or ''))} · {_link('Metodický tok', str(guide.get('method_url') or ''))}</p>",
            f"<p>DDDA-SCAFFOLD:{project_id}:control-center:usage</p>",
        ]
    )


def _control_summary(config: ProjectConfig, context: dict[str, Any]) -> str:
    status = context["status"]
    current = context["current_gate_data"]
    missing = current.get("missing") or []
    actions = context["next_actions"].get("actions") or []
    project = context["project"].get("project") or {}
    project_commit = str(status.get("project_commit") or "UNCOMMITTED")
    lines = [
        f"<p><strong>{html.escape(str(project.get('name') or config.name))}</strong></p>",
        f"<p>Project ID: {html.escape(config.project_id)}</p>",
        f"<p><strong>Aktuální fáze:</strong> {html.escape(context['current_stage'])}</p>",
        f"<p><strong>Aktuální gate:</strong> {html.escape(context['current_gate'])}</p>",
        f"<p><strong>Gate status:</strong> {html.escape(str(current.get('status') or 'not_ready'))}</p>",
        f"<p><strong>Decision question:</strong> {html.escape(str(current.get('question') or ''))}</p>",
        f"<p><strong>Decision owner:</strong> {html.escape(str(current.get('decision_owner') or context['decision_owner']))}</p>",
        f"<p><strong>Reviewer / approver:</strong> {html.escape(str(current.get('reviewer') or 'PENDING'))} / {html.escape(str(current.get('approver') or 'PENDING'))}</p>",
        f"<p><strong>Blocking evidence:</strong> {html.escape(', '.join(map(str, missing)) if missing else 'žádná mechanicky chybějící evidence')}</p>",
        f"<p><strong>Open questions:</strong> {html.escape('; '.join(map(str, current.get('decision_invalid_reasons') or [])) or 'žádné evidované')}</p>",
        f"<p><strong>Next actions:</strong> {html.escape('; '.join(map(str, actions)) if actions else 'nejsou')}</p>",
        f"<p><strong>Commit:</strong> {html.escape(project_commit)}</p>",
        f"<p><strong>Last sync:</strong> {html.escape(context['last_sync_at'])}</p>",
        "<p><strong>Autorita:</strong> Git/YAML + explicitní human gate decision.</p>",
        f"<p>DDDA-SCAFFOLD:{config.project_id}:control-center:summary</p>",
    ]
    return "".join(lines)


def _gate_content(
    gate_id: str,
    stage: dict[str, Any],
    gate_cfg: dict[str, Any],
    gate_state: dict[str, Any],
    status_defs: dict[str, dict[str, Any]],
    current_gate: str,
    frame_titles: dict[str, str],
) -> tuple[str, str]:
    status_id = str(gate_state.get("status") or "not_ready")
    status_def = status_defs.get(status_id) or status_defs.get("not_ready") or {}
    marker = "AKTUÁLNÍ KROK" if gate_id == current_gate else ("DOKONČENO" if status_id == "passed" else "DALŠÍ / ITEROVATELNÝ")
    blockers = len(gate_state.get("missing") or [])
    work_frame_id = str(stage.get("work_frame") or "")
    work_frame_title = frame_titles.get(work_frame_id, work_frame_id)
    content = "".join(
        [
            f"<p><strong>{html.escape(gate_id)} · {html.escape(str(stage.get('title_cs') or stage.get('id')))}</strong></p>",
            f"<p><strong>{html.escape(str(status_def.get('symbol') or '•'))} {html.escape(str(status_def.get('label_cs') or status_id))}</strong></p>",
            f"<p>{html.escape(marker)} · blokery: {blockers}</p>",
            f"<p>{html.escape(str(gate_cfg.get('label_cs') or stage.get('subtitle_cs') or ''))}</p>",
            f"<p><strong>Pracovní oblast:</strong> {html.escape(work_frame_title)}</p>",
            f"<p>{_link('kuchařka', str(stage.get('cookbook_url') or ''))} · {_link('metodika', str(stage.get('method_url') or ''))}</p>",
        ]
    )
    return content, str(status_def.get("fill_color") or "#FFFFFF")


def _shape_payload(
    *,
    content: str,
    x: float,
    y: float,
    width: float,
    height: float,
    fill_color: str,
    font_size: float,
    shape: str = "round_rectangle",
    parent_id: str | None = None,
    border_color: str = "#64748B",
    border_width: float = 2,
    text_align: str = "center",
    text_align_vertical: str = "middle",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "data": {"content": content, "shape": shape},
        "style": {
            "fillColor": fill_color,
            "borderColor": border_color,
            "borderWidth": border_width,
            "fontSize": font_size,
            "fontFamily": "arial",
            "textAlign": text_align,
            "textAlignVertical": text_align_vertical,
        },
        "position": {"x": x, "y": y, "origin": "center"},
        "geometry": {"width": width, "height": height},
    }
    if parent_id:
        payload["parent"] = {"id": parent_id}
    return payload


def _text_payload(
    *,
    content: str,
    x: float,
    y: float,
    width: float,
    font_size: float,
    parent_id: str | None = None,
    text_align: str = "left",
    color: str = "#1F2937",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "data": {"content": content},
        "style": {
            "color": color,
            "fontSize": font_size,
            "fontFamily": "arial",
            "textAlign": text_align,
        },
        "position": {"x": x, "y": y, "origin": "center"},
        "geometry": {"width": width},
    }
    if parent_id:
        payload["parent"] = {"id": parent_id}
    return payload


def _template_layout(frame: dict[str, Any], template: dict[str, Any]) -> tuple[dict[str, tuple[float, float, float, float]], tuple[float, float, float]]:
    frame_width = float(frame.get("width", 5200))
    frame_height = float(frame.get("height", 4200))
    guide_width = min(2100.0, max(1550.0, frame_width * 0.37))
    left = -frame_width / 2 + guide_width + 400
    right = frame_width / 2 - 250
    top = -frame_height / 2 + 650
    bottom = frame_height / 2 - 300
    title_y = top + 100
    item_top = top + 350
    items = template.get("items") or []
    if not items:
        return {}, ((left + right) / 2, title_y, max(900.0, right - left))

    min_left = min(float(item.get("x", 0)) - float(item.get("width", 0)) / 2 for item in items)
    max_right = max(float(item.get("x", 0)) + float(item.get("width", 0)) / 2 for item in items)
    min_top = min(float(item.get("y", 0)) - float(item.get("height", 0)) / 2 for item in items)
    max_bottom = max(float(item.get("y", 0)) + float(item.get("height", 0)) / 2 for item in items)
    source_width = max(max_right - min_left, 1.0)
    source_height = max(max_bottom - min_top, 1.0)
    target_width = max(right - left, 900.0)
    target_height = max(bottom - item_top, 900.0)
    scale = min(target_width / source_width, target_height / source_height, 1.15)
    source_center_x = (min_left + max_right) / 2
    source_center_y = (min_top + max_bottom) / 2
    target_center_x = (left + right) / 2
    target_center_y = (item_top + bottom) / 2

    result: dict[str, tuple[float, float, float, float]] = {}
    for item in items:
        item_id = str(item.get("id") or "item")
        result[item_id] = (
            target_center_x + (float(item.get("x", 0)) - source_center_x) * scale,
            target_center_y + (float(item.get("y", 0)) - source_center_y) * scale,
            float(item.get("width", 900)) * scale,
            float(item.get("height", 600)) * scale,
        )
    return result, (target_center_x, title_y, target_width)


def _render_frame_guide_and_example(
    *,
    scaffold: dict[str, Any],
    frame: dict[str, Any],
    frame_remote_id: str,
    mapping: dict[str, Any],
    operations: list[dict[str, Any]],
    client: MiroClient,
    board_id: str,
    project_id: str,
) -> None:
    frame_id = str(frame["id"])
    minimum_fonts = (scaffold.get("coordinate_system") or {}).get("minimum_font_size") or {}
    frame_width = float(frame.get("width", 5200))
    frame_height = float(frame.get("height", 4200))
    guide_width = min(2100.0, max(1550.0, frame_width * 0.37))
    guide_x = -frame_width / 2 + guide_width / 2 + 180
    guide_y = -frame_height / 2 + 850
    guide_payload = _text_payload(
        content=_frame_guide_content(frame, project_id),
        x=guide_x,
        y=guide_y,
        width=guide_width,
        font_size=float(minimum_fonts.get("workshop_guide", 22)),
        parent_id=frame_remote_id,
        text_align="left",
    )
    _upsert_system_item(
        mapping=mapping,
        operations=operations,
        client=client,
        board_id=board_id,
        dry_run=False,
        item_id=f"{frame_id}:guide",
        item_type="text",
        payload=guide_payload,
        frame_id=frame_id,
        role="workshop_guide",
    )

    template_id = str(frame.get("example_template") or "")
    template = (scaffold.get("example_templates") or {}).get(template_id) or {}
    layout, title = _template_layout(frame, template)
    title_x, title_y, title_width = title
    title_payload = _text_payload(
        content=f"<p><strong>{html.escape(str(template.get('title_cs') or 'Mini-vzor'))}</strong></p>",
        x=title_x,
        y=title_y,
        width=title_width,
        font_size=max(float(minimum_fonts.get("workshop_example", 20)) + 3, 23),
        parent_id=frame_remote_id,
        text_align="center",
        color="#365A8C",
    )
    _upsert_system_item(
        mapping=mapping,
        operations=operations,
        client=client,
        board_id=board_id,
        dry_run=False,
        item_id=f"example:{frame_id}:title",
        item_type="text",
        payload=title_payload,
        frame_id=frame_id,
        role="workshop_example_title",
    )

    for item in template.get("items") or []:
        item_id = str(item.get("id") or "item")
        x, y, width, height = layout[item_id]
        font_size = max(float(minimum_fonts.get("workshop_example", 20)), float(item.get("font_size", 20)))
        content = "".join(f"<p>{html.escape(line)}</p>" for line in str(item.get("label_cs") or item_id).splitlines())
        payload = _shape_payload(
            content=content,
            x=x,
            y=y,
            width=width,
            height=height,
            fill_color=str(item.get("fill_color") or "#FFFFFF"),
            font_size=font_size,
            shape=str(item.get("shape") or "round_rectangle"),
            parent_id=frame_remote_id,
        )
        _upsert_system_item(
            mapping=mapping,
            operations=operations,
            client=client,
            board_id=board_id,
            dry_run=False,
            item_id=f"example:{frame_id}:{item_id}",
            item_type="shape",
            payload=payload,
            frame_id=frame_id,
            role="workshop_example",
        )


def _delete_deprecated_items(
    *,
    mapping: dict[str, Any],
    operations: list[dict[str, Any]],
    client: MiroClient,
    board_id: str,
) -> None:
    deprecated = [
        item_id
        for item_id, entry in (mapping.get("items") or {}).items()
        if item_id.endswith(":instructions") and str((entry or {}).get("role") or "") == "workshop_template"
    ]
    for item_id in deprecated:
        entry = mapping["items"].get(item_id) or {}
        remote_id = str(entry.get("miro_item_id") or "")
        if remote_id:
            client.delete_item(board_id, remote_id)
        operations.append({"action": "delete_deprecated_system_item", "item_id": item_id})
        mapping["items"].pop(item_id, None)


def _load_remote_items(client: MiroClient, board_id: str, expected_ids: set[str]) -> list[dict[str, Any]]:
    latest: list[dict[str, Any]] = []
    for attempt in range(4):
        latest = client.list_items(board_id)
        actual_ids = {str(item.get("id") or "") for item in latest}
        if expected_ids.issubset(actual_ids):
            return latest
        if attempt < 3:
            time.sleep(1.0 + attempt)
    missing = sorted(expected_ids - {str(item.get("id") or "") for item in latest})
    raise ValueError(f"Miro remote layout snapshot is incomplete; missing item IDs: {missing[:10]}")


def validate_remote_layout(
    scaffold: dict[str, Any],
    mapping: dict[str, Any],
    remote_items: list[dict[str, Any]],
) -> dict[str, Any]:
    failures: list[str] = []
    remote_by_id = {str(item.get("id") or ""): item for item in remote_items}
    contract = scaffold.get("visual_contract") or {}
    minimum_fonts = (scaffold.get("coordinate_system") or {}).get("minimum_font_size") or {}
    frames = scaffold.get("frames") or []
    frame_remote: list[dict[str, Any]] = []
    for frame in frames:
        frame_id = str(frame.get("id") or "")
        remote_id = str(((mapping.get("frames") or {}).get(frame_id) or {}).get("miro_item_id") or "")
        remote = remote_by_id.get(remote_id)
        if not remote:
            failures.append(f"remote frame {frame_id} is missing")
            continue
        frame_remote.append({"semantic_id": frame_id, **remote})
        authored_geometry = (float(frame.get("width", 0)), float(frame.get("height", 0)))
        actual_geometry_raw = remote.get("geometry") or {}
        actual_geometry = (actual_geometry_raw.get("width"), actual_geometry_raw.get("height"))
        if None in actual_geometry or tuple(map(float, actual_geometry)) != authored_geometry:
            failures.append(f"remote frame {frame_id} geometry drifted: {actual_geometry} vs {authored_geometry}")
        authored_position = (float(frame.get("x", 0)), float(frame.get("y", 0)))
        actual_position_raw = remote.get("position") or {}
        actual_position = (actual_position_raw.get("x"), actual_position_raw.get("y"))
        if None in actual_position or any(abs(float(actual_position[index]) - authored_position[index]) > 1 for index in (0, 1)):
            failures.append(f"remote frame {frame_id} position drifted: {actual_position} vs {authored_position}")

    overview_id = str(contract.get("overview_frame") or "method-overview")
    work_remote = [frame for frame in frame_remote if frame.get("semantic_id") != overview_id]
    minimum_gap = float(contract.get("minimum_frame_gap", 0))
    for index, left in enumerate(work_remote):
        for right in work_remote[index + 1 :]:
            if _overlaps(left, right, gap=minimum_gap):
                failures.append(f"remote work frames {left.get('semantic_id')} and {right.get('semantic_id')} overlap")

    role_entries: dict[str, list[tuple[str, dict[str, Any], dict[str, Any]]]] = {}
    for item_id, entry in (mapping.get("items") or {}).items():
        if not (entry or {}).get("system_item"):
            continue
        remote_id = str((entry or {}).get("miro_item_id") or "")
        remote = remote_by_id.get(remote_id)
        if not remote:
            failures.append(f"remote system item {item_id} is missing")
            continue
        role_entries.setdefault(str((entry or {}).get("role") or "unknown"), []).append((item_id, entry, remote))

    stage_cards = role_entries.get("journey_gate") or []
    if len(stage_cards) != 8:
        failures.append(f"remote overview must contain 8 journey cards, got {len(stage_cards)}")
    for item_id, _entry, remote in stage_cards:
        font_size = float((remote.get("style") or {}).get("fontSize") or 0)
        if font_size < float(minimum_fonts.get("journey", 28)):
            failures.append(f"{item_id} font size {font_size} is below readable minimum")

    stage_visuals = role_entries.get("stage_visual") or []
    for gate_id in GATE_IDS:
        count = len([item_id for item_id, _, _ in stage_visuals if item_id.startswith(f"stage-visual:{gate_id}:")])
        minimum_stage_visuals = int(contract.get("minimum_stage_visual_items", 4))
        if count < minimum_stage_visuals:
            failures.append(f"{gate_id} has only {count} situation-card visual items")

    legends = role_entries.get("gate_state_legend") or []
    if len(legends) != 5:
        failures.append(f"remote control frame must contain 5 gate-state legend cards, got {len(legends)}")
    for item_id, _entry, remote in legends:
        font_size = float((remote.get("style") or {}).get("fontSize") or 0)
        if font_size < float(minimum_fonts.get("gate_legend", 24)):
            failures.append(f"{item_id} font size {font_size} is below readable minimum")

    guides = role_entries.get("workshop_guide") or []
    for item_id, entry, remote in guides:
        position = entry.get("position") or {}
        if float(position.get("x", 0)) >= 0 or float(position.get("y", 0)) >= 0:
            failures.append(f"{item_id} is not anchored in the top-left quadrant")
        font_size = float((remote.get("style") or {}).get("fontSize") or 0)
        if font_size < float(minimum_fonts.get("workshop_guide", 22)):
            failures.append(f"{item_id} font size {font_size} is below readable minimum")

    example_entries = role_entries.get("workshop_example") or []
    for frame in frames:
        frame_id = str(frame.get("id") or "")
        if frame_id in {overview_id, "control-center"}:
            continue
        count = len([item_id for item_id, _, _ in example_entries if item_id.startswith(f"example:{frame_id}:")])
        if count < int(contract.get("minimum_example_items", 3)):
            failures.append(f"remote frame {frame_id} has only {count} example items")

    zones = role_entries.get("zone_header") or []
    if len(zones) != 4:
        failures.append(f"remote overview must contain 4 zone headers, got {len(zones)}")
    for item_id, _entry, remote in zones:
        font_size = float((remote.get("style") or {}).get("fontSize") or 0)
        if font_size < float(minimum_fonts.get("zone_header", 28)):
            failures.append(f"{item_id} font size {font_size} is below readable minimum")

    transitions = role_entries.get("method_transition") or []
    feedback = [item_id for item_id, _, _ in transitions if "feedback" in item_id]
    if len(transitions) < 9 or len(feedback) < 2:
        failures.append("remote overview does not expose full forward flow plus feedback loops")

    if failures:
        raise ValueError("Miro remote layout contract failed: " + "; ".join(failures))
    return {
        "status": "PASS",
        "remote_item_count": len(remote_items),
        "remote_frame_count": len(frame_remote),
        "journey_card_count": len(stage_cards),
        "stage_visual_count": len(stage_visuals),
        "gate_legend_count": len(legends),
        "workshop_guide_count": len(guides),
        "workshop_example_count": len(example_entries),
        "zone_header_count": len(zones),
        "transition_count": len(transitions),
    }


def render_board(config: ProjectConfig, client: MiroClient | None, *, create_board: bool, dry_run: bool) -> dict[str, Any]:
    scaffold = load_yaml(config.scaffold_path)
    if not isinstance(scaffold, dict):
        raise ValueError(f"Invalid scaffold: {config.scaffold_path}")
    contract = validate_layout_contract(scaffold)
    context = _project_context(config)
    assert_utf8_contract(context, label="project steering context")

    board_id = config.board_id
    operations: list[dict[str, Any]] = []
    if not board_id:
        if not create_board:
            raise ValueError("No Miro board ID is configured. Set miro.board_id / board_id_env, or use --create-board.")
        operations.append({"action": "create_board", "name": config.name})
        if not dry_run:
            assert client is not None
            board = client.create_board(
                f"DDDA – {config.name}",
                f"DDDA project {config.project_id}; managed through YAML and Git. Miro is a projection, not gate authority.",
                team_id=config.team_id,
                project_id=config.miro_project_id,
            )
            board_id = str(board["id"])

    mapping = load_map(config.root, config.project_id, board_id)
    palette = scaffold.get("palette") or {}
    frame_remote_ids: dict[str, str] = {}
    frames = scaffold.get("frames") or []
    frame_titles = {str(frame.get("id")): str(frame.get("title_cs") or frame.get("id")) for frame in frames}

    for frame in frames:
        frame_id = str(frame["id"])
        entry = mapping["frames"].get(frame_id) or {}
        payload = _frame_payload(frame, palette)
        operations.append(
            {
                "action": "update_frame" if entry.get("miro_item_id") else "create_frame",
                "frame_id": frame_id,
                "title": payload["data"]["title"],
            }
        )
        if dry_run:
            if frame_id not in {"control-center", str((scaffold.get("visual_contract") or {}).get("overview_frame") or "method-overview")}:
                operations.append({"action": "create_system_item", "item_id": f"{frame_id}:guide", "item_type": "text", "role": "workshop_guide"})
                template = (scaffold.get("example_templates") or {}).get(str(frame.get("example_template") or "")) or {}
                for item in template.get("items") or []:
                    operations.append({"action": "create_system_item", "item_id": f"example:{frame_id}:{item.get('id')}", "item_type": "shape", "role": "workshop_example"})
            continue
        assert client is not None and board_id is not None
        remote = (
            client.update_item(board_id, "frame", str(entry["miro_item_id"]), payload)
            if entry.get("miro_item_id")
            else client.create_item(board_id, "frame", payload)
        )
        remote_id = str(remote["id"])
        frame_remote_ids[frame_id] = remote_id
        mapping["frames"][frame_id] = {
            "miro_item_id": remote_id,
            "role": frame.get("role") or "work",
            "stage": frame.get("stage"),
            "title": payload["data"]["title"],
            "position": payload["position"],
            "geometry": payload["geometry"],
            "updated_at": utc_now(),
        }

    if dry_run:
        for stage in scaffold.get("method_flow", {}).get("stages") or []:
            gate_id = str(stage.get("gate_after") or "")
            operations.append({"action": "create_system_item", "item_id": f"journey:{gate_id}", "item_type": "shape", "role": "journey_gate"})
            template = (scaffold.get("stage_visual_templates") or {}).get(str(stage.get("visual_template") or "")) or {}
            for item in template.get("items") or []:
                operations.append({"action": "create_system_item", "item_id": f"stage-visual:{gate_id}:{item.get('id')}", "item_type": "shape", "role": "stage_visual"})
        for state in scaffold.get("gate_states") or []:
            operations.append({"action": "create_system_item", "item_id": f"legend:{state.get('id')}", "item_type": "shape", "role": "gate_state_legend"})
        for zone in scaffold.get("zones") or []:
            operations.append({"action": "create_system_item", "item_id": str(zone.get("id")), "item_type": "shape", "role": "zone_header"})
        for transition in scaffold.get("method_transitions") or []:
            operations.append({"action": "create_system_item", "item_id": f"transition:{transition.get('kind')}:{transition.get('id')}", "item_type": "text", "role": "method_transition"})
        return {
            "project_id": config.project_id,
            "board_id": board_id,
            "dry_run": True,
            "operations": operations,
            "operation_count": len(operations),
            "technical_sync_status": "NOT_RUN",
            "layout_contract_status": contract["status"],
            "remote_layout_status": "NOT_RUN",
            "utf8_status": "PASS",
            "human_visual_acceptance_status": "PENDING",
            "overall_status": "PENDING_HUMAN_REVIEW",
            "traceability_count": contract["traceability_count"],
            "review_team_selection_status": "EXPLICIT_TEAM" if config.team_id else "DEFAULT_TOKEN_TEAM",
        }

    assert client is not None and board_id is not None
    _delete_deprecated_items(mapping=mapping, operations=operations, client=client, board_id=board_id)

    overview_id = str((scaffold.get("visual_contract") or {}).get("overview_frame") or "method-overview")
    control_frame = frame_remote_ids.get("control-center") or str((mapping["frames"].get("control-center") or {}).get("miro_item_id") or "")
    if not control_frame:
        raise ValueError("Navigation frame 00 – Navigace, legenda a stav artefaktů was not rendered")

    for frame in frames:
        frame_id = str(frame["id"])
        if frame_id in {overview_id, "control-center"}:
            continue
        frame_remote_id = frame_remote_ids.get(frame_id) or str((mapping["frames"].get(frame_id) or {}).get("miro_item_id") or "")
        if not frame_remote_id:
            raise ValueError(f"Work frame {frame_id} was not rendered")
        _render_frame_guide_and_example(
            scaffold=scaffold,
            frame=frame,
            frame_remote_id=frame_remote_id,
            mapping=mapping,
            operations=operations,
            client=client,
            board_id=board_id,
            project_id=config.project_id,
        )

    summary_payload = _text_payload(
        content=_control_summary(config, context),
        x=-1550,
        y=-1350,
        width=2600,
        font_size=22,
        parent_id=control_frame,
        text_align="left",
    )
    _upsert_system_item(
        mapping=mapping,
        operations=operations,
        client=client,
        board_id=board_id,
        dry_run=False,
        item_id="control-center:summary",
        item_type="text",
        payload=summary_payload,
        frame_id="control-center",
        role="control_center_summary",
    )

    control_frame_cfg = next(frame for frame in frames if str(frame.get("id")) == "control-center")
    usage_payload = _text_payload(
        content=_control_usage_content(control_frame_cfg, config.project_id),
        x=1600,
        y=-1350,
        width=2500,
        font_size=22,
        parent_id=control_frame,
        text_align="left",
        color="#365A8C",
    )
    _upsert_system_item(
        mapping=mapping,
        operations=operations,
        client=client,
        board_id=board_id,
        dry_run=False,
        item_id="control-center:usage",
        item_type="text",
        payload=usage_payload,
        frame_id="control-center",
        role="control_center_usage",
    )

    status_defs = _status_definitions(scaffold)
    gate_configs = {str(item.get("id")): item for item in scaffold.get("gates") or []}
    stage_card = (scaffold.get("coordinate_system") or {}).get("stage_card") or {}
    stage_width = float(stage_card.get("width", 3600))
    stage_height = float(stage_card.get("height", 2200))
    minimum_fonts = (scaffold.get("coordinate_system") or {}).get("minimum_font_size") or {}

    for stage in scaffold.get("method_flow", {}).get("stages") or []:
        gate_id = str(stage.get("gate_after") or "")
        gate_state = context["gates"].get(gate_id) or {"status": "not_ready", "missing": []}
        content, fill_color = _gate_content(
            gate_id,
            stage,
            gate_configs.get(gate_id) or {},
            gate_state,
            status_defs,
            context["current_gate"],
            frame_titles,
        )
        payload = _shape_payload(
            content=content,
            x=float(stage.get("x", 0)),
            y=float(stage.get("y", -4400)),
            width=stage_width,
            height=stage_height,
            fill_color=fill_color,
            font_size=float(minimum_fonts.get("journey", 28)),
            shape="round_rectangle",
            border_color="#365A8C",
            border_width=4 if gate_id == context["current_gate"] else 2,
            text_align="center",
            text_align_vertical="top",
        )
        _upsert_system_item(
            mapping=mapping,
            operations=operations,
            client=client,
            board_id=board_id,
            dry_run=False,
            item_id=f"journey:{gate_id}",
            item_type="shape",
            payload=payload,
            role="journey_gate",
        )

        template = (scaffold.get("stage_visual_templates") or {}).get(str(stage.get("visual_template") or "")) or {}
        for item in template.get("items") or []:
            item_id = str(item.get("id") or "item")
            content = "".join(f"<p><strong>{html.escape(line)}</strong></p>" for line in str(item.get("label_cs") or item_id).splitlines())
            visual_payload = _shape_payload(
                content=content,
                x=float(stage.get("x", 0)) + float(item.get("x", 0)),
                y=float(stage.get("y", 0)) + float(item.get("y", 500)),
                width=float(item.get("width", 760)),
                height=float(item.get("height", 420)),
                fill_color=str(item.get("fill_color") or "#FFFFFF"),
                font_size=max(float(minimum_fonts.get("stage_example", 20)), float(item.get("font_size", 20))),
                shape=str(item.get("shape") or "round_rectangle"),
                border_color="#64748B",
                border_width=1,
            )
            _upsert_system_item(
                mapping=mapping,
                operations=operations,
                client=client,
                board_id=board_id,
                dry_run=False,
                item_id=f"stage-visual:{gate_id}:{item_id}",
                item_type="shape",
                payload=visual_payload,
                role="stage_visual",
            )

    legend_positions = [-2200, -1100, 0, 1100, 2200]
    for index, state in enumerate(scaffold.get("gate_states") or []):
        state_id = str(state.get("id"))
        payload = _shape_payload(
            content=(
                f"<p><strong>{html.escape(str(state.get('symbol') or '•'))} "
                f"{html.escape(str(state.get('label_cs') or state_id))}</strong></p>"
                f"<p>{html.escape(str(state.get('meaning_cs') or ''))}</p>"
            ),
            x=legend_positions[index],
            y=1450,
            width=1000,
            height=650,
            fill_color=str(state.get("fill_color") or "#FFFFFF"),
            font_size=float(minimum_fonts.get("gate_legend", 24)),
            parent_id=control_frame,
            border_color="#64748B",
            border_width=2,
        )
        _upsert_system_item(
            mapping=mapping,
            operations=operations,
            client=client,
            board_id=board_id,
            dry_run=False,
            item_id=f"legend:{state_id}",
            item_type="shape",
            payload=payload,
            frame_id="control-center",
            role="gate_state_legend",
        )

    for zone in scaffold.get("zones") or []:
        payload = _shape_payload(
            content=f"<p><strong>{html.escape(str(zone.get('title_cs') or zone.get('id')))}</strong></p>",
            x=float(zone.get("x", 0)),
            y=float(zone.get("y", -5650)),
            width=float(zone.get("width", 4200)),
            height=float(zone.get("height", 650)),
            fill_color="#E0F2FE",
            font_size=float(minimum_fonts.get("zone_header", 28)),
            shape="round_rectangle",
            border_color="#2F7E95",
            border_width=2,
        )
        _upsert_system_item(
            mapping=mapping,
            operations=operations,
            client=client,
            board_id=board_id,
            dry_run=False,
            item_id=str(zone.get("id")),
            item_type="shape",
            payload=payload,
            role="zone_header",
        )

    for transition in scaffold.get("method_transitions") or []:
        transition_id = str(transition.get("id") or "transition")
        kind = str(transition.get("kind") or "forward")
        color = "#B45309" if kind == "feedback" else "#365A8C"
        payload = _text_payload(
            content=(
                f"<p><strong>{html.escape(str(transition.get('symbol') or '→'))}</strong> "
                f"{html.escape(str(transition.get('label_cs') or ''))}</p>"
            ),
            x=float(transition.get("x", 0)),
            y=float(transition.get("y", 0)),
            width=2800 if kind == "feedback" else 2200,
            font_size=26,
            text_align="center",
            color=color,
        )
        _upsert_system_item(
            mapping=mapping,
            operations=operations,
            client=client,
            board_id=board_id,
            dry_run=False,
            item_id=f"transition:{kind}:{transition_id}",
            item_type="text",
            payload=payload,
            role="method_transition",
        )

    expected_remote_ids = {
        str(frame.get("miro_item_id"))
        for frame in (mapping.get("frames") or {}).values()
        if (frame or {}).get("miro_item_id")
    }
    expected_remote_ids.update(
        str(entry.get("miro_item_id"))
        for entry in (mapping.get("items") or {}).values()
        if (entry or {}).get("system_item") and (entry or {}).get("miro_item_id")
    )
    remote_items = _load_remote_items(client, board_id, expected_remote_ids)
    remote_layout = validate_remote_layout(scaffold, mapping, remote_items)

    mapping["board_id"] = board_id
    mapping["scaffold_id"] = scaffold.get("id")
    mapping["scaffold_schema_version"] = scaffold.get("schema_version")
    mapping["rendered_at"] = utc_now()
    mapping["layout_contract_status"] = "PASS"
    mapping["remote_layout_status"] = remote_layout["status"]
    mapping["remote_layout_evidence"] = remote_layout
    mapping["utf8_status"] = "PASS"
    mapping["human_visual_acceptance_status"] = "PENDING"
    mapping["overall_status"] = "PENDING_HUMAN_REVIEW"
    mapping["review_team_selection_status"] = "EXPLICIT_TEAM" if config.team_id else "DEFAULT_TOKEN_TEAM"
    mapping["developer_team_watermark_status"] = "EXTERNAL_ENVIRONMENT_NOT_RENDERED_BY_DDDA"
    mapping["traceability"] = scaffold.get("traceability") or []
    assert_utf8_contract(mapping, label="Miro mapping")
    save_map(config.root, mapping)

    return {
        "project_id": config.project_id,
        "board_id": board_id,
        "dry_run": False,
        "operations": operations,
        "operation_count": len(operations),
        "technical_sync_status": "NOT_RUN",
        "layout_contract_status": "PASS",
        "remote_layout_status": remote_layout["status"],
        "remote_layout_evidence": remote_layout,
        "utf8_status": "PASS",
        "human_visual_acceptance_status": "PENDING",
        "overall_status": "PENDING_HUMAN_REVIEW",
        "traceability_count": contract["traceability_count"],
        "current_gate": context["current_gate"],
        "review_team_selection_status": "EXPLICIT_TEAM" if config.team_id else "DEFAULT_TOKEN_TEAM",
        "developer_team_watermark_status": "EXTERNAL_ENVIRONMENT_NOT_RENDERED_BY_DDDA",
    }
