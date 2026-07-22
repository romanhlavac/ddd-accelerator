from __future__ import annotations

from typing import Any

from .client import MiroClient
from .config import ProjectConfig
from .state import load_map, save_map, utc_now
from .yamlio import load_yaml


def render_board(config: ProjectConfig, client: MiroClient | None, *, create_board: bool, dry_run: bool) -> dict[str, Any]:
    scaffold = load_yaml(config.scaffold_path)
    if not isinstance(scaffold, dict):
        raise ValueError(f"Invalid scaffold: {config.scaffold_path}")
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
                f"DDDA project {config.project_id}; managed through YAML and Git.",
                team_id=config.team_id,
                project_id=config.miro_project_id,
            )
            board_id = str(board["id"])
    mapping = load_map(config.root, config.project_id, board_id)
    palette = scaffold.get("palette") or {}
    for frame in scaffold.get("frames") or []:
        frame_id = str(frame["id"])
        entry = mapping["frames"].get(frame_id) or {}
        payload = {
            "data": {"title": str(frame.get("title_cs") or frame_id)},
            "style": {"fillColor": str(palette.get("frame_background") or "#F8FAFC")},
            "position": {"x": float(frame.get("x", 0)), "y": float(frame.get("y", 0)), "origin": "center"},
            "geometry": {"width": float(frame.get("width", 3000)), "height": float(frame.get("height", 2200))},
        }
        operations.append({"action": "update_frame" if entry.get("miro_item_id") else "create_frame", "frame_id": frame_id, "title": payload["data"]["title"]})
        if dry_run:
            continue
        assert client is not None and board_id is not None
        remote = client.update_item(board_id, "frame", str(entry["miro_item_id"]), payload) if entry.get("miro_item_id") else client.create_item(board_id, "frame", payload)
        remote_id = str(remote["id"])
        mapping["frames"][frame_id] = {"miro_item_id": remote_id, "stage": frame.get("stage"), "title": payload["data"]["title"], "updated_at": utc_now()}
        sections = frame.get("scaffold") or []
        text_id = f"{frame_id}:instructions"
        text_entry = mapping["items"].get(text_id) or {}
        checklist = "<p><strong>Cíl a pracovní oblasti</strong></p>" + "".join(f"<p>• {str(section).replace('_', ' ')}</p>" for section in sections)
        checklist += f"<p><small>DDDA-SCAFFOLD:{config.project_id}:{text_id}</small></p>"
        text_payload = {
            "data": {"content": checklist}, "position": {"x": 0, "y": 0, "origin": "center"},
            "geometry": {"width": max(800, float(frame.get("width", 3000)) - 300)}, "parent": {"id": remote_id},
        }
        text_remote = client.update_item(board_id, "text", str(text_entry["miro_item_id"]), text_payload) if text_entry.get("miro_item_id") else client.create_item(board_id, "text", text_payload)
        mapping["items"][text_id] = {"miro_item_id": str(text_remote["id"]), "item_type": "text", "frame_id": frame_id, "managed": True, "system_item": True, "updated_at": utc_now()}
    if not dry_run:
        mapping["board_id"] = board_id
        mapping["scaffold_id"] = scaffold.get("id")
        mapping["rendered_at"] = utc_now()
        save_map(config.root, mapping)
    return {"project_id": config.project_id, "board_id": board_id, "dry_run": dry_run, "operations": operations, "operation_count": len(operations)}
