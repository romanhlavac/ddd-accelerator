from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .anchor_contract import _close, _writable, canonical_miro_text
from .yamlio import load_yaml

REMEDIATION_ID = "REM-PR8-HVA-CC-012.4"
EXPECTED_ROLES = {
    "project_identity", "decision_now", "phase_gate_state", "owner_next_action",
    "attention_blockers", "artifact_panel", "artifact_status", "artifact_legend",
}
SUPPORTED_TYPES = {"shape", "text", "sticky_note"}


def _aggregate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    states = {key: 0 for key in ("scaffold", "working", "candidate", "validated", "accepted", "superseded")}
    artifacts = list(registry.get("artifacts") or [])
    attention = blockers = 0
    for artifact in artifacts:
        state = str(artifact.get("lifecycle") or "").lower()
        if state not in states:
            raise ValueError(f"unsupported registry lifecycle: {state!r}")
        states[state] += 1
        attention += int(bool(artifact.get("attention")))
        blockers += int(bool(artifact.get("blocking")))
    return {"total": len(artifacts), "lifecycle_counts": states, "attention_count": attention, "blocker_count": blockers}


def _validate_bounds(item: dict[str, Any], width: float, height: float) -> None:
    x, y = float(item["x"]), float(item["y"])
    w = float(item["width"])
    h = float(item.get("visual_height") or item.get("height") or 1)
    if x - w / 2 < 0 or x + w / 2 > width or y - h / 2 < 0 or y + h / 2 > height:
        raise ValueError(f"managed role {item['role']} escapes frame 00")


def load_contract(path: Path) -> dict[str, Any]:
    path = path.resolve()
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError("REM-012.4 manifest must be a mapping")
    required = {
        "schema_version", "remediation_id", "authorized_base_sha", "target_branch", "board_id", "frame",
        "protected_frame_ids", "source_paths", "project_state", "artifact_health", "managed_updates", "cleanup", "verification",
    }
    missing = sorted(required - set(data))
    if missing or int(data.get("schema_version") or 0) != 1 or str(data.get("remediation_id") or "") != REMEDIATION_ID:
        raise ValueError(f"invalid REM-012.4 manifest; missing={missing}")
    if str(data["target_branch"]) != "feat/project-steering-and-documentation":
        raise ValueError("target branch mismatch")
    sha = str(data["authorized_base_sha"])
    if len(sha) != 40 or any(char not in "0123456789abcdef" for char in sha):
        raise ValueError("authorized base SHA is invalid")

    frame = data["frame"]
    protected = [str(item) for item in data["protected_frame_ids"]]
    if len(protected) != 17 or len(set(protected)) != 17 or str(frame["id"]) in protected:
        raise ValueError("frame 00 plus exactly 17 protected frames are required")
    updates = list(data["managed_updates"])
    roles = {str(item.get("role") or "") for item in updates}
    ids = [str(item.get("id") or "") for item in updates]
    if roles != EXPECTED_ROLES or len(updates) != 8 or len(set(ids)) != 8:
        raise ValueError("managed role/item identity mismatch")
    for item in updates:
        if str(item.get("type") or "") not in SUPPORTED_TYPES:
            raise ValueError(f"unsupported item type: {item.get('type')}")
        _validate_bounds(item, float(frame["width"]), float(frame["height"]))

    root = path.parents[2]
    sources = {key: root / str(value) for key, value in data["source_paths"].items()}
    missing_sources = sorted(key for key, value in sources.items() if not value.is_file())
    if missing_sources:
        raise ValueError(f"source files missing: {missing_sources}")
    registry = load_yaml(sources["project_registry"])
    if not isinstance(registry, dict) or str(registry.get("project_id") or "") != str(data["project_state"]["project_id"]):
        raise ValueError("project registry identity mismatch")
    actual = _aggregate_registry(registry)
    health = data["artifact_health"]
    expected = {
        "total": int(health["total"]),
        "lifecycle_counts": {key: int(value) for key, value in health["lifecycle_counts"].items()},
        "attention_count": int(health["attention_count"]),
        "blocker_count": int(health["blocker_count"]),
    }
    if actual != expected:
        raise ValueError(f"Artifact Health projection drift: {actual}")
    charter = next((item for item in registry.get("artifacts") or [] if str(item.get("id") or "") == "project-charter"), None)
    if not charter or str(charter.get("owner") or "") != str(data["project_state"]["decision_owner_role"]):
        raise ValueError("decision owner does not match project registry")

    text = " ".join(canonical_miro_text(item.get("content")) for item in updates)
    for phrase in data["verification"]["required_phrases"]:
        if str(phrase) not in text:
            raise ValueError(f"missing required phrase: {phrase}")
    for phrase in data["verification"]["forbidden_phrases"]:
        if str(phrase) in text:
            raise ValueError(f"forbidden phrase: {phrase}")
    cleanup_ids = {str(item) for item in data["cleanup"].get("explicit_item_ids") or []}
    if cleanup_ids & set(ids):
        raise ValueError("cleanup targets a new managed item")
    data["_root"] = str(root)
    return data


def _target_payload(remote: dict[str, Any], update: dict[str, Any], frame_id: str) -> dict[str, Any]:
    if str((remote.get("parent") or {}).get("id") or "") != frame_id:
        raise ValueError(f"item {remote.get('id')} is outside frame 00")
    item_type = str(update["type"])
    if str(remote.get("type") or "") != item_type:
        raise ValueError(f"item {remote.get('id')} type mismatch")
    payload = _writable(remote)
    payload["parent"] = {"id": frame_id}
    payload["position"] = {"x": float(update["x"]), "y": float(update["y"]), "origin": "center"}
    payload.setdefault("data", {})["content"] = str(update["content"])

    # Sticky-note presentation is intentionally unmanaged in REM-012.4 unless
    # the manifest declares it. Miro may normalize those style values during
    # PATCH/read-back, so inherited style must not become an accidental target.
    if item_type == "sticky_note":
        style = deepcopy(update.get("style") or {})
    else:
        style = dict(payload.get("style") or {})
        style.update(deepcopy(update.get("style") or {}))
    if "font_size" in update:
        style["fontSize"] = int(update["font_size"])
    if style:
        payload["style"] = style
    else:
        payload.pop("style", None)

    geometry = dict(payload.get("geometry") or {})
    geometry = {"width": float(update["width"])} if item_type == "sticky_note" else geometry
    geometry["width"] = float(update["width"])
    if item_type != "sticky_note" and "height" in update:
        geometry["height"] = float(update["height"])
    payload["geometry"] = geometry
    return payload


def _matches(remote: dict[str, Any], payload: dict[str, Any]) -> bool:
    if str((remote.get("parent") or {}).get("id") or "") != str((payload.get("parent") or {}).get("id") or ""):
        return False
    if canonical_miro_text((remote.get("data") or {}).get("content")) != canonical_miro_text((payload.get("data") or {}).get("content")):
        return False
    color_keys = {"fillColor", "borderColor", "color"}
    for section in ("position", "geometry", "style"):
        actual, expected = remote.get(section) or {}, payload.get(section) or {}
        for key, value in expected.items():
            if key in {"x", "y", "width", "height", "fontSize"}:
                if not _close(actual.get(key), value):
                    return False
            elif key in color_keys:
                # Miro normalizes hexadecimal colors to lowercase on read-back.
                if str(actual.get(key) or "").lower() != str(value or "").lower():
                    return False
            elif actual.get(key) != value:
                return False
    return True


def _selector_matches(item: dict[str, Any], selector: dict[str, Any]) -> bool:
    if str(item.get("type") or "") != str(selector["type"]):
        return False
    if "exact_text" in selector and canonical_miro_text((item.get("data") or {}).get("content")) != str(selector["exact_text"]):
        return False
    position, geometry, style = item.get("position") or {}, item.get("geometry") or {}, item.get("style") or {}
    for key in ("x", "y"):
        if key in selector and not _close(position.get(key), selector[key], tolerance=2.0):
            return False
    for key in ("width", "height"):
        if key in selector and not _close(geometry.get(key), selector[key], tolerance=2.0):
            return False
    return "fill_color" not in selector or str(style.get("fillColor") or "").upper() == str(selector["fill_color"]).upper()
