from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .yamlio import load_yaml, save_yaml


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_map(project_root: Path, project_id: str, board_id: str | None) -> dict[str, Any]:
    path = project_root / "miro" / "miro-map.yaml"
    data = load_yaml(path) or {}
    data.setdefault("schema_version", 1)
    data.setdefault("project_id", project_id)
    data["board_id"] = board_id or data.get("board_id")
    data.setdefault("scaffold_id", "strategic-ddd-method-board")
    data.setdefault("frames", {})
    data.setdefault("items", {})
    return data


def save_map(project_root: Path, data: dict[str, Any]) -> None:
    data["updated_at"] = utc_now()
    save_yaml(project_root / "miro" / "miro-map.yaml", data)


def load_state(project_root: Path, project_id: str, board_id: str | None) -> dict[str, Any]:
    path = project_root / "miro" / "sync-state.yaml"
    data = load_yaml(path) or {}
    data.setdefault("schema_version", 1)
    data.setdefault("project_id", project_id)
    data["board_id"] = board_id or data.get("board_id")
    data.setdefault("items", {})
    return data


def save_state(project_root: Path, data: dict[str, Any]) -> None:
    data["last_sync_at"] = utc_now()
    save_yaml(project_root / "miro" / "sync-state.yaml", data)
