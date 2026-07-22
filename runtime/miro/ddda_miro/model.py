from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .yamlio import load_yaml, save_yaml

MARKER_RE = re.compile(r"DDDA:(?P<project>[a-z0-9-]+):(?P<artifact>[a-zA-Z0-9._:-]+)")

DEFAULT_ITEM_TYPES = {
    "domain_event": "sticky_note", "command": "sticky_note", "policy": "sticky_note",
    "procedure": "sticky_note", "hotspot": "sticky_note", "actor": "sticky_note",
    "external_system": "sticky_note", "read_model": "sticky_note",
    "bounded_context": "shape", "subdomain": "shape", "team": "shape",
    "decision": "shape", "note": "text", "text": "text",
}
PALETTE = {
    "domain_event": "#F6A04D", "command": "#86C5E8", "policy": "#C49ACD",
    "procedure": "#C49ACD", "read_model": "#C8E986", "external_system": "#F3B4C4",
    "actor": "#F4DC67", "hotspot": "#E84C3D", "bounded_context": "#DDEFA9",
    "subdomain": "#DDEFA9", "team": "#B7D7F0", "decision": "#F8E58C",
    "note": "#FFFFFF", "text": "#FFFFFF",
}


@dataclass(slots=True)
class ManagedArtifact:
    artifact_id: str
    artifact_type: str
    name: str
    description: str
    status: str
    stage: str
    source_path: Path
    document: Any
    item_type: str
    frame_id: str | None
    position: dict[str, Any]
    geometry: dict[str, Any]
    style: dict[str, Any]

    def semantic(self) -> dict[str, str]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "stage": self.stage,
        }

    def semantic_hash(self) -> str:
        raw = json.dumps(self.semantic(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def marker(self, project_id: str) -> str:
        return f"DDDA:{project_id}:{self.artifact_id}"

    def to_miro_content(self, project_id: str) -> str:
        description = html.escape(self.description).replace("\n", "<br>")
        parts = [f"<p><strong>{html.escape(self.name)}</strong></p>"]
        if description:
            parts.append(f"<p>{description}</p>")
        parts.extend([
            f"<p><small>Typ: {html.escape(self.artifact_type)}</small></p>",
            f"<p><small>Stav: {html.escape(self.status)}</small></p>",
            f"<p><small>Fáze: {html.escape(self.stage)}</small></p>",
            f"<p><small>{self.marker(project_id)}</small></p>",
        ])
        return "".join(parts)

    def to_miro_payload(self, project_id: str, *, parent_item_id: str | None = None, include_layout: bool = False) -> dict[str, Any]:
        if self.item_type == "frame":
            payload: dict[str, Any] = {"data": {"title": f"{self.name} [{self.marker(project_id)}]"}}
        else:
            payload = {"data": {"content": self.to_miro_content(project_id)}}
            if self.item_type == "sticky_note":
                payload["data"]["shape"] = "rectangle"
            if self.item_type == "shape":
                payload["data"]["shape"] = "round_rectangle"
        style = dict(self.style)
        if self.item_type in {"sticky_note", "shape", "frame"}:
            style.setdefault("fillColor", PALETTE.get(self.artifact_type, "#FFFFFF"))
        if style:
            payload["style"] = style
        if parent_item_id:
            payload["parent"] = {"id": parent_item_id}
        if include_layout:
            if self.position:
                payload["position"] = self.position
            if self.geometry:
                payload["geometry"] = self.geometry
        return payload


def _first(mapping: dict[str, Any], *names: str, default: Any = "") -> Any:
    for name in names:
        if name in mapping and mapping[name] is not None:
            return mapping[name]
    return default


def load_artifacts(project_root: Path, artifact_root: str) -> list[ManagedArtifact]:
    root = project_root / artifact_root
    if not root.exists():
        return []
    artifacts: list[ManagedArtifact] = []
    for path in sorted(root.rglob("*.yaml")) + sorted(root.rglob("*.yml")):
        if any(part in {"generated", "diagrams", ".ddda"} for part in path.parts):
            continue
        document = load_yaml(path)
        if not isinstance(document, dict):
            continue
        payload = document.get("artifact", document)
        if not isinstance(payload, dict):
            continue
        artifact_id = _first(payload, "id", "artifact_id")
        artifact_type = _first(payload, "type", "artifact_type")
        if not artifact_id or not artifact_type:
            continue
        miro = payload.get("miro") or document.get("miro") or {}
        item_type = miro.get("item_type") or DEFAULT_ITEM_TYPES.get(str(artifact_type), "sticky_note")
        artifacts.append(ManagedArtifact(
            artifact_id=str(artifact_id), artifact_type=str(artifact_type),
            name=str(_first(payload, "name", "title", "label", default=artifact_id)),
            description=str(_first(payload, "description", "content", "text", default="")),
            status=str(_first(payload, "status", default="candidate")),
            stage=str(_first(payload, "stage", default="discover")),
            source_path=path, document=document, item_type=str(item_type),
            frame_id=miro.get("frame_id"), position=dict(miro.get("position") or {}),
            geometry=dict(miro.get("geometry") or {}), style=dict(miro.get("style") or {}),
        ))
    return artifacts


def update_artifact_from_remote(artifact: ManagedArtifact, remote: dict[str, str]) -> None:
    payload = artifact.document.get("artifact", artifact.document)
    for key in ("name", "description", "status", "stage"):
        if key in remote:
            payload[key] = remote[key]
    save_yaml(artifact.source_path, artifact.document)


def create_artifact_from_remote(project_root: Path, artifact_root: str, remote: dict[str, str],
                                remote_item: dict[str, Any], frame_id: str | None) -> Path:
    artifact_id = str(remote.get("artifact_id") or "")
    artifact_type = str(remote.get("artifact_type") or "")
    stage = str(remote.get("stage") or "discover")
    if not artifact_id or not artifact_type:
        raise ValueError("A promoted Miro item requires artifact_id and artifact_type")
    safe_id = re.sub(r"[^a-zA-Z0-9._-]+", "-", artifact_id).strip("-")
    safe_type = re.sub(r"[^a-zA-Z0-9._-]+", "-", artifact_type).strip("-")
    safe_stage = re.sub(r"[^a-zA-Z0-9._-]+", "-", stage).strip("-") or "discover"
    path = project_root / artifact_root / safe_stage / safe_type / f"{safe_id}.yaml"
    if path.exists():
        raise ValueError(f"Promotion target already exists: {path}")
    item_type = str(remote_item.get("type") or DEFAULT_ITEM_TYPES.get(artifact_type, "sticky_note"))
    document: dict[str, Any] = {
        "artifact": {
            "id": artifact_id,
            "type": artifact_type,
            "name": str(remote.get("name") or artifact_id),
            "description": str(remote.get("description") or ""),
            "status": str(remote.get("status") or "candidate"),
            "stage": stage,
            "miro": {
                "item_type": item_type,
                "frame_id": frame_id,
            },
        }
    }
    save_yaml(path, document)
    return path


def semantic_hash(data: dict[str, Any]) -> str:
    selected = {key: str(data.get(key, "")) for key in ("artifact_id", "artifact_type", "name", "description", "status", "stage")}
    raw = json.dumps(selected, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def remote_semantic(item: dict[str, Any], project_id: str) -> dict[str, str] | None:
    data = item.get("data") or {}
    raw = str(data.get("content") or data.get("title") or "")
    marker = MARKER_RE.search(raw)
    if not marker or marker.group("project") != project_id:
        return None
    artifact_id = marker.group("artifact")
    text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result = {"artifact_id": artifact_id, "artifact_type": "", "name": lines[0] if lines else artifact_id,
              "description": "", "status": "candidate", "stage": "discover"}
    description_lines: list[str] = []
    for line in lines[1:]:
        if line.startswith("Typ:"):
            result["artifact_type"] = line.split(":", 1)[1].strip()
        elif line.startswith("Stav:"):
            result["status"] = line.split(":", 1)[1].strip()
        elif line.startswith("Fáze:"):
            result["stage"] = line.split(":", 1)[1].strip()
        elif not line.startswith("DDDA:"):
            description_lines.append(line)
    result["description"] = "\n".join(description_lines)
    return result
