from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .yamlio import load_yaml


@dataclass(slots=True)
class ProjectConfig:
    root: Path
    platform_root: Path
    raw: dict[str, Any]
    project_id: str
    name: str
    artifact_root: str
    board_id: str | None
    board_id_env: str | None
    token_env: str
    team_id: str | None
    miro_project_id: str | None
    scaffold_path: Path
    conflict_policy: str
    synchronization: str

    @classmethod
    def load(cls, root: Path, platform_root: Path | None = None) -> "ProjectConfig":
        root = root.resolve()
        resolved_platform_root = platform_root.resolve() if platform_root else root
        raw = load_yaml(root / "project.yaml")
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid or missing project.yaml in {root}")
        project = raw.get("project") or {}
        miro = raw.get("miro") or {}
        artifacts = raw.get("artifacts") or {}
        project_id = str(project.get("id") or "")
        if not project_id:
            raise ValueError("project.yaml: project.id is required")
        board_id_env = miro.get("board_id_env")
        board_id = miro.get("board_id") or (os.environ.get(str(board_id_env)) if board_id_env else None)
        if not board_id:
            local_map = load_yaml(root / "miro" / "miro-map.yaml") or {}
            if isinstance(local_map, dict):
                board_id = local_map.get("board_id")
        token_env = str(miro.get("access_token_env") or "MIRO_ACCESS_TOKEN")
        team_id = miro.get("team_id") or (os.environ.get(str(miro.get("team_id_env"))) if miro.get("team_id_env") else None)
        miro_project_id = miro.get("project_id") or (os.environ.get(str(miro.get("project_id_env"))) if miro.get("project_id_env") else None)
        scaffold = Path(str(miro.get("scaffold") or "scaffolds/miro/strategic-ddd-method-board.yaml"))
        if not scaffold.is_absolute():
            scaffold = resolved_platform_root / scaffold
        return cls(
            root=root,
            platform_root=resolved_platform_root,
            raw=raw,
            project_id=project_id,
            name=str(project.get("name") or project_id),
            artifact_root=str(artifacts.get("root") or "artifacts"),
            board_id=str(board_id) if board_id else None,
            board_id_env=str(board_id_env) if board_id_env else None,
            token_env=token_env,
            team_id=str(team_id) if team_id else None,
            miro_project_id=str(miro_project_id) if miro_project_id else None,
            scaffold_path=scaffold,
            conflict_policy=str(artifacts.get("conflict_policy") or "manual-review"),
            synchronization=str(miro.get("synchronization") or "disabled"),
        )

    def access_token(self) -> str:
        token = os.environ.get(self.token_env)
        if not token:
            raise ValueError(f"Miro access token is missing. Set environment variable {self.token_env}.")
        return token
