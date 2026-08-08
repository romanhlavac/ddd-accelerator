from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from .anchor_contract import (
    _close,
    _get_frame,
    _get_item,
    _patch,
    _protected_snapshot,
    _writable,
    canonical_miro_text,
)
from .anchor_evidence import _verify_no_anchor_overlap
from .client import MiroApiError, MiroClient, normalize_miro_font_size
from .image_transport import reconcile as reconcile_images
from .yamlio import load_yaml

REMEDIATION_ID = "REM-PR8-HVA-CC-012.3"
SUPPORTED_NATIVE_TYPES = {"shape", "text", "sticky_note"}
ENDPOINT = {"shape": "shapes", "text": "texts", "sticky_note": "sticky_notes"}


def _load(path: Path) -> dict[str, Any]:
    manifest = load_yaml(path.resolve())
    if not isinstance(manifest, dict) or manifest.get("remediation_id") != REMEDIATION_ID:
        raise ValueError("invalid REM-012.3 manifest")
    required = {
        "board_id", "source_board_id", "frames", "protected_frames", "updates",
        "images", "native_clones", "cleanup_ids", "project_registry",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise ValueError(f"REM-012.3 manifest missing fields: {missing}")
    if len(manifest["protected_frames"]) != 15:
        raise ValueError("REM-012.3 requires exactly 15 protected frames")
    if len(manifest["images"].get("assets") or []) != 17:
        raise ValueError("REM-012.3 requires exactly 17 managed images")
    if {str(item["name"]) for item in manifest["native_clones"]} != {"align-onboarding", "filled-bmc-example"}:
        raise ValueError("REM-012.3 native clone identity mismatch")
    manifest["_source_root"] = str(path.resolve().parents[2])
    return manifest


def _target_image_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    assets = []
    for item in manifest["images"]["assets"]:
        assets.append({
            "id": str(item["id"]),
            "usage": "REM-012.3 HVR readability remediation",
            "source": {
                "board_id": str(item["source_board_id"]),
                "frame_id": str(item["source_frame_id"]),
                "item_id": str(item["source_item_id"]),
                "title": str(item["id"]),
                "expected_sha256": str(item["expected_sha256"]),
            },
            "target": {
                "frame_id": str(item["target_frame"]),
                "position": {"x": float(item["x_centered"]), "y": float(item["y_centered"])},
                "width": float(item["width"]),
            },
        })
    return {
        "manifest_id": str(manifest["images"]["manifest_id"]),
        "diagnostic_only": False,
        "assets": assets,
    }


def _same_item(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    if str((remote.get("parent") or {}).get("id") or "") != str((expected.get("parent") or {}).get("id") or ""):
        return False
    for key, value in (expected.get("data") or {}).items():
        actual = (remote.get("data") or {}).get(key)
        if key in {"content", "title"}:
            if canonical_miro_text(actual) != canonical_miro_text(value):
                return False
        elif actual != value:
            return False
    for section in ("position", "geometry", "style"):
        actual = remote.get(section) or {}
        for key, value in (expected.get(section) or {}).items():
            if key in {"x", "y", "width", "height", "fontSize"}:
                if not _close(actual.get(key), value):
                    return False
            elif actual.get(key) != value:
                return False
    return True


def _sanitized_style(item_type: str, style: dict[str, Any], scale: float) -> dict[str, Any]:
    allowed = {
        "shape": {"fillColor", "fillOpacity", "fontFamily", "fontSize", "textAlign", "textAlignVertical", "color", "borderColor", "borderOpacity", "borderStyle", "borderWidth"},
        "text": {"fillColor", "fillOpacity", "fontFamily", "fontSize", "textAlign", "color"},
        "sticky_note": {"fillColor", "textAlign", "textAlignVertical"},
    }[item_type]
    result = {key: deepcopy(value) for key, value in style.items() if key in allowed}
    if item_type in {"shape", "text"} and result.get("fontSize") is not None:
        result["fontSize"] = normalize_miro_font_size(float(result["fontSize"]) * scale)
    if result.get("borderWidth") is not None:
        result["borderWidth"] = max(1.0, float(result["borderWidth"]) * scale)
    return result


def _native_payload(source: dict[str, Any], target_frame_id: str, clone: dict[str, Any]) -> dict[str, Any]:
    item_type = str(source["type"])
    scale = float(clone["scale"])
    source_position = source.get("position") or {}
    source_geometry = source.get("geometry") or {}
    x = float(clone["offset_x"]) + float(source_position.get("x") or 0) * scale
    y = float(clone["offset_y"]) + float(source_position.get("y") or 0) * scale
    data = deepcopy(source.get("data") or {})
    data = {key: value for key, value in data.items() if key in {"content", "shape"}}
    payload: dict[str, Any] = {
        "data": data,
        "position": {"x": x, "y": y, "origin": "center"},
        "parent": {"id": target_frame_id},
    }
    style = _sanitized_style(item_type, dict(source.get("style") or {}), scale)
    if style:
        payload["style"] = style
    if item_type == "sticky_note":
        payload["geometry"] = {"width": float(source_geometry["width"]) * scale}
    elif item_type == "text":
        payload["geometry"] = {"width": float(source_geometry["width"]) * scale}
    else:
        payload["geometry"] = {
            "width": float(source_geometry["width"]) * scale,
            "height": float(source_geometry["height"]) * scale,
        }
    return payload


def _position_identity(remote: dict[str, Any], expected: dict[str, Any]) -> bool:
    if str(remote.get("type") or "") not in SUPPORTED_NATIVE_TYPES:
        return False
    if str((remote.get("parent") or {}).get("id") or "") != str((expected.get("parent") or {}).get("id") or ""):
        return False
    actual_pos, expected_pos = remote.get("position") or {}, expected.get("position") or {}
    actual_geo, expected_geo = remote.get("geometry") or {}, expected.get("geometry") or {}
    return (
        _close(actual_pos.get("x"), expected_pos.get("x"))
        and _close(actual_pos.get("y"), expected_pos.get("y"))
        and _close(actual_geo.get("width"), expected_geo.get("width"))
    )


def _clone_native_set(client: MiroClient, manifest: dict[str, Any], clone: dict[str, Any]) -> dict[str, Any]:
    source_board = str(manifest["source_board_id"])
    target_board = str(manifest["board_id"])
    source_frame_id = str(clone["source_frame_id"])
    target_frame_id = str(manifest["frames"][str(clone["target_frame"])]["id"])
    source_items = [
        item for item in client.list_items(source_board)
        if str((item.get("parent") or {}).get("id") or "") == source_frame_id
        and str(item.get("type") or "") in SUPPORTED_NATIVE_TYPES
    ]
    expected_count = int(clone["expected_supported_count"])
    if len(source_items) != expected_count:
        raise ValueError(f"source clone {clone['name']} count mismatch: {len(source_items)} != {expected_count}")
    cleanup_ids = {str(item) for item in manifest.get("cleanup_ids") or []}
    target_items = [
        item for item in client.list_items(target_board)
        if str((item.get("parent") or {}).get("id") or "") == target_frame_id
        and str(item.get("type") or "") in SUPPORTED_NATIVE_TYPES
        and str(item.get("id") or "") not in cleanup_ids
    ]
    result = {"name": str(clone["name"]), "created": 0, "updated": 0, "unchanged": 0, "item_ids": [], "created_ids": []}
    for source in sorted(source_items, key=lambda item: str(item.get("id") or "")):
        item_type = str(source["type"])
        payload = _native_payload(source, target_frame_id, clone)
        exact = [item for item in target_items if item.get("type") == item_type and _same_item(item, payload)]
        if len(exact) > 1:
            raise ValueError(f"duplicate exact clones for source item {source['id']}")
        if exact:
            remote, action = exact[0], "unchanged"
        else:
            candidates = [item for item in target_items if item.get("type") == item_type and _position_identity(item, payload)]
            if len(candidates) > 1:
                raise ValueError(f"ambiguous clone target for source item {source['id']}")
            if candidates:
                remote = _patch(client, target_board, item_type, str(candidates[0]["id"]), payload)
                action = "updated"
                target_items[target_items.index(candidates[0])] = remote
            else:
                remote = client._request("POST", f"boards/{target_board}/{ENDPOINT[item_type]}", body=payload)
                action = "created"
                target_items.append(remote)
        if not _same_item(remote, payload):
            raise ValueError(f"native clone {source['id']} did not reach target")
        result[action] += 1
        result["item_ids"].append(str(remote["id"]))
        if action == "created":
            result["created_ids"].append(str(remote["id"]))
    if result["created"] + result["updated"] + result["unchanged"] != expected_count:
        raise ValueError(f"native clone reconciliation mismatch: {result}")
    return result


def _apply_update(client: MiroClient, board: str, frames: dict[str, str], update: dict[str, Any], snapshots: dict[str, Any]) -> str:
    item_id, item_type = str(update["id"]), str(update["type"])
    remote = _get_item(client, board, item_id)
    snapshots.setdefault(item_id, remote)
    target_frame = frames[str(update["frame"])]
    payload = _writable(remote)
    payload["parent"] = {"id": target_frame}
    payload["position"] = {"x": float(update["x"]), "y": float(update["y"]), "origin": "center"}
    if "content" in update:
        payload.setdefault("data", {})["content"] = str(update["content"])
    if "font_size" in update:
        payload.setdefault("style", {})["fontSize"] = int(update["font_size"])
    geometry = dict(payload.get("geometry") or {})
    if item_type == "sticky_note":
        if "width" in update:
            geometry = {"width": float(update["width"])}
        else:
            geometry = {"width": float(geometry["width"])}
    else:
        for key in ("width", "height"):
            if key in update:
                geometry[key] = float(update[key])
    if geometry:
        payload["geometry"] = geometry
    if _same_item(remote, payload):
        return "unchanged"
    updated = _patch(client, board, item_type, item_id, payload)
    if not _same_item(updated, payload):
        raise ValueError(f"managed update {item_id} did not reach target")
    return "updated"


def _verify_registry(manifest: dict[str, Any]) -> dict[str, Any]:
    root = Path(str(manifest["_source_root"]))
    spec = manifest["project_registry"]
    yaml_path = root / str(spec["yaml_path"])
    markdown_path = root / str(spec["markdown_path"])
    if not yaml_path.is_file() or not markdown_path.is_file():
        raise ValueError("project-owned Artifact Registry files are missing")
    registry = load_yaml(yaml_path)
    if not isinstance(registry, dict) or str(registry.get("project_id") or "") != str(spec["project_id"]):
        raise ValueError("project Artifact Registry identity mismatch")
    artifacts = registry.get("artifacts") or []
    expected_ids = [str(item) for item in spec["expected_artifact_ids"]]
    actual_ids = [str(item.get("id") or "") for item in artifacts]
    if actual_ids != expected_ids:
        raise ValueError(f"project Artifact Registry artifact mismatch: {actual_ids}")
    markdown_raw = markdown_path.read_bytes()
    digest = hashlib.sha256(markdown_raw).hexdigest()
    if digest != str(spec["markdown_sha256"]):
        raise ValueError(f"project Artifact Registry Markdown digest mismatch: {digest}")
    text = markdown_raw.decode("utf-8")
    for required in ("Project-owned source of truth", "ATTENTION", "does not approve a gate"):
        if required not in text:
            raise ValueError(f"project Artifact Registry Markdown missing: {required}")
    return {
        "status": "PASS",
        "project_id": str(spec["project_id"]),
        "yaml_path": str(spec["yaml_path"]),
        "markdown_path": str(spec["markdown_path"]),
        "markdown_sha256": digest,
        "artifact_count": len(artifacts),
    }


def _verify_control(client: MiroClient, manifest: dict[str, Any]) -> dict[str, Any]:
    board = str(manifest["board_id"])
    checks = manifest["control_verification"]
    text = " ".join(
        canonical_miro_text((item.get("data") or {}).get("content"))
        for item in client.list_items(board)
        if str((item.get("parent") or {}).get("id") or "") == str(manifest["frames"]["control"]["id"])
    )
    for phrase in checks["required_phrases"]:
        if str(phrase) not in text:
            raise ValueError(f"Control Center missing required phrase: {phrase}")
    for phrase in checks["forbidden_phrases"]:
        if str(phrase) in text:
            raise ValueError(f"Control Center retains forbidden phrase: {phrase}")
    return {"status": "PASS", "required_phrase_count": len(checks["required_phrases"])}


def _delete_if_present(client: MiroClient, board: str, item_id: str) -> str:
    try:
        _get_item(client, board, item_id)
    except MiroApiError as exc:
        if exc.status == 404:
            return "absent"
        raise
    client.delete_item(board, item_id)
    return "deleted"


def _rollback(client: MiroClient, board: str, snapshots: dict[str, Any], created_native: list[str], images_before: set[str], image_manifest_id: str) -> dict[str, Any]:
    errors: list[str] = []
    for item_id, snapshot in reversed(list(snapshots.items())):
        try:
            _patch(client, board, str(snapshot["type"]), item_id, _writable(snapshot))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"item {item_id}: {exc}")
    for item_id in reversed(created_native):
        try:
            client.delete_item(board, item_id)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"created native {item_id}: {exc}")
    try:
        for image in client.list_items(board, "image"):
            image_id = str(image.get("id") or "")
            title = canonical_miro_text((image.get("data") or {}).get("title"))
            if image_id not in images_before and title.startswith(f"DDDA-IMAGE:{image_manifest_id}:"):
                client.delete_item(board, image_id)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"managed images: {exc}")
    return {"status": "PASS" if not errors else "PARTIAL", "errors": errors}


def apply_remediation(client: MiroClient, manifest: dict[str, Any], source_sha: str | None = None) -> dict[str, Any]:
    board = str(manifest["board_id"])
    if source_sha and os.environ.get("GITHUB_SHA") and source_sha != os.environ["GITHUB_SHA"]:
        raise ValueError("source SHA does not match GITHUB_SHA")
    for key, spec in manifest["frames"].items():
        remote = _get_frame(client, board, str(spec["id"]))
        expected = spec["expected"]
        if not all((
            _close((remote.get("position") or {}).get("x"), expected["x"]),
            _close((remote.get("position") or {}).get("y"), expected["y"]),
            _close((remote.get("geometry") or {}).get("width"), expected["width"]),
            _close((remote.get("geometry") or {}).get("height"), expected["height"]),
        )):
            raise ValueError(f"anchor frame {key} is not at the REM-012.2 target state")
    protected_before = _protected_snapshot(client, board, [str(item) for item in manifest["protected_frames"]])
    registry = _verify_registry(manifest)
    frame_ids = {key: str(spec["id"]) for key, spec in manifest["frames"].items()}
    snapshots: dict[str, Any] = {}
    images_before = {str(item.get("id") or "") for item in client.list_items(board, "image")}
    created_native: list[str] = []
    irreversible = False
    try:
        updates = {"updated": 0, "unchanged": 0}
        for update in manifest["updates"]:
            updates[_apply_update(client, board, frame_ids, update, snapshots)] += 1

        image_manifest = _target_image_manifest(manifest)
        first_images = reconcile_images(client, board, frame_ids, image_manifest)
        second_images = reconcile_images(client, board, frame_ids, image_manifest)
        if second_images["created"] or second_images["updated"] or second_images["unchanged"] != 17:
            raise ValueError(f"managed image second reconcile is not zero mutation: {second_images}")

        first_clones = []
        for clone in manifest["native_clones"]:
            result = _clone_native_set(client, manifest, clone)
            first_clones.append(result)
            created_native.extend(result["created_ids"])
        second_clones = [_clone_native_set(client, manifest, clone) for clone in manifest["native_clones"]]
        for result in second_clones:
            if result["created"] or result["updated"] or result["unchanged"] != len(result["item_ids"]):
                raise ValueError(f"native clone second reconcile is not zero mutation: {result}")

        control = _verify_control(client, manifest)
        geometry = _verify_no_anchor_overlap(client, manifest)
        if _protected_snapshot(client, board, [str(item) for item in manifest["protected_frames"]])["digest"] != protected_before["digest"]:
            raise ValueError("protected frames changed before cleanup")

        irreversible = True
        deleted = {str(item): _delete_if_present(client, board, str(item)) for item in manifest["cleanup_ids"]}
        protected_after = _protected_snapshot(client, board, [str(item) for item in manifest["protected_frames"]])
        if protected_after["digest"] != protected_before["digest"]:
            raise ValueError("protected frames changed during cleanup")
        return {
            "status": "PASS",
            "remediation_id": REMEDIATION_ID,
            "source_sha": source_sha,
            "board_id": board,
            "updates": updates,
            "images": {"asset_count": 17, "first_run": first_images, "second_run": second_images},
            "native_clones": {"first_run": first_clones, "second_run": second_clones, "zero_mutation_second_run": True},
            "artifact_registry": registry,
            "control_center": control,
            "geometry": geometry,
            "deleted": deleted,
            "protected_frames": {
                "status": "PASS",
                "count": 15,
                "before_digest": protected_before["digest"],
                "after_digest": protected_after["digest"],
                "unchanged": True,
            },
            "technical_status": "PASS",
            "human_review_status": "PENDING",
            "overall_status": "READY_FOR_HUMAN_REVIEW",
        }
    except Exception as exc:
        rollback = {"status": "NOT_ATTEMPTED", "reason": "irreversible cleanup already started"} if irreversible else _rollback(
            client, board, snapshots, created_native, images_before, str(manifest["images"]["manifest_id"])
        )
        raise RuntimeError(f"REM-012.3 failed; rollback={rollback}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ddda_miro.hvr_remediation")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source-sha")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest = _load(args.manifest)
        report = apply_remediation(MiroClient(os.environ["MIRO_ACCESS_TOKEN"]), manifest, args.source_sha) if args.apply else {
            "status": "DRY_RUN",
            "remediation_id": REMEDIATION_ID,
            "board_id": manifest["board_id"],
            "managed_images": 17,
            "native_clone_count": sum(int(item["expected_supported_count"]) for item in manifest["native_clones"]),
        }
        code = 0
    except Exception as exc:  # noqa: BLE001
        report = {
            "status": "FAIL",
            "error": str(exc),
            "source_sha": args.source_sha,
            "technical_status": "FAIL",
            "human_review_status": "PENDING",
            "overall_status": "CHANGES_REQUIRED",
        }
        code = 1
        print(f"DDDA Miro HVR remediation error: {exc}", file=sys.stderr)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if code == 0:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
