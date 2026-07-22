from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import MiroClient
from .config import ProjectConfig
from .model import load_artifacts, remote_semantic, semantic_hash, update_artifact_from_remote
from .state import load_map, load_state, save_map, save_state, utc_now
from .yamlio import save_yaml


def _remote_index(items: list[dict[str, Any]], project_id: str) -> dict[str, tuple[dict[str, Any], dict[str, str]]]:
    result: dict[str, tuple[dict[str, Any], dict[str, str]]] = {}
    for item in items:
        semantic = remote_semantic(item, project_id)
        if semantic:
            result[semantic["artifact_id"]] = (item, semantic)
    return result


def _write_conflict(project_root: Path, artifact_id: str, local: dict[str, Any] | None, remote: dict[str, Any] | None,
                    base_local_hash: str | None, base_remote_hash: str | None, reason: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = project_root / "miro" / "conflicts" / f"{stamp}-{artifact_id}.yaml"
    save_yaml(path, {
        "schema_version": 1,
        "conflict_id": f"{stamp}-{artifact_id}",
        "artifact_id": artifact_id,
        "reason": reason,
        "base_local_hash": base_local_hash,
        "base_remote_hash": base_remote_hash,
        "local": local,
        "miro": remote,
        "resolution": "pending",
        "allowed_resolutions": ["accept_yaml", "accept_miro", "merge_manual", "supersede_artifact"],
    })
    return path


def _record_conflict(config: ProjectConfig, conflicts: list[str], *, artifact_id: str,
                     local: dict[str, Any] | None, remote: dict[str, Any] | None,
                     base_local_hash: str | None, base_remote_hash: str | None,
                     reason: str, dry_run: bool) -> None:
    if dry_run:
        conflicts.append(f"miro/conflicts/<timestamp>-{artifact_id}.yaml")
        return
    path = _write_conflict(
        config.root, artifact_id, local, remote, base_local_hash, base_remote_hash, reason,
    )
    conflicts.append(str(path.relative_to(config.root)))


def sync_project(config: ProjectConfig, client: MiroClient, *, direction: str, dry_run: bool, include_layout: bool,
                 confirm_delete: bool, recreate_missing: bool = False) -> dict[str, Any]:
    if not config.board_id:
        raise ValueError("Miro board ID is required for synchronization")
    if config.synchronization == "disabled":
        raise ValueError("project.yaml has miro.synchronization: disabled")
    artifacts = load_artifacts(config.root, config.artifact_root)
    local_by_id = {artifact.artifact_id: artifact for artifact in artifacts}
    mapping = load_map(config.root, config.project_id, config.board_id)
    state = load_state(config.root, config.project_id, config.board_id)
    remote_by_id = _remote_index(client.list_items(config.board_id), config.project_id)
    operations: list[dict[str, Any]] = []
    conflicts: list[str] = []
    ids = sorted(set(local_by_id) | set(remote_by_id) | set(mapping["items"]) | set(state["items"]))

    for artifact_id in ids:
        artifact = local_by_id.get(artifact_id)
        remote_pair = remote_by_id.get(artifact_id)
        remote_item = remote_pair[0] if remote_pair else None
        remote_data = remote_pair[1] if remote_pair else None
        entry = state["items"].get(artifact_id) or {}
        map_entry = mapping["items"].get(artifact_id) or {}
        if map_entry.get("system_item"):
            continue
        base_local_hash, base_remote_hash = entry.get("local_hash"), entry.get("remote_hash")
        local_hash = artifact.semantic_hash() if artifact else None
        remote_hash = semantic_hash(remote_data) if remote_data else None
        local_changed = local_hash is not None and local_hash != base_local_hash
        remote_changed = remote_hash is not None and remote_hash != base_remote_hash

        if artifact and artifact.status == "deleted_pending":
            if remote_item and confirm_delete:
                operations.append({"action": "delete_remote", "artifact_id": artifact_id})
                if not dry_run:
                    client.delete_item(config.board_id, str(remote_item["id"]))
                    mapping["items"].pop(artifact_id, None)
                    state["items"].pop(artifact_id, None)
            elif remote_item:
                operations.append({"action": "delete_pending", "artifact_id": artifact_id})
            else:
                operations.append({"action": "tombstone_without_remote", "artifact_id": artifact_id})
            continue

        if not artifact and map_entry.get("yaml_path"):
            operations.append({"action": "conflict", "artifact_id": artifact_id, "reason": "mapped_local_artifact_missing"})
            _record_conflict(
                config, conflicts, artifact_id=artifact_id, local=None, remote=remote_data,
                base_local_hash=base_local_hash, base_remote_hash=base_remote_hash,
                reason="mapped YAML artifact is missing; restore it or create an explicit tombstone",
                dry_run=dry_run,
            )
            continue

        if artifact and not remote_item and map_entry.get("miro_item_id") and not recreate_missing:
            operations.append({"action": "conflict", "artifact_id": artifact_id, "reason": "mapped_remote_item_missing"})
            _record_conflict(
                config, conflicts, artifact_id=artifact_id, local=artifact.semantic(), remote=None,
                base_local_hash=base_local_hash, base_remote_hash=base_remote_hash,
                reason="mapped Miro item is missing or inaccessible; use explicit recreate after review",
                dry_run=dry_run,
            )
            continue

        if local_changed and remote_changed and local_hash != remote_hash:
            operations.append({"action": "conflict", "artifact_id": artifact_id, "reason": "concurrent_semantic_change"})
            _record_conflict(
                config, conflicts, artifact_id=artifact_id,
                local=artifact.semantic() if artifact else None, remote=remote_data,
                base_local_hash=base_local_hash, base_remote_hash=base_remote_hash,
                reason="semantic fields changed in YAML and Miro since common base",
                dry_run=dry_run,
            )
            continue

        if direction in {"pull", "both"} and remote_data and (remote_changed or not artifact):
            if artifact:
                operations.append({"action": "pull_update_yaml", "artifact_id": artifact_id})
                if not dry_run:
                    update_artifact_from_remote(artifact, remote_data)
                    artifact = next(item for item in load_artifacts(config.root, config.artifact_root) if item.artifact_id == artifact_id)
                    local_by_id[artifact_id] = artifact
                    local_hash = artifact.semantic_hash()
                    local_changed = False
            else:
                operations.append({"action": "pull_unmapped_requires_promotion", "artifact_id": artifact_id})
                continue

        if direction in {"push", "both"} and artifact and (local_changed or not remote_item):
            parent_id = (mapping["frames"].get(artifact.frame_id) or {}).get("miro_item_id") if artifact.frame_id else None
            payload = artifact.to_miro_payload(
                config.project_id,
                parent_item_id=parent_id,
                include_layout=include_layout or remote_item is None,
            )
            if remote_item:
                operations.append({"action": "push_update_miro", "artifact_id": artifact_id})
                if not dry_run:
                    remote_item = client.update_item(config.board_id, artifact.item_type, str(remote_item["id"]), payload)
            else:
                operations.append({"action": "push_create_miro", "artifact_id": artifact_id})
                if not dry_run:
                    remote_item = client.create_item(config.board_id, artifact.item_type, payload)
            if not dry_run and remote_item:
                remote_data = remote_semantic(remote_item, config.project_id) or artifact.semantic()
                remote_hash = semantic_hash(remote_data)
                mapping["items"][artifact_id] = {
                    "miro_item_id": str(remote_item["id"]),
                    "item_type": artifact.item_type,
                    "yaml_path": str(artifact.source_path.relative_to(config.root)).replace("\\", "/"),
                    "frame_id": artifact.frame_id,
                    "managed": True,
                    "updated_at": utc_now(),
                }

        if artifact and remote_data and not dry_run:
            current_local_hash = artifact.semantic_hash()
            current_remote_hash = semantic_hash(remote_data)
            if current_local_hash == current_remote_hash:
                state["items"][artifact_id] = {
                    "local_hash": current_local_hash,
                    "remote_hash": current_remote_hash,
                    "miro_item_id": str((remote_item or {}).get("id") or map_entry.get("miro_item_id") or ""),
                    "yaml_path": str(artifact.source_path.relative_to(config.root)).replace("\\", "/"),
                    "synced_at": utc_now(),
                }

    if not dry_run:
        save_map(config.root, mapping)
        save_state(config.root, state)
        report = {
            "schema_version": 1,
            "project_id": config.project_id,
            "board_id": config.board_id,
            "direction": direction,
            "completed_at": utc_now(),
            "operations": operations,
            "conflicts": conflicts,
        }
        report_path = config.root / "reports" / "miro-sync" / f"sync-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.yaml"
        save_yaml(report_path, report)
    return {
        "project_id": config.project_id,
        "board_id": config.board_id,
        "direction": direction,
        "dry_run": dry_run,
        "operations": operations,
        "operation_count": len(operations),
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
    }
