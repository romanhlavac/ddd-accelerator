from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from .client import MiroClient
from .config import ProjectConfig
from .state import load_map, save_map, utc_now
from .yamlio import load_yaml

MOJIBAKE_MARKERS = ("â€“", "â€”", "Ă", "Ĺ", "Ä", "�")
GATE_IDS = [f"G{index}" for index in range(1, 9)]
GATE_STATUS_IDS = ["not_ready", "ready_for_review", "conditional", "rejected", "passed"]


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


def validate_layout_contract(scaffold: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    stages = scaffold.get("method_flow", {}).get("stages") or []
    gates = scaffold.get("gates") or []
    frames = scaffold.get("frames") or []
    states = scaffold.get("gate_states") or []
    traceability = scaffold.get("traceability") or []
    placements = scaffold.get("managed_placements") or {}

    stage_ids = [str(item.get("id") or "") for item in stages]
    gate_ids = [str(item.get("id") or "") for item in gates]
    frame_ids = {str(item.get("id") or "") for item in frames}
    state_ids = [str(item.get("id") or "") for item in states]
    traced_gates = [str(item.get("gate") or "") for item in traceability]

    expected_stages = ["align", "discover", "decompose", "strategize", "connect", "organize", "define", "code"]
    if stage_ids != expected_stages:
        failures.append(f"method_flow stages must be {expected_stages}, got {stage_ids}")
    if gate_ids != GATE_IDS:
        failures.append(f"gates must be {GATE_IDS}, got {gate_ids}")
    if state_ids != GATE_STATUS_IDS:
        failures.append(f"gate states must be {GATE_STATUS_IDS}, got {state_ids}")
    if "control-center" not in frame_ids:
        failures.append("control-center frame is missing")
    if sorted(traced_gates) != sorted(GATE_IDS):
        failures.append("traceability must cover G1–G8 exactly once")

    for stage in stages:
        work_frame = str(stage.get("work_frame") or "")
        if not work_frame or work_frame not in frame_ids:
            failures.append(f"stage {stage.get('id')} does not reference an existing work frame")

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

    for frame in frames:
        if not frame.get("purpose_cs"):
            failures.append(f"frame {frame.get('id')} has no purpose")
        if not frame.get("scaffold"):
            failures.append(f"frame {frame.get('id')} has no workshop structure")

    def overlaps(left: dict[str, Any], right: dict[str, Any]) -> bool:
        lx, ly = float(left.get("x", 0)), float(left.get("y", 0))
        lw, lh = float(left.get("width", 0)), float(left.get("height", 0))
        rx, ry = float(right.get("x", 0)), float(right.get("y", 0))
        rw, rh = float(right.get("width", 0)), float(right.get("height", 0))
        return abs(lx - rx) * 2 < (lw + rw) and abs(ly - ry) * 2 < (lh + rh)

    for overlay in scaffold.get("overlays") or []:
        if str(overlay.get("role") or "").lower() in {"watermark", "branding_overlay", "developer_team"}:
            for frame in frames:
                if overlaps(overlay, frame):
                    failures.append(f"overlay {overlay.get('id')} overlaps work frame {frame.get('id')}")

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
        "updated_at": utc_now(),
    }
    return remote_id


def _frame_payload(frame: dict[str, Any], palette: dict[str, Any]) -> dict[str, Any]:
    return {
        "data": {"title": str(frame.get("title_cs") or frame["id"])},
        "style": {"fillColor": str(palette.get("frame_background") or "#F8FAFC")},
        "position": {"x": float(frame.get("x", 0)), "y": float(frame.get("y", 0)), "origin": "center"},
        "geometry": {"width": float(frame.get("width", 3000)), "height": float(frame.get("height", 2200))},
    }


def _section_content(frame: dict[str, Any], scaffold: dict[str, Any], project_id: str) -> str:
    catalog = scaffold.get("section_catalog") or {}
    purpose = html.escape(str(frame.get("purpose_cs") or "Řízená pracovní oblast."))
    parts = [
        f"<p><strong>Účel</strong></p><p>{purpose}</p>",
        "<p><strong>Pracovní struktura</strong></p>",
    ]
    for number, section_id in enumerate(frame.get("scaffold") or [], start=1):
        section = catalog.get(section_id) or {}
        label = html.escape(str(section.get("label_cs") or str(section_id).replace("_", " ")))
        guidance = html.escape(str(section.get("guidance_cs") or "Zachyť fakta, hypotézy, ownera a otevřené otázky."))
        parts.append(f"<p><strong>{number}. {label}</strong><br>{guidance}</p>")
    parts.append("<p><em>Fakta, hypotézy a rozhodnutí udržuj explicitně oddělené.</em></p>")
    parts.append(f"<p>DDDA-SCAFFOLD:{project_id}:{frame['id']}:instructions</p>")
    return "".join(parts)


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
        f"<p><strong>Reviewer:</strong> {html.escape(str(current.get('reviewer') or 'PENDING'))}</p>",
        f"<p><strong>Approver:</strong> {html.escape(str(current.get('approver') or 'PENDING'))}</p>",
        f"<p><strong>Blocking evidence:</strong> {html.escape(', '.join(map(str, missing)) if missing else 'žádná mechanicky chybějící evidence')}</p>",
        f"<p><strong>Open questions:</strong> {html.escape('; '.join(map(str, current.get('decision_invalid_reasons') or [])) or 'žádné evidované')}</p>",
        f"<p><strong>Next actions:</strong> {html.escape('; '.join(map(str, actions)) if actions else 'nejsou')}</p>",
        f"<p><strong>Project/source commit:</strong> {html.escape(project_commit)}</p>",
        f"<p><strong>Last sync:</strong> {html.escape(context['last_sync_at'])}</p>",
        f"<p><strong>Last render:</strong> {html.escape(utc_now())}</p>",
        "<p><strong>Autorita:</strong> Git/YAML + explicitní human gate decision. Miro samo gate neschvaluje.</p>",
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
) -> tuple[str, str]:
    status_id = str(gate_state.get("status") or "not_ready")
    status_def = status_defs.get(status_id) or status_defs.get("not_ready") or {}
    marker = "AKTUÁLNÍ" if gate_id == current_gate else ("DOKONČENO" if status_id == "passed" else "NÁSLEDUJÍCÍ")
    blockers = len(gate_state.get("missing") or [])
    content = "".join([
        f"<p><strong>{html.escape(gate_id)} {html.escape(str(stage.get('title_cs') or stage.get('id')))}</strong></p>",
        f"<p><strong>{html.escape(str(status_def.get('symbol') or '•'))} {html.escape(str(status_def.get('label_cs') or status_id))}</strong></p>",
        f"<p>{html.escape(marker)} · otevřené blokery: {blockers}</p>",
        f"<p>{html.escape(str(gate_cfg.get('label_cs') or stage.get('subtitle_cs') or ''))}</p>",
        f"<p>Pracovní frame: {html.escape(str(stage.get('work_frame') or ''))}</p>",
    ])
    return content, str(status_def.get("fill_color") or "#FFFFFF")


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

    for frame in scaffold.get("frames") or []:
        frame_id = str(frame["id"])
        entry = mapping["frames"].get(frame_id) or {}
        payload = _frame_payload(frame, palette)
        operations.append({"action": "update_frame" if entry.get("miro_item_id") else "create_frame", "frame_id": frame_id, "title": payload["data"]["title"]})
        if dry_run:
            continue
        assert client is not None and board_id is not None
        remote = client.update_item(board_id, "frame", str(entry["miro_item_id"]), payload) if entry.get("miro_item_id") else client.create_item(board_id, "frame", payload)
        remote_id = str(remote["id"])
        frame_remote_ids[frame_id] = remote_id
        mapping["frames"][frame_id] = {
            "miro_item_id": remote_id,
            "stage": frame.get("stage"),
            "title": payload["data"]["title"],
            "position": payload["position"],
            "geometry": payload["geometry"],
            "updated_at": utc_now(),
        }

        text_id = f"{frame_id}:instructions"
        width = max(900, float(frame.get("width", 3000)) - 350)
        text_payload = {
            "data": {"content": _section_content(frame, scaffold, config.project_id)},
            "position": {"x": 0, "y": -250 if frame_id == "control-center" else 0, "origin": "center"},
            "geometry": {"width": width},
            "parent": {"id": remote_id},
        }
        _upsert_system_item(
            mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False,
            item_id=text_id, item_type="text", payload=text_payload, frame_id=frame_id, role="workshop_template",
        )

    # Dry-run still advertises all deterministic operations without writing.
    if dry_run:
        for stage in scaffold.get("method_flow", {}).get("stages") or []:
            operations.append({"action": "create_system_item", "item_id": f"journey:{stage.get('gate_after')}", "item_type": "shape", "role": "journey_gate"})
        for state in scaffold.get("gate_states") or []:
            operations.append({"action": "create_system_item", "item_id": f"legend:{state.get('id')}", "item_type": "shape", "role": "gate_state_legend"})
        for zone in scaffold.get("zones") or []:
            operations.append({"action": "create_system_item", "item_id": str(zone.get("id")), "item_type": "text", "role": "zone_header"})
        return {
            "project_id": config.project_id,
            "board_id": board_id,
            "dry_run": True,
            "operations": operations,
            "operation_count": len(operations),
            "technical_sync_status": "NOT_RUN",
            "layout_contract_status": contract["status"],
            "utf8_status": "PASS",
            "human_visual_acceptance_status": "PENDING",
            "overall_status": "PENDING_HUMAN_REVIEW",
            "traceability_count": contract["traceability_count"],
        }

    assert client is not None and board_id is not None
    control_frame = frame_remote_ids.get("control-center") or str((mapping["frames"].get("control-center") or {}).get("miro_item_id") or "")
    if not control_frame:
        raise ValueError("Control Center frame was not rendered")

    summary_payload = {
        "data": {"content": _control_summary(config, context)},
        "position": {"x": 0, "y": -1050, "origin": "center"},
        "geometry": {"width": 4500},
        "parent": {"id": control_frame},
    }
    _upsert_system_item(
        mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False,
        item_id="control-center:summary", item_type="text", payload=summary_payload,
        frame_id="control-center", role="control_center_summary",
    )

    status_defs = _status_definitions(scaffold)
    gate_configs = {str(item.get("id")): item for item in scaffold.get("gates") or []}
    for stage in scaffold.get("method_flow", {}).get("stages") or []:
        gate_id = str(stage.get("gate_after") or "")
        gate_state = context["gates"].get(gate_id) or {"status": "not_ready", "missing": []}
        content, fill_color = _gate_content(
            gate_id, stage, gate_configs.get(gate_id) or {}, gate_state,
            status_defs, context["current_gate"],
        )
        payload = {
            "data": {"content": content, "shape": "round_rectangle"},
            "style": {"fillColor": fill_color, "borderColor": "#365A8C", "borderWidth": 2},
            "position": {"x": float(stage.get("x", 0)), "y": float(stage.get("y", -4400)), "origin": "center"},
            "geometry": {"width": 3000, "height": 1150},
        }
        _upsert_system_item(
            mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False,
            item_id=f"journey:{gate_id}", item_type="shape", payload=payload,
            role="journey_gate",
        )

    for index, state in enumerate(scaffold.get("gate_states") or []):
        state_id = str(state.get("id"))
        payload = {
            "data": {"content": (
                f"<p><strong>{html.escape(str(state.get('symbol') or '•'))} "
                f"{html.escape(str(state.get('label_cs') or state_id))}</strong></p>"
                f"<p>{html.escape(str(state.get('meaning_cs') or ''))}</p>"
            ), "shape": "round_rectangle"},
            "style": {"fillColor": str(state.get("fill_color") or "#FFFFFF"), "borderColor": "#64748B"},
            "position": {"x": -1900 + index * 950, "y": 1200, "origin": "center"},
            "geometry": {"width": 850, "height": 550},
            "parent": {"id": control_frame},
        }
        _upsert_system_item(
            mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False,
            item_id=f"legend:{state_id}", item_type="shape", payload=payload,
            frame_id="control-center", role="gate_state_legend",
        )

    for zone in scaffold.get("zones") or []:
        payload = {
            "data": {"content": f"<p><strong>{html.escape(str(zone.get('title_cs') or zone.get('id')))}</strong></p>"},
            "position": {"x": float(zone.get("x", 0)), "y": float(zone.get("y", -5650)), "origin": "center"},
            "geometry": {"width": float(zone.get("width", 3000))},
        }
        _upsert_system_item(
            mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False,
            item_id=str(zone.get("id")), item_type="text", payload=payload, role="zone_header",
        )

    mapping["board_id"] = board_id
    mapping["scaffold_id"] = scaffold.get("id")
    mapping["scaffold_schema_version"] = scaffold.get("schema_version")
    mapping["rendered_at"] = utc_now()
    mapping["layout_contract_status"] = "PASS"
    mapping["utf8_status"] = "PASS"
    mapping["human_visual_acceptance_status"] = "PENDING"
    mapping["overall_status"] = "PENDING_HUMAN_REVIEW"
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
        "utf8_status": "PASS",
        "human_visual_acceptance_status": "PENDING",
        "overall_status": "PENDING_HUMAN_REVIEW",
        "traceability_count": contract["traceability_count"],
        "current_gate": context["current_gate"],
    }
