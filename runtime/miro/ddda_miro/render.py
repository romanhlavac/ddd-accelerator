from __future__ import annotations

import html
import time
from pathlib import Path
from typing import Any

from .client import MiroClient
from .config import ProjectConfig
from .model import load_artifacts
from .state import load_map, save_map, utc_now
from .yamlio import load_yaml

MOJIBAKE_MARKERS = ("â€“", "â€”", "Ă", "Ĺ", "Ä", "�")
GATE_IDS = [f"G{index}" for index in range(1, 9)]
GATE_STATUS_IDS = ["not_ready", "ready_for_review", "conditional", "rejected", "passed"]
EXPECTED_STAGES = ["align", "discover", "decompose", "strategize", "connect", "organize", "define", "code"]
CANONICAL_SHELL_FRAME_IDS = [
    "discover-big-picture-es",
    "discover-evidence",
    "discover-process-modeling",
    "decompose-domain",
    "decompose-lifecycles",
    "strategize-classification",
    "connect-context-map",
    "organize-teams",
    "define-bounded-context",
    "define-design-level-es",
    "define-lifecycle",
    "define-quality",
    "code-tactical-model",
    "code-state-machine",
    "code-views-and-decisions",
]


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
    zone_transitions = scaffold.get("zone_transitions") or []
    transitions = scaffold.get("method_transitions") or []
    stage_templates = scaffold.get("stage_visual_templates") or {}
    example_templates = scaffold.get("example_templates") or {}
    contract = scaffold.get("visual_contract") or {}
    coordinate = scaffold.get("coordinate_system") or {}
    minimum_fonts = coordinate.get("minimum_font_size") or {}
    stage_columns = scaffold.get("stage_columns") or []

    stage_ids = [str(item.get("id") or "") for item in stages]
    gate_ids = [str(item.get("id") or "") for item in gates]
    frame_ids = {str(item.get("id") or "") for item in frames}
    state_ids = [str(item.get("id") or "") for item in states]
    traced_gates = [str(item.get("gate") or "") for item in traceability]
    if stage_ids != EXPECTED_STAGES:
        failures.append(f"method_flow stages must be {EXPECTED_STAGES}, got {stage_ids}")
    if contract.get("require_stage_columns"):
        if len({float(stage.get("y", 0)) for stage in stages}) != 1:
            failures.append("stage headers must share one horizontal axis")
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

    resources = scaffold.get("overview_resources") or []
    if len(resources) < int(contract.get("require_overview_resources", 4)):
        failures.append("overview must expose DDD Starter, DDDA methodology, cookbooks and knowledge resources")
    for resource in resources:
        if not str(resource.get("url") or "").startswith("https://"):
            failures.append(f"overview resource {resource.get('id')} has no usable URL")
    board_guide = scaffold.get("board_guide") or {}
    if len(board_guide.get("steps_cs") or []) < 6:
        failures.append("control-center must contain a compact first-user board guide")
    for field in ("details_url", "cookbook_url", "method_url", "starter_reference_url", "knowledge_index_url"):
        if not str(board_guide.get(field) or "").startswith("https://"):
            failures.append(f"board guide is missing {field}")
    registry_cfg = scaffold.get("artifact_status_tables") or {}
    if not registry_cfg:
        failures.append("control-center artifact registry contract is missing")
    if contract.get("require_state_lifecycle_provenance_separation"):
        for field in (
            "project_gate_state_title_cs",
            "lifecycle_title_cs",
            "lifecycle_legend_cs",
            "provenance_title_cs",
            "provenance_legend_cs",
            "provenance_values",
            "registry_columns",
        ):
            if not registry_cfg.get(field):
                failures.append(f"control-center artifact registry is missing {field}")
        lifecycle_ids = [str(item.get("id") or "") for item in registry_cfg.get("statuses") or []]
        if lifecycle_ids != ["scaffold", "working", "candidate", "validated", "accepted", "superseded"]:
            failures.append("artifact lifecycle must be SCAFFOLD → WORKING → CANDIDATE → VALIDATED → ACCEPTED → SUPERSEDED")
        provenance_ids = [str(item.get("id") or "") for item in registry_cfg.get("provenance_values") or []]
        if provenance_ids != ["generated", "workshop", "imported", "manual"]:
            failures.append("artifact provenance must be GENERATED, WORKSHOP, IMPORTED, MANUAL")
        registry_columns = [str(item.get("id") or "") for item in registry_cfg.get("registry_columns") or []]
        if registry_columns != [
            "artifact", "type", "stage", "lifecycle", "provenance",
            "owner", "revision", "last_sync", "detail",
        ]:
            failures.append("artifact registry columns do not match the Control Center contract")

    frame_by_id = {str(item.get("id") or ""): item for item in frames}
    overview = frame_by_id.get(overview_id) or {}
    stage_card = coordinate.get("stage_card") or {}
    stage_width = float(stage_card.get("width", 0))
    stage_height = float(stage_card.get("height", 0))
    if stage_width < float(contract.get("minimum_stage_card_width", 0)) or stage_height < float(contract.get("minimum_stage_card_height", 0)):
        failures.append("stage card size is below the visual contract")

    stage_boxes: list[dict[str, Any]] = []
    for stage in stages:
        stage_id = str(stage.get("id") or "")
        work_frame = str(stage.get("work_frame") or "")
        if not work_frame or work_frame not in frame_ids:
            failures.append(f"stage {stage_id} does not reference an existing work frame")
        template = stage_templates.get(str(stage.get("visual_template") or "")) or {}
        if len(template.get("items") or []) < int(contract.get("minimum_stage_visual_items", 4)):
            failures.append(f"stage {stage_id} has too few methodological visual items")
        for link_name in ("cookbook_url", "method_url", "starter_reference_url"):
            if not str(stage.get(link_name) or "").startswith("https://"):
                failures.append(f"stage {stage_id} has no usable {link_name}")
        box = {"id": stage_id, "x": float(stage.get("x", 0)), "y": float(stage.get("y", 0)), "width": stage_width, "height": stage_height}
        stage_boxes.append(box)
        if overview and not _inside(box, overview, margin=300):
            failures.append(f"stage card {stage_id} is outside overview frame {overview_id}")
    for index, left in enumerate(stage_boxes):
        for right in stage_boxes[index + 1:]:
            if _overlaps(left, right, gap=250):
                failures.append(f"stage cards {left['id']} and {right['id']} overlap or are too close")

    required_placements = {"project-charter": "control-center", "ddda.current-status": "control-center", "ddda.next-actions": "control-center"}
    for artifact_id, expected_frame in required_placements.items():
        placement = placements.get(artifact_id) or {}
        if placement.get("frame_id") != expected_frame:
            failures.append(f"managed placement {artifact_id} must use frame_id={expected_frame}")
        if not {"x", "y"}.issubset((placement.get("position") or {})):
            failures.append(f"managed placement {artifact_id} must have deterministic x/y")

    minimum_frame_width = float(contract.get("minimum_work_frame_width", 0))
    minimum_frame_height = float(contract.get("minimum_work_frame_height", 0))
    minimum_gap = float(contract.get("minimum_frame_gap", 0))
    work_frames = [frame for frame in frames if str(frame.get("role") or "work") != "overview"]
    canonical_shell_ids = [
        str(frame.get("id") or "")
        for frame in frames
        if frame.get("canonical_workshop_shell") is True
    ]
    if contract.get("require_canonical_workshop_shell"):
        if canonical_shell_ids != CANONICAL_SHELL_FRAME_IDS:
            failures.append(
                "canonical workshop shell must cover frames 20–82 exactly and preserve frames 01/10"
            )
    if contract.get("require_stage_columns"):
        owned_frame_ids: list[str] = []
        for column in stage_columns:
            column_x = float(column.get("x", 0))
            for owned_frame_id in column.get("frames") or []:
                owned_frame_id = str(owned_frame_id)
                owned_frame_ids.append(owned_frame_id)
                owned_frame = frame_by_id.get(owned_frame_id)
                if not owned_frame:
                    failures.append(f"stage column {column.get('id')} references unknown frame {owned_frame_id}")
                elif float(owned_frame.get("x", 0)) != column_x:
                    failures.append(f"frame {owned_frame_id} is outside its deterministic stage column")
        expected_owned = [str(frame.get("id") or "") for frame in work_frames]
        if sorted(owned_frame_ids) != sorted(expected_owned) or len(owned_frame_ids) != len(set(owned_frame_ids)):
            failures.append("stage columns must own every non-overview frame exactly once")
    for frame in work_frames:
        frame_id = str(frame.get("id") or "")
        if not frame.get("purpose_cs") or not frame.get("scaffold"):
            failures.append(f"frame {frame_id} has no purpose or workshop structure")
        if float(frame.get("width", 0)) < minimum_frame_width or float(frame.get("height", 0)) < minimum_frame_height:
            failures.append(f"frame {frame_id} is below minimum work-frame size")
        if frame_id != "control-center":
            guide = frame.get("guide") or {}
            for field in ("start_cs", "outputs_cs", "cookbook_url", "method_url", "starter_reference_url"):
                if not guide.get(field):
                    failures.append(f"frame {frame_id} guide is missing {field}")
            if frame.get("canonical_workshop_shell") is True:
                for field in (
                    "recipe_cs",
                    "done_criteria_cs",
                    "open_questions_cs",
                    "heuristics_cs",
                    "anti_patterns_cs",
                ):
                    if not guide.get(field):
                        failures.append(f"frame {frame_id} canonical guide is missing {field}")
            template = example_templates.get(str(frame.get("example_template") or "")) or {}
            if len(template.get("items") or []) < int(contract.get("minimum_example_items", 3)):
                failures.append(f"frame {frame_id} has no useful mini-example template")
            if contract.get("require_example_panel") and not template.get("panel"):
                failures.append(f"frame {frame_id} has no dedicated VZOR / LEGENDA panel")
            if contract.get("require_example_sync_ignore") and str(template.get("sync_policy") or "") != "ignore":
                failures.append(f"frame {frame_id} example template must be ignored by YAML sync")
            item_ids = {str(item.get("id") or "") for item in template.get("items") or []}
            for connector in template.get("connectors") or []:
                if str(connector.get("from") or "") not in item_ids or str(connector.get("to") or "") not in item_ids:
                    failures.append(f"frame {frame_id} example connector references an unknown item")
            example_layout, _title, panel = _template_layout(frame, template)
            local_frame = {"x": 0, "y": 0, "width": frame.get("width", 0), "height": frame.get("height", 0)}
            if not _inside(panel, local_frame, margin=100):
                failures.append(f"frame {frame_id} example panel is outside parent boundaries")
            if frame.get("canonical_workshop_shell") is True:
                shell = _workshop_shell_layout(frame)
                workspace = shell["workspace"]
                if not _inside(workspace, local_frame, margin=100):
                    failures.append(f"frame {frame_id} editable workspace is outside parent boundaries")
                if _overlaps(workspace, panel, gap=120):
                    failures.append(f"frame {frame_id} editable workspace overlaps VZOR / LEGENDA")
            for example_id, (x, y, width, height) in example_layout.items():
                if not _inside({"x": x, "y": y, "width": width, "height": height}, panel, margin=80):
                    failures.append(f"frame {frame_id} mini-example {example_id} is outside example panel")
    for index, left in enumerate(work_frames):
        for right in work_frames[index + 1:]:
            if _overlaps(left, right, gap=minimum_gap):
                failures.append(f"work frames {left.get('id')} and {right.get('id')} overlap or violate minimum gap")

    zone_stage_ids = [str(stage_id) for zone in zones for stage_id in (zone.get("stages") or [])]
    if sorted(zone_stage_ids) != sorted(EXPECTED_STAGES) or len(zones) != 4:
        failures.append("four aligned zone headers must cover every stage exactly once")
    zone_y = {float(zone.get("y", 0)) for zone in zones}
    if len(zone_y) != 1:
        failures.append("all high-level methodological zone headers must share one visual baseline")
    zone_ids = {str(zone.get("id") or "") for zone in zones}
    if len(zone_transitions) < int(contract.get("require_zone_connectors", 3)):
        failures.append("high-level methodological zones are missing flow connectors")
    for transition in zone_transitions:
        if str(transition.get("from") or "") not in zone_ids or str(transition.get("to") or "") not in zone_ids:
            failures.append("zone transition references an unknown zone")
    navigation_connector_count = len(zone_transitions) + len(transitions) + len(stages)
    if navigation_connector_count < int(contract.get("minimum_connector_count", 20)):
        failures.append(
            f"navigation requires at least {contract.get('minimum_connector_count', 20)} connectors, "
            f"got {navigation_connector_count}"
        )

    forward_pairs = {(str(item.get("from")), str(item.get("to"))) for item in transitions if item.get("kind") == "forward"}
    required_forward = set(zip(EXPECTED_STAGES, EXPECTED_STAGES[1:]))
    if not required_forward.issubset(forward_pairs):
        failures.append("method transitions do not cover the full G1–G8 forward journey")
    feedback_count = len([item for item in transitions if item.get("kind") == "feedback"])
    if feedback_count < int(contract.get("require_iteration_transitions", 2)):
        failures.append("method overview must show at least two explicit feedback transitions")
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
    example_connector_count = sum(len((example_templates.get(str(frame.get("example_template"))) or {}).get("connectors") or []) for frame in work_frames if frame.get("id") != "control-center")
    stage_connector_count = sum(len((stage_templates.get(str(stage.get("visual_template"))) or {}).get("connectors") or []) for stage in stages)
    return {
        "status": "PASS", "stage_count": len(stages), "gate_count": len(gates), "frame_count": len(frames),
        "traceability_count": len(traceability), "required_placements": sorted(required_placements),
        "stage_visual_count": sum(len((stage_templates.get(str(stage.get('visual_template'))) or {}).get("items") or []) for stage in stages),
        "workshop_example_count": sum(len((example_templates.get(str(frame.get('example_template'))) or {}).get("items") or []) for frame in work_frames if frame.get("id") != "control-center"),
        "transition_count": len(transitions), "feedback_transition_count": feedback_count,
        "zone_transition_count": len(zone_transitions), "example_connector_count": example_connector_count,
        "stage_connector_count": stage_connector_count,
        "canonical_workshop_shell_count": len(canonical_shell_ids),
        "stage_column_count": len(stage_columns),
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


def _delete_remote_system_item(client: MiroClient, board_id: str, entry: dict[str, Any]) -> None:
    remote_id = str(entry.get("miro_item_id") or "")
    if not remote_id:
        return
    if str(entry.get("item_type") or "") == "connector":
        client.delete_connector(board_id, remote_id)
    else:
        client.delete_item(board_id, remote_id)


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
    managed: bool = True,
    sync_policy: str = "managed",
) -> str | None:
    entry = _system_entry(mapping, item_id)
    if entry.get("miro_item_id") and str(entry.get("item_type") or "") != item_type:
        operations.append({"action": "replace_system_item_type", "item_id": item_id, "from": entry.get("item_type"), "to": item_type})
        if not dry_run:
            assert client is not None and board_id is not None
            _delete_remote_system_item(client, board_id, entry)
        mapping.setdefault("items", {}).pop(item_id, None)
        entry = {}
    action = "update_system_item" if entry.get("miro_item_id") else "create_system_item"
    operations.append({"action": action, "item_id": item_id, "item_type": item_type, "role": role, "frame_id": frame_id, "sync_policy": sync_policy})
    if dry_run:
        return None
    assert client is not None and board_id is not None
    remote = client.update_item(board_id, item_type, str(entry["miro_item_id"]), payload) if entry.get("miro_item_id") else client.create_item(board_id, item_type, payload)
    remote_id = str(remote["id"])
    mapping["items"][item_id] = {
        "miro_item_id": remote_id, "item_type": item_type, "frame_id": frame_id,
        "managed": managed, "system_item": True, "role": role, "sync_policy": sync_policy,
        "exclude_from_ingestion": sync_policy == "ignore",
        "position": dict(payload.get("position") or {}), "geometry": dict(payload.get("geometry") or {}),
        "style": dict(payload.get("style") or {}), "updated_at": utc_now(),
    }
    return remote_id


def _upsert_connector(
    *, mapping: dict[str, Any], operations: list[dict[str, Any]], client: MiroClient | None,
    board_id: str | None, dry_run: bool, item_id: str, payload: dict[str, Any], role: str,
    frame_id: str | None = None, sync_policy: str = "managed",
) -> str | None:
    entry = _system_entry(mapping, item_id)
    if entry.get("miro_item_id") and str(entry.get("item_type") or "") != "connector":
        if not dry_run:
            assert client is not None and board_id is not None
            _delete_remote_system_item(client, board_id, entry)
        mapping.setdefault("items", {}).pop(item_id, None)
        entry = {}
    action = "update_connector" if entry.get("miro_item_id") else "create_connector"
    operations.append({"action": action, "item_id": item_id, "item_type": "connector", "role": role, "frame_id": frame_id, "sync_policy": sync_policy})
    if dry_run:
        return None
    assert client is not None and board_id is not None
    remote = client.update_connector(board_id, str(entry["miro_item_id"]), payload) if entry.get("miro_item_id") else client.create_connector(board_id, payload)
    remote_id = str(remote["id"])
    mapping["items"][item_id] = {
        "miro_item_id": remote_id, "item_type": "connector", "frame_id": frame_id,
        "managed": False if sync_policy == "ignore" else True, "system_item": True,
        "role": role, "sync_policy": sync_policy, "exclude_from_ingestion": sync_policy == "ignore",
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
    sections = [
        f"<p><strong>ÚČEL</strong><br>{html.escape(str(frame.get('purpose_cs') or 'Řízená pracovní oblast.'))}</p>",
        f"<p><strong>JAK ZAČÍT</strong><br>{html.escape(str(guide.get('start_cs') or 'Začni fakty, hypotézami a otevřenými otázkami.'))}</p>",
    ]
    if frame.get("canonical_workshop_shell") is True:
        sections.extend([
            f"<p><strong>RECEPT</strong><br>{html.escape(str(guide.get('recipe_cs') or 'Postupuj od evidence přes hypotézy k ověřenému výstupu.'))}</p>",
            f"<p><strong>HOTOVO KDYŽ</strong><br>{html.escape(str(guide.get('done_criteria_cs') or guide.get('outputs_cs') or scaffold_names))}</p>",
            f"<p><strong>OTEVŘENÉ OTÁZKY</strong><br>{html.escape(str(guide.get('open_questions_cs') or 'Co ještě nevíme, kdo to ověří a do kdy?'))}</p>",
            f"<p><strong>HEURISTIKY</strong><br>{html.escape(str(guide.get('heuristics_cs') or 'Odděluj fakta, hypotézy a rozhodnutí.'))}</p>",
            f"<p><strong>ANTI-PATTERNS</strong><br>{html.escape(str(guide.get('anti_patterns_cs') or 'Nezaměňuj příklad za projektovou evidenci.'))}</p>",
        ])
    sections.extend([
        f"<p><strong>VÝSTUP</strong><br>{html.escape(str(guide.get('outputs_cs') or scaffold_names))}</p>",
        f"<p><strong>ARTEFAKTY</strong><br>{html.escape(scaffold_names)}</p>",
        f"<p>{_link('DDDA kuchařka', str(guide.get('cookbook_url') or ''))} · {_link('Metodika DDDA', str(guide.get('method_url') or ''))}</p>",
        f"<p>{_link('DDD Starter Modelling Process', str(guide.get('starter_reference_url') or ''))}</p>",
        f"<p>DDDA-SCAFFOLD:{project_id}:{frame['id']}:guide</p>",
    ])
    return "".join(sections)


def _control_usage_content(frame: dict[str, Any], project_id: str, scaffold: dict[str, Any]) -> str:
    guide = scaffold.get("board_guide") or {}
    steps = guide.get("steps_cs") or []
    compact = "".join(f"<p><strong>{index}.</strong> {html.escape(str(step))}</p>" for index, step in enumerate(steps, start=1))
    links = " · ".join([
        _link("Podrobný návod", str(guide.get("details_url") or "")),
        _link("Kuchařka", str(guide.get("cookbook_url") or "")),
        _link("Metodika DDDA", str(guide.get("method_url") or "")),
        _link("DDD Starter", str(guide.get("starter_reference_url") or "")),
        _link("Knowledge index", str(guide.get("knowledge_index_url") or "")),
    ])
    return "".join([
        f"<p><strong>{html.escape(str(guide.get('title_cs') or 'Jak board používat'))}</strong></p>",
        compact,
        f"<p>{links}</p>",
        "<p><strong>Autorita:</strong> Git/YAML + explicitní human gate decision. VZOR / LEGENDA je pouze pomůcka a sync ji ignoruje.</p>",
        f"<p>DDDA-SCAFFOLD:{project_id}:control-center:usage</p>",
    ])

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


def _sticky_payload(
    *, content: str, x: float, y: float, width: float, fill_color: str,
    parent_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "data": {"content": content, "shape": "rectangle"},
        "style": {"fillColor": fill_color},
        "position": {"x": x, "y": y, "origin": "center"},
        "geometry": {"width": width},
    }
    if parent_id:
        payload["parent"] = {"id": parent_id}
    return payload


def _visual_payload(
    item: dict[str, Any], *, x: float, y: float, width: float, height: float,
    font_size: float, parent_id: str | None,
) -> tuple[str, dict[str, Any]]:
    item_type = str(item.get("item_type") or "shape")
    content = "".join(f"<p>{html.escape(line)}</p>" for line in str(item.get("label_cs") or item.get("id") or "").splitlines())
    if item_type == "sticky_note":
        return item_type, _sticky_payload(content=content, x=x, y=y, width=width, fill_color=str(item.get("fill_color") or "light_yellow"), parent_id=parent_id)
    if item_type == "text":
        return item_type, _text_payload(content=content, x=x, y=y, width=width, font_size=font_size, parent_id=parent_id, text_align=str(item.get("text_align") or "center"), color=str(item.get("color") or "#1F2937"))
    return "shape", _shape_payload(
        content=content, x=x, y=y, width=width, height=height,
        fill_color=str(item.get("fill_color") or "#FFFFFF"), font_size=font_size,
        shape=str(item.get("shape") or "rectangle"), parent_id=parent_id,
        border_color=str(item.get("border_color") or "#64748B"),
        border_width=float(item.get("border_width", 2)),
    )


def _connector_payload(
    start_item_id: str, end_item_id: str, label: str, *, shape: str = "straight",
    stroke_color: str = "#365A8C", stroke_style: str = "normal",
    start_snap: str = "auto", end_snap: str = "auto",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "startItem": {"id": start_item_id, "snapTo": start_snap},
        "endItem": {"id": end_item_id, "snapTo": end_snap},
        "shape": shape,
        "style": {"strokeColor": stroke_color, "strokeWidth": 2, "strokeStyle": stroke_style, "endStrokeCap": "stealth", "fontSize": 24, "color": stroke_color},
    }
    if label:
        payload["captions"] = [{"content": html.escape(label), "position": 0.5, "textAlignVertical": "top"}]
    return payload


def _artifact_status_bucket(status: str, table_cfg: dict[str, Any]) -> str:
    normalized = str(status or "candidate").lower()
    for definition in table_cfg.get("statuses") or []:
        aliases = {str(item).lower() for item in definition.get("aliases") or []}
        if normalized == str(definition.get("id") or "").lower() or normalized in aliases:
            return str(definition.get("id"))
    return "working"


def _artifact_payload(artifact: Any) -> dict[str, Any]:
    document = artifact.document if isinstance(artifact.document, dict) else {}
    payload = document.get("artifact", document)
    return payload if isinstance(payload, dict) else {}


def _artifact_provenance(artifact: Any, table_cfg: dict[str, Any]) -> str:
    payload = _artifact_payload(artifact)
    miro = payload.get("miro") if isinstance(payload.get("miro"), dict) else {}
    raw = str(payload.get("provenance") or miro.get("provenance") or "generated").lower()
    aliases: dict[str, str] = {}
    for definition in table_cfg.get("provenance_values") or []:
        provenance_id = str(definition.get("id") or "")
        aliases[provenance_id.lower()] = provenance_id
        for alias in definition.get("aliases") or []:
            aliases[str(alias).lower()] = provenance_id
    return aliases.get(raw, "manual")


def _artifact_owner(artifact: Any) -> str:
    payload = _artifact_payload(artifact)
    owner = payload.get("owner") or payload.get("owners") or "NEURČENO"
    if isinstance(owner, dict):
        owner = owner.get("name") or owner.get("id") or ", ".join(map(str, owner.values()))
    if isinstance(owner, list):
        owner = ", ".join(map(str, owner))
    return str(owner)


def _artifact_revision(artifact: Any, project_commit: str) -> str:
    payload = _artifact_payload(artifact)
    revision = str(payload.get("revision") or payload.get("git_revision") or project_commit or "UNCOMMITTED")
    return revision[:12] if len(revision) >= 12 else revision


def _workshop_shell_layout(frame: dict[str, Any]) -> dict[str, dict[str, float]]:
    frame_width = float(frame.get("width", 5200))
    frame_height = float(frame.get("height", 4200))
    outer_margin = 180.0
    zone_gap = 180.0
    if frame.get("canonical_workshop_shell") is not True:
        legacy_guide_width = min(2100.0, max(1550.0, frame_width * 0.34))
        panel_left = -frame_width / 2 + legacy_guide_width + 300
        panel_right = frame_width / 2 - outer_margin
        panel_top = -frame_height / 2 + 240
        panel_bottom = frame_height / 2 - outer_margin
        return {
            "guide": {
                "x": -frame_width / 2 + legacy_guide_width / 2 + 120,
                "y": -frame_height / 2 + 900,
                "width": legacy_guide_width,
                "height": frame_height - 2 * outer_margin,
            },
            "workspace": {"x": 0, "y": 0, "width": 0, "height": 0},
            "example": {
                "x": (panel_left + panel_right) / 2,
                "y": (panel_top + panel_bottom) / 2,
                "width": panel_right - panel_left,
                "height": panel_bottom - panel_top,
            },
        }

    guide_width = min(1900.0, max(1400.0, frame_width * 0.28))
    example_width = min(2100.0, max(1400.0, frame_width * 0.30))
    usable_width = frame_width - 2 * outer_margin - 2 * zone_gap
    workspace_width = usable_width - guide_width - example_width
    left = -frame_width / 2 + outer_margin
    panel_top = -frame_height / 2 + 180
    panel_bottom = frame_height / 2 - 180
    guide = {
        "x": left + guide_width / 2,
        "y": -frame_height / 2 + 1240,
        "width": guide_width,
        "height": panel_bottom - panel_top,
    }
    workspace_left = left + guide_width + zone_gap
    workspace = {
        "x": workspace_left + workspace_width / 2,
        "y": (panel_top + panel_bottom) / 2,
        "width": workspace_width,
        "height": panel_bottom - panel_top,
    }
    example_left = workspace_left + workspace_width + zone_gap
    example = {
        "x": example_left + example_width / 2,
        "y": (panel_top + panel_bottom) / 2,
        "width": example_width,
        "height": panel_bottom - panel_top,
    }
    return {"guide": guide, "workspace": workspace, "example": example}


def _template_layout(frame: dict[str, Any], template: dict[str, Any]) -> tuple[dict[str, tuple[float, float, float, float]], tuple[float, float, float], dict[str, float]]:
    shell = _workshop_shell_layout(frame)
    panel = shell["example"]
    panel_left = panel["x"] - panel["width"] / 2
    panel_right = panel["x"] + panel["width"] / 2
    panel_top = panel["y"] - panel["height"] / 2
    panel_bottom = panel["y"] + panel["height"] / 2
    title_y = panel_top + 220
    item_top = panel_top + 520
    items = template.get("items") or []
    if not items:
        return {}, ((panel_left + panel_right) / 2, title_y, max(900.0, panel_right - panel_left - 160)), panel
    min_left = min(float(item.get("x", 0)) - float(item.get("width", 0)) / 2 for item in items)
    max_right = max(float(item.get("x", 0)) + float(item.get("width", 0)) / 2 for item in items)
    min_top = min(float(item.get("y", 0)) - float(item.get("height", 0)) / 2 for item in items)
    max_bottom = max(float(item.get("y", 0)) + float(item.get("height", 0)) / 2 for item in items)
    source_width = max(max_right - min_left, 1.0)
    source_height = max(max_bottom - min_top, 1.0)
    target_width = max(panel_right - panel_left - 220, 900.0)
    target_height = max(panel_bottom - item_top - 120, 900.0)
    scale = min(target_width / source_width, target_height / source_height, 1.1)
    source_center_x = (min_left + max_right) / 2
    source_center_y = (min_top + max_bottom) / 2
    target_center_x = (panel_left + panel_right) / 2
    target_center_y = (item_top + panel_bottom - 100) / 2
    result: dict[str, tuple[float, float, float, float]] = {}
    for item in items:
        item_id = str(item.get("id") or "item")
        result[item_id] = (
            target_center_x + (float(item.get("x", 0)) - source_center_x) * scale,
            target_center_y + (float(item.get("y", 0)) - source_center_y) * scale,
            float(item.get("width", 900)) * scale,
            float(item.get("height", 600)) * scale,
        )
    return result, (target_center_x, title_y, target_width), panel

def _render_frame_guide_and_example(
    *, scaffold: dict[str, Any], frame: dict[str, Any], frame_remote_id: str,
    mapping: dict[str, Any], operations: list[dict[str, Any]], client: MiroClient,
    board_id: str, project_id: str,
) -> None:
    frame_id = str(frame["id"])
    minimum_fonts = (scaffold.get("coordinate_system") or {}).get("minimum_font_size") or {}
    shell = _workshop_shell_layout(frame)
    guide = shell["guide"]
    guide_payload = _text_payload(
        content=_frame_guide_content(frame, project_id),
        x=guide["x"],
        y=guide["y"],
        width=guide["width"],
        font_size=float(minimum_fonts.get("workshop_guide", 22)),
        parent_id=frame_remote_id, text_align="left",
    )
    _upsert_system_item(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False,
        item_id=f"{frame_id}:guide", item_type="text", payload=guide_payload, frame_id=frame_id, role="workshop_guide")

    if frame.get("canonical_workshop_shell") is True:
        workspace = shell["workspace"]
        workspace_payload = _shape_payload(
            content=(
                "<p><strong>EDITOVATELNÁ PRACOVNÍ PLOCHA</strong></p>"
                "<p>Sem patří projektový workshopový obsah. Rozlišuj fakta, hypotézy, "
                "rozhodnutí, ownera a otevřené otázky.</p>"
            ),
            x=workspace["x"], y=workspace["y"],
            width=workspace["width"], height=workspace["height"],
            fill_color="#F8FAFC", font_size=18, shape="rectangle",
            parent_id=frame_remote_id, border_color="#94A3B8", border_width=2,
            text_align="center", text_align_vertical="top",
        )
        _upsert_system_item(
            mapping=mapping, operations=operations, client=client, board_id=board_id,
            dry_run=False, item_id=f"workspace-panel:{frame_id}", item_type="shape",
            payload=workspace_payload, frame_id=frame_id, role="workshop_workspace_panel",
            managed=False, sync_policy="manual",
        )

    template = (scaffold.get("example_templates") or {}).get(str(frame.get("example_template") or "")) or {}
    layout, title, panel = _template_layout(frame, template)
    panel_payload = _shape_payload(
        content="", x=panel["x"], y=panel["y"], width=panel["width"], height=panel["height"],
        fill_color="#FFFFFF", font_size=18, shape="rectangle", parent_id=frame_remote_id,
        border_color="#365A8C", border_width=2,
    )
    _upsert_system_item(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False,
        item_id=f"example-panel:{frame_id}", item_type="shape", payload=panel_payload, frame_id=frame_id,
        role="workshop_example_panel", managed=False, sync_policy="ignore")
    title_x, title_y, title_width = title
    panel_cfg = template.get("panel") or {}
    title_payload = _text_payload(
        content=f"<p><strong>{html.escape(str(panel_cfg.get('title_cs') or template.get('title_cs') or 'VZOR / LEGENDA'))}</strong></p><p>{html.escape(str(template.get('title_cs') or ''))}</p>",
        x=title_x, y=title_y, width=title_width,
        font_size=max(float(minimum_fonts.get("workshop_example", 20)) + 3, 23),
        parent_id=frame_remote_id, text_align="center", color="#365A8C",
    )
    _upsert_system_item(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False,
        item_id=f"example:{frame_id}:title", item_type="text", payload=title_payload, frame_id=frame_id,
        role="workshop_example_title", managed=False, sync_policy="ignore")

    remote_ids: dict[str, str] = {}
    for item in template.get("items") or []:
        item_id = str(item.get("id") or "item")
        x, y, width, height = layout[item_id]
        visual_item = dict(item)
        if str(template.get("representation") or "") == "table_grid":
            visual_item["shape"] = "rectangle"
            visual_item["border_width"] = max(float(visual_item.get("border_width", 1)), 2)
        item_type, payload = _visual_payload(visual_item, x=x, y=y, width=width, height=height,
            font_size=max(float(minimum_fonts.get("workshop_example", 20)), float(item.get("font_size", 20))), parent_id=frame_remote_id)
        remote_id = _upsert_system_item(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False,
            item_id=f"example:{frame_id}:{item_id}", item_type=item_type, payload=payload, frame_id=frame_id,
            role="workshop_example", managed=False, sync_policy="ignore")
        if remote_id:
            remote_ids[item_id] = remote_id
    for connector in template.get("connectors") or []:
        start = remote_ids.get(str(connector.get("from") or ""))
        end = remote_ids.get(str(connector.get("to") or ""))
        if not start or not end:
            raise ValueError(f"Example connector {frame_id}/{connector.get('id')} has no rendered endpoints")
        _upsert_connector(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False,
            item_id=f"example-connector:{frame_id}:{connector.get('id')}",
            payload=_connector_payload(start, end, str(connector.get("label_cs") or ""), shape=str(connector.get("shape") or "straight"),
                stroke_color=str(connector.get("stroke_color") or "#365A8C"), stroke_style=str(connector.get("stroke_style") or "normal")),
            frame_id=frame_id, role="workshop_example_connector", sync_policy="ignore")

def _delete_deprecated_items(
    *, mapping: dict[str, Any], operations: list[dict[str, Any]], client: MiroClient, board_id: str,
) -> None:
    deprecated = [
        item_id for item_id, entry in (mapping.get("items") or {}).items()
        if (item_id.endswith(":instructions") and str((entry or {}).get("role") or "") == "workshop_template")
        or (
            str((entry or {}).get("role") or "") == "method_transition"
            and str((entry or {}).get("item_type") or "") != "connector"
        )
        or str((entry or {}).get("role") or "") == "artifact_status_table"
    ]
    for item_id in deprecated:
        entry = mapping["items"].get(item_id) or {}
        _delete_remote_system_item(client, board_id, entry)
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


def _load_remote_connectors(client: MiroClient, board_id: str, expected_ids: set[str]) -> list[dict[str, Any]]:
    latest: list[dict[str, Any]] = []
    for attempt in range(4):
        latest = client.list_connectors(board_id)
        actual_ids = {str(item.get("id") or "") for item in latest}
        if expected_ids.issubset(actual_ids):
            return latest
        if attempt < 3:
            time.sleep(1.0 + attempt)
    missing = sorted(expected_ids - {str(item.get("id") or "") for item in latest})
    raise ValueError(f"Miro remote connector snapshot is incomplete; missing connector IDs: {missing[:10]}")

def validate_remote_layout(
    scaffold: dict[str, Any], mapping: dict[str, Any], remote_items: list[dict[str, Any]],
    remote_connectors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    all_remote = list(remote_items) + list(remote_connectors or [])
    remote_by_id = {str(item.get("id") or ""): item for item in all_remote}
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
    for index, left in enumerate(work_remote):
        for right in work_remote[index + 1:]:
            if _overlaps(left, right, gap=float(contract.get("minimum_frame_gap", 0))):
                failures.append(f"remote work frames {left.get('semantic_id')} and {right.get('semantic_id')} overlap")

    role_entries: dict[str, list[tuple[str, dict[str, Any], dict[str, Any]]]] = {}
    for item_id, entry in (mapping.get("items") or {}).items():
        if not (entry or {}).get("system_item"):
            continue
        remote = remote_by_id.get(str((entry or {}).get("miro_item_id") or ""))
        if not remote:
            failures.append(f"remote system item {item_id} is missing")
            continue
        role_entries.setdefault(str((entry or {}).get("role") or "unknown"), []).append((item_id, entry, remote))
    stage_cards = role_entries.get("journey_gate") or []
    gate_markers = role_entries.get("journey_gate_marker") or []
    if len(stage_cards) != 8 or len(gate_markers) != 8:
        failures.append(f"remote overview must contain 8 stage flow shapes and 8 gate diamonds, got {len(stage_cards)}/{len(gate_markers)}")
    for item_id, _entry, remote in stage_cards:
        if float((remote.get("style") or {}).get("fontSize") or 0) < float(minimum_fonts.get("journey", 28)):
            failures.append(f"{item_id} font size is below readable minimum")
    stage_visuals = role_entries.get("stage_visual") or []
    for gate_id in GATE_IDS:
        if len([item_id for item_id, _, _ in stage_visuals if item_id.startswith(f"stage-visual:{gate_id}:")]) < int(contract.get("minimum_stage_visual_items", 4)):
            failures.append(f"{gate_id} has too few methodological visual items")
    legends = role_entries.get("gate_state_legend") or []
    if len(legends) != 5:
        failures.append(f"remote control frame must contain 5 gate-state legend cards, got {len(legends)}")
    guides = role_entries.get("workshop_guide") or []
    for item_id, entry, remote in guides:
        position = entry.get("position") or {}
        if float(position.get("x", 0)) >= 0 or float(position.get("y", 0)) >= 0:
            failures.append(f"{item_id} is not anchored in the top-left quadrant")
        if float((remote.get("style") or {}).get("fontSize") or 0) < float(minimum_fonts.get("workshop_guide", 22)):
            failures.append(f"{item_id} font size is below readable minimum")
    examples = role_entries.get("workshop_example") or []
    panels = role_entries.get("workshop_example_panel") or []
    workspaces = role_entries.get("workshop_workspace_panel") or []
    for frame in frames:
        frame_id = str(frame.get("id") or "")
        if frame_id in {overview_id, "control-center"}:
            continue
        if len([item_id for item_id, _, _ in examples if item_id.startswith(f"example:{frame_id}:")]) < int(contract.get("minimum_example_items", 3)):
            failures.append(f"remote frame {frame_id} has too few example items")
        panel_entries = [entry for item_id, entry, _ in panels if item_id == f"example-panel:{frame_id}"]
        if len(panel_entries) != 1 or panel_entries[0].get("sync_policy") != "ignore":
            failures.append(f"remote frame {frame_id} has no sync-ignored example panel")
        workspace_entries = [
            entry for item_id, entry, _ in workspaces
            if item_id == f"workspace-panel:{frame_id}"
        ]
        if frame.get("canonical_workshop_shell") is True:
            if len(workspace_entries) != 1 or workspace_entries[0].get("sync_policy") != "manual":
                failures.append(f"remote frame {frame_id} has no editable manual workspace panel")
        elif workspace_entries:
            failures.append(f"preserved frame {frame_id} must not receive the canonical workspace shell")
    zones = role_entries.get("zone_header") or []
    zone_connectors = role_entries.get("zone_transition") or []
    method_connectors = role_entries.get("method_transition") or []
    stage_gate_connectors = role_entries.get("stage_gate_transition") or []
    if len(zones) != 4 or len(zone_connectors) < int(contract.get("require_zone_connectors", 3)):
        failures.append("remote overview does not expose four aligned zones with connectors")
    if len(method_connectors) < 9 or len(stage_gate_connectors) != 8:
        failures.append("remote overview does not expose full named stage/gate flow plus feedback loops")
    navigation_connector_count = len(zone_connectors) + len(method_connectors) + len(stage_gate_connectors)
    if navigation_connector_count < int(contract.get("minimum_connector_count", 20)):
        failures.append(
            f"remote overview exposes only {navigation_connector_count} navigation connectors; "
            f"minimum is {contract.get('minimum_connector_count', 20)}"
        )
    resources = role_entries.get("overview_resource_panel") or []
    if len(resources) != 1:
        failures.append("remote overview resource panel is missing")
    gate_state_titles = role_entries.get("project_gate_state_title") or []
    lifecycle_legends = role_entries.get("artifact_lifecycle_legend") or []
    provenance_legends = role_entries.get("artifact_provenance_legend") or []
    artifact_registry_titles = role_entries.get("artifact_registry_title") or []
    artifact_registry = role_entries.get("artifact_registry_table") or []
    if len(gate_state_titles) != 1:
        failures.append("control-center Project / Gate State title is missing")
    if len(lifecycle_legends) != 1:
        failures.append("control-center Artifact Lifecycle legend is missing")
    if len(provenance_legends) != 1:
        failures.append("control-center Artifact Provenance legend is missing")
    if len(artifact_registry_titles) != 1:
        failures.append("control-center Artifact Registry title is missing")
    registry_cfg = scaffold.get("artifact_status_tables") or {}
    expected_registry_cells = len(registry_cfg.get("registry_columns") or []) * (
        1 + int(registry_cfg.get("max_artifact_rows", 4))
    )
    if len(artifact_registry) != expected_registry_cells:
        failures.append(
            f"control-center Artifact Registry projection is incomplete: "
            f"{len(artifact_registry)} vs {expected_registry_cells}"
        )
    ignored_roles = (
        examples
        + panels
        + (role_entries.get("workshop_example_title") or [])
        + (role_entries.get("workshop_example_connector") or [])
        + stage_visuals
        + (role_entries.get("stage_visual_connector") or [])
        + lifecycle_legends
        + provenance_legends
        + artifact_registry_titles
        + artifact_registry
    )
    ignored = [entry for _item_id, entry, _remote in ignored_roles]
    if any(entry.get("sync_policy") != "ignore" or not entry.get("exclude_from_ingestion") for entry in ignored):
        failures.append("reference or registry projection content is not explicitly excluded from YAML sync/ingestion")
    if failures:
        raise ValueError("Miro remote layout contract failed: " + "; ".join(failures))
    return {
        "status": "PASS", "remote_item_count": len(remote_items), "remote_connector_count": len(remote_connectors or []),
        "remote_frame_count": len(frame_remote), "journey_card_count": len(stage_cards), "gate_marker_count": len(gate_markers),
        "stage_visual_count": len(stage_visuals), "gate_legend_count": len(legends), "workshop_guide_count": len(guides),
        "workshop_example_count": len(examples), "example_panel_count": len(panels), "zone_header_count": len(zones),
        "workshop_workspace_count": len(workspaces),
        "zone_transition_count": len(zone_connectors), "transition_count": len(method_connectors) + len(stage_gate_connectors),
        "navigation_connector_count": navigation_connector_count,
        "artifact_registry_cell_count": len(artifact_registry),
        "artifact_status_table_item_count": len(artifact_registry),
        "state_lifecycle_provenance_separation": "PASS",
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
            board = client.create_board(f"DDDA – {config.name}", f"DDDA project {config.project_id}; managed through YAML and Git. Miro is a projection, not gate authority.", team_id=config.team_id, project_id=config.miro_project_id)
            board_id = str(board["id"])
    mapping = load_map(config.root, config.project_id, board_id)
    palette = scaffold.get("palette") or {}
    frames = scaffold.get("frames") or []
    frame_remote_ids: dict[str, str] = {}
    frame_titles = {str(frame.get("id")): str(frame.get("title_cs") or frame.get("id")) for frame in frames}
    for frame in frames:
        frame_id = str(frame["id"])
        entry = mapping["frames"].get(frame_id) or {}
        payload = _frame_payload(frame, palette)
        operations.append({"action": "update_frame" if entry.get("miro_item_id") else "create_frame", "frame_id": frame_id, "title": payload["data"]["title"]})
        if dry_run:
            if frame_id not in {"control-center", str((scaffold.get("visual_contract") or {}).get("overview_frame") or "method-overview")}:
                if frame.get("canonical_workshop_shell") is True:
                    operations.append({
                        "action": "create_system_item",
                        "item_id": f"workspace-panel:{frame_id}",
                        "item_type": "shape",
                        "role": "workshop_workspace_panel",
                        "sync_policy": "manual",
                    })
                operations.append({"action": "create_system_item", "item_id": f"example-panel:{frame_id}", "item_type": "shape", "role": "workshop_example_panel", "sync_policy": "ignore"})
                template = (scaffold.get("example_templates") or {}).get(str(frame.get("example_template") or "")) or {}
                for item in template.get("items") or []:
                    operations.append({"action": "create_system_item", "item_id": f"example:{frame_id}:{item.get('id')}", "item_type": item.get("item_type", "shape"), "role": "workshop_example", "sync_policy": "ignore"})
                for connector in template.get("connectors") or []:
                    operations.append({"action": "create_connector", "item_id": f"example-connector:{frame_id}:{connector.get('id')}", "item_type": "connector", "role": "workshop_example_connector", "sync_policy": "ignore"})
            continue
        assert client is not None and board_id is not None
        remote = client.update_item(board_id, "frame", str(entry["miro_item_id"]), payload) if entry.get("miro_item_id") else client.create_item(board_id, "frame", payload)
        remote_id = str(remote["id"])
        frame_remote_ids[frame_id] = remote_id
        mapping["frames"][frame_id] = {"miro_item_id": remote_id, "role": frame.get("role") or "work", "stage": frame.get("stage"), "title": payload["data"]["title"], "position": payload["position"], "geometry": payload["geometry"], "updated_at": utc_now()}
    if dry_run:
        for stage in scaffold.get("method_flow", {}).get("stages") or []:
            gate_id = str(stage.get("gate_after") or "")
            operations.extend([
                {"action": "create_system_item", "item_id": f"journey:{gate_id}", "item_type": "shape", "role": "journey_gate"},
                {"action": "create_system_item", "item_id": f"gate-marker:{gate_id}", "item_type": "shape", "role": "journey_gate_marker"},
                {"action": "create_connector", "item_id": f"stage-gate:{gate_id}", "item_type": "connector", "role": "stage_gate_transition"},
            ])
        for zone in scaffold.get("zones") or []:
            operations.append({"action": "create_system_item", "item_id": str(zone.get("id")), "item_type": "shape", "role": "zone_header"})
        for transition in scaffold.get("zone_transitions") or []:
            operations.append({"action": "create_connector", "item_id": f"zone-transition:{transition.get('id')}", "item_type": "connector", "role": "zone_transition"})
        for transition in scaffold.get("method_transitions") or []:
            operations.append({"action": "create_connector", "item_id": f"transition:{transition.get('kind')}:{transition.get('id')}", "item_type": "connector", "role": "method_transition"})
        return {"project_id": config.project_id, "board_id": board_id, "dry_run": True, "operations": operations, "operation_count": len(operations), "technical_sync_status": "NOT_RUN", "layout_contract_status": contract["status"], "remote_layout_status": "NOT_RUN", "utf8_status": "PASS", "human_visual_acceptance_status": "PENDING", "overall_status": "PENDING_HUMAN_REVIEW", "traceability_count": contract["traceability_count"], "review_team_selection_status": "EXPLICIT_TEAM" if config.team_id else "DEFAULT_TOKEN_TEAM"}

    assert client is not None and board_id is not None
    _delete_deprecated_items(mapping=mapping, operations=operations, client=client, board_id=board_id)
    overview_id = str((scaffold.get("visual_contract") or {}).get("overview_frame") or "method-overview")
    control_frame = frame_remote_ids.get("control-center") or str((mapping["frames"].get("control-center") or {}).get("miro_item_id") or "")
    if not control_frame:
        raise ValueError("Navigation frame 00 – Control Center was not rendered")
    for frame in frames:
        frame_id = str(frame["id"])
        if frame_id in {overview_id, "control-center"}:
            continue
        frame_remote_id = frame_remote_ids.get(frame_id) or str((mapping["frames"].get(frame_id) or {}).get("miro_item_id") or "")
        if not frame_remote_id:
            raise ValueError(f"Work frame {frame_id} was not rendered")
        _render_frame_guide_and_example(scaffold=scaffold, frame=frame, frame_remote_id=frame_remote_id, mapping=mapping, operations=operations, client=client, board_id=board_id, project_id=config.project_id)

    # Control Center summary and compact onboarding.
    _upsert_system_item(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False,
        item_id="control-center:summary", item_type="text", payload=_text_payload(content=_control_summary(config, context), x=-2300, y=-2350, width=4000, font_size=22, parent_id=control_frame, text_align="left"), frame_id="control-center", role="control_center_summary")
    control_cfg = next(frame for frame in frames if str(frame.get("id")) == "control-center")
    _upsert_system_item(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False,
        item_id="control-center:usage", item_type="text", payload=_text_payload(content=_control_usage_content(control_cfg, config.project_id, scaffold), x=2300, y=-2350, width=4000, font_size=18, parent_id=control_frame, text_align="left", color="#365A8C"), frame_id="control-center", role="control_center_usage")

    minimum_fonts = (scaffold.get("coordinate_system") or {}).get("minimum_font_size") or {}
    status_defs = _status_definitions(scaffold)
    gate_configs = {str(item.get("id")): item for item in scaffold.get("gates") or []}
    stage_card = (scaffold.get("coordinate_system") or {}).get("stage_card") or {}
    stage_width, stage_height = float(stage_card.get("width", 3400)), float(stage_card.get("height", 2000))
    journey_ids: dict[str, str] = {}
    gate_marker_ids: dict[str, str] = {}
    stage_visual_ids: dict[str, dict[str, str]] = {}
    for stage in scaffold.get("method_flow", {}).get("stages") or []:
        gate_id = str(stage.get("gate_after") or "")
        gate_state = context["gates"].get(gate_id) or {"status": "not_ready", "missing": []}
        content, fill_color = _gate_content(gate_id, stage, gate_configs.get(gate_id) or {}, gate_state, status_defs, context["current_gate"], frame_titles)
        stage_remote = _upsert_system_item(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False,
            item_id=f"journey:{gate_id}", item_type="shape", payload=_shape_payload(content=content, x=float(stage.get("x", 0)), y=float(stage.get("y", -6200)), width=stage_width, height=stage_height, fill_color=fill_color, font_size=float(minimum_fonts.get("journey", 28)), shape=str(stage.get("shape") or "hexagon"), border_color="#365A8C", border_width=4 if gate_id == context["current_gate"] else 2, text_align="center", text_align_vertical="top"), role="journey_gate")
        if stage_remote:
            journey_ids[str(stage.get("id"))] = stage_remote
        status_id = str(gate_state.get("status") or "not_ready")
        status_def = status_defs.get(status_id) or {}
        gate_remote = _upsert_system_item(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False,
            item_id=f"gate-marker:{gate_id}", item_type="shape", payload=_shape_payload(content=f"<p><strong>{html.escape(gate_id)}</strong></p><p>{html.escape(str(status_def.get('symbol') or '•'))}</p>", x=float(stage.get("x", 0)), y=float(stage.get("y", -6200))+1550, width=800, height=800, fill_color=str(status_def.get("fill_color") or "#FFFFFF"), font_size=26, shape="rhombus", border_color="#365A8C", border_width=3), role="journey_gate_marker")
        if gate_remote:
            gate_marker_ids[gate_id]=gate_remote
        if stage_remote and gate_remote:
            _upsert_connector(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False, item_id=f"stage-gate:{gate_id}", payload=_connector_payload(stage_remote, gate_remote, f"{gate_id} · lidské rozhodnutí", shape="straight", start_snap="bottom", end_snap="top"), role="stage_gate_transition")
        template = (scaffold.get("stage_visual_templates") or {}).get(str(stage.get("visual_template") or "")) or {}
        stage_visual_ids[gate_id]={}
        for item in template.get("items") or []:
            item_id = str(item.get("id") or "item")
            item_type, payload = _visual_payload(item, x=float(stage.get("x", 0))+float(item.get("x", 0))*0.75, y=float(stage.get("y", 0))+2850+float(item.get("y", 0))*0.55, width=float(item.get("width", 760))*0.75, height=float(item.get("height", 420))*0.75, font_size=max(float(minimum_fonts.get("stage_example", 20)), float(item.get("font_size", 20))), parent_id=None)
            rid=_upsert_system_item(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False, item_id=f"stage-visual:{gate_id}:{item_id}", item_type=item_type, payload=payload, role="stage_visual", managed=False, sync_policy="ignore")
            if rid: stage_visual_ids[gate_id][item_id]=rid
        for connector in template.get("connectors") or []:
            start=stage_visual_ids[gate_id].get(str(connector.get("from") or "")); end=stage_visual_ids[gate_id].get(str(connector.get("to") or ""))
            if start and end:
                _upsert_connector(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False, item_id=f"stage-visual-connector:{gate_id}:{connector.get('id')}", payload=_connector_payload(start,end,str(connector.get("label_cs") or ""),shape=str(connector.get("shape") or "straight")), role="stage_visual_connector", sync_policy="ignore")

    # Overview resources and aligned zones.
    resources = scaffold.get("overview_resources") or []
    resource_content = "<p><strong>METODIKA A ZDROJE</strong></p>" + "".join(f"<p>{_link(str(item.get('label_cs') or item.get('id')), str(item.get('url') or ''))}</p>" for item in resources)
    _upsert_system_item(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False, item_id="overview:resources", item_type="text", payload=_text_payload(content=resource_content, x=-16000, y=-10600, width=7000, font_size=24, text_align="left", color="#365A8C"), role="overview_resource_panel")
    zone_ids: dict[str,str]={}
    for zone in scaffold.get("zones") or []:
        rid=_upsert_system_item(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False, item_id=str(zone.get("id")), item_type="shape", payload=_shape_payload(content=f"<p><strong>{html.escape(str(zone.get('title_cs') or zone.get('id')))}</strong></p>", x=float(zone.get("x",0)), y=float(zone.get("y",-9200)), width=float(zone.get("width",4200)), height=float(zone.get("height",650)), fill_color="#E0F2FE", font_size=float(minimum_fonts.get("zone_header",28)), shape="rectangle", border_color="#2F7E95", border_width=3), role="zone_header")
        if rid: zone_ids[str(zone.get("id"))]=rid
    for transition in scaffold.get("zone_transitions") or []:
        start=zone_ids.get(str(transition.get("from") or "")); end=zone_ids.get(str(transition.get("to") or ""))
        if start and end:
            _upsert_connector(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False, item_id=f"zone-transition:{transition.get('id')}", payload=_connector_payload(start,end,str(transition.get("label_cs") or ""),shape=str(transition.get("shape") or "straight"),start_snap="right",end_snap="left"), role="zone_transition")

    # Named forward and feedback connectors between gate diamonds and stage flow shapes.
    stage_order={str(stage.get("id")):str(stage.get("gate_after")) for stage in scaffold.get("method_flow",{}).get("stages") or []}
    for transition in scaffold.get("method_transitions") or []:
        from_stage=str(transition.get("from") or ""); to_stage=str(transition.get("to") or "")
        kind=str(transition.get("kind") or "forward")
        start = gate_marker_ids.get(stage_order.get(from_stage,"")) if kind=="forward" else journey_ids.get(from_stage)
        end = journey_ids.get(to_stage)
        if not start or not end:
            raise ValueError(f"Method transition {transition.get('id')} has no rendered endpoints")
        _upsert_connector(mapping=mapping, operations=operations, client=client, board_id=board_id, dry_run=False, item_id=f"transition:{kind}:{transition.get('id')}", payload=_connector_payload(start,end,str(transition.get("label_cs") or ""),shape=str(transition.get("shape") or ("curved" if kind=="feedback" else "elbowed")),stroke_color="#B45309" if kind=="feedback" else "#365A8C",stroke_style="dashed" if kind=="feedback" else "normal",start_snap="auto",end_snap="auto"), role="method_transition")

    # Control Center keeps gate state, artifact lifecycle and artifact provenance separate.
    table_cfg = scaffold.get("artifact_status_tables") or {}
    _upsert_system_item(
        mapping=mapping, operations=operations, client=client, board_id=board_id,
        dry_run=False, item_id="control-center:gate-state-title", item_type="text",
        payload=_text_payload(
            content=(
                f"<p><strong>{html.escape(str(table_cfg.get('project_gate_state_title_cs') or 'PROJECT / GATE STATE — LEGENDA'))}</strong></p>"
                "<p>Výsledek rozhodovacího bodu projektu; není to lifecycle artefaktu.</p>"
            ),
            x=0, y=-50, width=8000, font_size=18, parent_id=control_frame,
            text_align="center", color="#365A8C",
        ),
        frame_id="control-center", role="project_gate_state_title",
    )
    legend_positions = [-3200, -1600, 0, 1600, 3200]
    for index, state in enumerate(scaffold.get("gate_states") or []):
        _upsert_system_item(
            mapping=mapping, operations=operations, client=client, board_id=board_id,
            dry_run=False, item_id=f"legend:{state.get('id')}", item_type="shape",
            payload=_shape_payload(
                content=(
                    f"<p><strong>{html.escape(str(state.get('symbol') or '•'))} "
                    f"{html.escape(str(state.get('label_cs') or state.get('id')))}</strong></p>"
                    f"<p>{html.escape(str(state.get('meaning_cs') or ''))}</p>"
                ),
                x=legend_positions[index], y=390, width=1450, height=430,
                fill_color=str(state.get("fill_color") or "#FFFFFF"),
                font_size=float(minimum_fonts.get("gate_legend", 24)),
                parent_id=control_frame, border_color="#64748B", border_width=2,
            ),
            frame_id="control-center", role="gate_state_legend",
        )

    lifecycle_content = " · ".join(
        f"<strong>{html.escape(str(item.get('label_cs') or item.get('id')))}</strong>: "
        f"{html.escape(str(item.get('meaning_cs') or ''))}"
        for item in table_cfg.get("statuses") or []
    )
    _upsert_system_item(
        mapping=mapping, operations=operations, client=client, board_id=board_id,
        dry_run=False, item_id="artifact-registry:lifecycle-legend", item_type="shape",
        payload=_shape_payload(
            content=(
                f"<p><strong>{html.escape(str(table_cfg.get('lifecycle_title_cs') or 'ARTIFACT LIFECYCLE'))}</strong></p>"
                f"<p>{html.escape(str(table_cfg.get('lifecycle_legend_cs') or 'Zralost artefaktu.'))}</p>"
                f"<p>{lifecycle_content}</p>"
            ),
            x=0, y=1000, width=8200, height=650, fill_color="#EFF6FF",
            font_size=18, parent_id=control_frame, shape="rectangle",
            border_color="#2F7E95", border_width=2, text_align="left",
        ),
        frame_id="control-center", role="artifact_lifecycle_legend",
        managed=False, sync_policy="ignore",
    )
    provenance_content = " · ".join(
        f"<strong>{html.escape(str(item.get('label_cs') or item.get('id')))}</strong>: "
        f"{html.escape(str(item.get('meaning_cs') or ''))}"
        for item in table_cfg.get("provenance_values") or []
    )
    _upsert_system_item(
        mapping=mapping, operations=operations, client=client, board_id=board_id,
        dry_run=False, item_id="artifact-registry:provenance-legend", item_type="shape",
        payload=_shape_payload(
            content=(
                f"<p><strong>{html.escape(str(table_cfg.get('provenance_title_cs') or 'ARTIFACT PROVENANCE'))}</strong></p>"
                f"<p>{html.escape(str(table_cfg.get('provenance_legend_cs') or 'Původ projektového obsahu.'))}</p>"
                f"<p>{provenance_content}</p>"
            ),
            x=0, y=1660, width=8200, height=520, fill_color="#F5F3FF",
            font_size=18, parent_id=control_frame, shape="rectangle",
            border_color="#6D5AA7", border_width=2, text_align="left",
        ),
        frame_id="control-center", role="artifact_provenance_legend",
        managed=False, sync_policy="ignore",
    )
    _upsert_system_item(
        mapping=mapping, operations=operations, client=client, board_id=board_id,
        dry_run=False, item_id="artifact-registry:title", item_type="text",
        payload=_text_payload(
            content=(
                f"<p><strong>{html.escape(str(table_cfg.get('title_cs') or 'ARTIFACT REGISTRY'))}</strong></p>"
                "<p>Jedna projekce oddělující lifecycle a provenance. "
                "REST API v2 používá deterministický shape-grid, nikoli nativní Miro Table.</p>"
            ),
            x=0, y=2110, width=8200, font_size=18, parent_id=control_frame,
            text_align="center", color="#365A8C",
        ),
        frame_id="control-center", role="artifact_registry_title",
        managed=False, sync_policy="ignore",
    )

    artifacts = load_artifacts(config.root, config.artifact_root)
    artifacts = sorted(artifacts, key=lambda item: (item.stage, item.artifact_type, item.artifact_id))
    max_rows = int(table_cfg.get("max_artifact_rows", 4))
    registry_columns = table_cfg.get("registry_columns") or []
    total_weight = sum(float(column.get("width_weight", 1)) for column in registry_columns) or 1
    table_width = 8400.0
    left_edge = -table_width / 2
    header_y = 2480.0
    row_height = 300.0
    project_commit = str(context["status"].get("project_commit") or "UNCOMMITTED")
    last_sync = str(context.get("last_sync_at") or "NOT_SYNCED")
    rows: list[dict[str, str]] = []
    for artifact in artifacts[:max_rows]:
        try:
            detail = str(artifact.source_path.relative_to(config.root))
        except ValueError:
            detail = str(artifact.source_path)
        rows.append({
            "artifact": artifact.name,
            "type": artifact.artifact_type,
            "stage": artifact.stage,
            "lifecycle": _artifact_status_bucket(artifact.status, table_cfg).upper(),
            "provenance": _artifact_provenance(artifact, table_cfg).upper(),
            "owner": _artifact_owner(artifact),
            "revision": _artifact_revision(artifact, project_commit),
            "last_sync": last_sync,
            "detail": detail,
        })
    while len(rows) < max_rows:
        rows.append({str(column.get("id")): "—" for column in registry_columns})

    current_left = left_edge
    for column in registry_columns:
        column_id = str(column.get("id") or "")
        column_width = table_width * float(column.get("width_weight", 1)) / total_weight
        x = current_left + column_width / 2
        _upsert_system_item(
            mapping=mapping, operations=operations, client=client, board_id=board_id,
            dry_run=False, item_id=f"artifact-registry:header:{column_id}",
            item_type="shape", payload=_shape_payload(
                content=f"<p><strong>{html.escape(str(column.get('label_cs') or column_id))}</strong></p>",
                x=x, y=header_y, width=column_width, height=row_height,
                fill_color="#E0F2FE", font_size=18, parent_id=control_frame,
                shape="rectangle", border_color="#2F7E95", border_width=2,
            ),
            frame_id="control-center", role="artifact_registry_table",
            managed=False, sync_policy="ignore",
        )
        for row_index, row in enumerate(rows, start=1):
            _upsert_system_item(
                mapping=mapping, operations=operations, client=client, board_id=board_id,
                dry_run=False, item_id=f"artifact-registry:row:{row_index}:{column_id}",
                item_type="shape", payload=_shape_payload(
                    content=f"<p>{html.escape(str(row.get(column_id) or '—')[:72])}</p>",
                    x=x, y=header_y + row_index * row_height,
                    width=column_width, height=row_height,
                    fill_color="#FFFFFF" if row_index % 2 else "#F8FAFC",
                    font_size=18, parent_id=control_frame, shape="rectangle",
                    border_color="#94A3B8", border_width=1,
                    text_align="left", text_align_vertical="middle",
                ),
                frame_id="control-center", role="artifact_registry_table",
                managed=False, sync_policy="ignore",
            )
        current_left += column_width

    expected_item_ids={str(frame.get("miro_item_id")) for frame in (mapping.get("frames") or {}).values() if (frame or {}).get("miro_item_id")}
    expected_item_ids.update(str(entry.get("miro_item_id")) for entry in (mapping.get("items") or {}).values() if (entry or {}).get("system_item") and (entry or {}).get("item_type") != "connector" and (entry or {}).get("miro_item_id"))
    expected_connector_ids={str(entry.get("miro_item_id")) for entry in (mapping.get("items") or {}).values() if (entry or {}).get("system_item") and (entry or {}).get("item_type") == "connector" and (entry or {}).get("miro_item_id")}
    remote_items=_load_remote_items(client,board_id,expected_item_ids)
    remote_connectors=_load_remote_connectors(client,board_id,expected_connector_ids)
    remote_layout=validate_remote_layout(scaffold,mapping,remote_items,remote_connectors)
    mapping.update({"board_id":board_id,"scaffold_id":scaffold.get("id"),"scaffold_schema_version":scaffold.get("schema_version"),"rendered_at":utc_now(),"layout_contract_status":"PASS","remote_layout_status":remote_layout["status"],"remote_layout_evidence":remote_layout,"utf8_status":"PASS","human_visual_acceptance_status":"PENDING","overall_status":"PENDING_HUMAN_REVIEW","review_team_selection_status":"EXPLICIT_TEAM" if config.team_id else "DEFAULT_TOKEN_TEAM","developer_team_watermark_status":"EXTERNAL_ENVIRONMENT_NOT_RENDERED_BY_DDDA","traceability":scaffold.get("traceability") or []})
    assert_utf8_contract(mapping,label="Miro mapping")
    save_map(config.root,mapping)
    return {"project_id":config.project_id,"board_id":board_id,"dry_run":False,"operations":operations,"operation_count":len(operations),"technical_sync_status":"NOT_RUN","layout_contract_status":"PASS","remote_layout_status":remote_layout["status"],"remote_layout_evidence":remote_layout,"utf8_status":"PASS","human_visual_acceptance_status":"PENDING","overall_status":"PENDING_HUMAN_REVIEW","traceability_count":contract["traceability_count"],"current_gate":context["current_gate"],"review_team_selection_status":"EXPLICIT_TEAM" if config.team_id else "DEFAULT_TOKEN_TEAM","developer_team_watermark_status":"EXTERNAL_ENVIRONMENT_NOT_RENDERED_BY_DDDA"}
