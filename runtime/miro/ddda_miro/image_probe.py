from __future__ import annotations

import argparse
import json
import time
import urllib.parse
from pathlib import Path
from typing import Any

from .client import MiroApiError, MiroClient
from .config import ProjectConfig
from .image_transport import reconcile
from .yamlio import load_yaml


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = load_yaml(path)
    if not isinstance(manifest, dict) or int(manifest.get("schema_version") or 0) != 1:
        raise ValueError("image transport manifest schema_version must be 1")
    if not manifest.get("manifest_id") or not manifest.get("frames") or not manifest.get("assets"):
        raise ValueError("image transport manifest is incomplete")
    frame_ids = {str(frame["id"]) for frame in manifest["frames"]}
    if len(frame_ids) != len(manifest["frames"]):
        raise ValueError("image transport frame ids must be unique")
    asset_ids: set[str] = set()
    for asset in manifest["assets"]:
        asset_id = str(asset.get("id") or "")
        if not asset_id or asset_id in asset_ids:
            raise ValueError("image transport asset ids must be unique and non-empty")
        if str(asset["target"]["frame_id"]) not in frame_ids:
            raise ValueError(f"asset {asset_id} targets an unknown frame")
        if float(asset["target"]["width"]) <= 0:
            raise ValueError(f"asset {asset_id} width must be positive")
        asset_ids.add(asset_id)
    return manifest


def _get_item(client: MiroClient, board_id: str, item_id: str) -> dict[str, Any]:
    board_segment = urllib.parse.quote(board_id, safe="")
    item_segment = urllib.parse.quote(item_id, safe="")
    return client._request("GET", f"boards/{board_segment}/items/{item_segment}")


def _verify_remote_images(
    client: MiroClient,
    board_id: str,
    frame_ids: dict[str, str],
    manifest: dict[str, Any],
    reconcile_result: dict[str, Any],
) -> dict[str, Any]:
    assets_by_id = {str(asset["id"]): asset for asset in manifest["assets"]}
    verified: list[dict[str, Any]] = []
    for evidence in reconcile_result["assets"]:
        asset_id = str(evidence["asset_id"])
        asset = assets_by_id[asset_id]
        target_item_id = str(evidence["target_item_id"])
        remote = _get_item(client, board_id, target_item_id)
        remote_type = str(remote.get("type") or "")
        expected_parent = frame_ids[str(asset["target"]["frame_id"])]
        remote_parent = str((remote.get("parent") or {}).get("id") or "")
        expected_title = (
            f"DDDA-IMAGE:{manifest['manifest_id']}:{asset_id}:sha256={evidence['sha256']}"
        )
        remote_title = str((remote.get("data") or {}).get("title") or "")
        source = asset["source"]

        if remote_type != "image":
            raise ValueError(f"remote target {target_item_id} for {asset_id} is {remote_type!r}, not 'image'")
        if remote_parent != expected_parent:
            raise ValueError(f"remote target parent mismatch for {asset_id}")
        if remote_title != expected_title:
            raise ValueError(f"remote semantic title/digest mismatch for {asset_id}")
        if (
            str(evidence["source_board_id"]) != str(source["board_id"])
            or str(evidence["source_frame_id"]) != str(source["frame_id"])
            or str(evidence["source_item_id"]) != str(source["item_id"])
        ):
            raise ValueError(f"remote provenance evidence mismatch for {asset_id}")

        verified.append(
            {
                "asset_id": asset_id,
                "target_item_id": target_item_id,
                "remote_type": remote_type,
                "target_parent_id": remote_parent,
                "semantic_title": remote_title,
                "sha256": str(evidence["sha256"]),
                "source_board_id": str(source["board_id"]),
                "source_frame_id": str(source["frame_id"]),
                "source_item_id": str(source["item_id"]),
            }
        )

    if len(verified) != len(manifest["assets"]):
        raise ValueError("remote image verification count does not match the manifest")
    return {
        "status": "PASS",
        "item_count": len(verified),
        "all_remote_types": "image",
        "exact_provenance": True,
        "digest_identity": True,
        "items": verified,
    }


def _delete_board_and_verify(client: MiroClient, board_id: str) -> dict[str, Any]:
    board_segment = urllib.parse.quote(board_id, safe="")
    client._request("DELETE", f"boards/{board_segment}")
    for attempt in range(10):
        try:
            client.get_board(board_id)
        except MiroApiError as exc:
            if exc.status == 404:
                return {"state": "deleted", "verified": True, "attempts": attempt + 1}
            raise
        if attempt < 9:
            time.sleep(1.0)
    raise ValueError(f"diagnostic board {board_id} still exists after cleanup")


def run_probe(config: ProjectConfig, client: MiroClient, path: Path, *, keep_board: bool = False) -> dict[str, Any]:
    manifest = load_manifest(path)
    board_id: str | None = None
    report: dict[str, Any] | None = None
    cleanup: dict[str, Any] = {"state": "not_created", "verified": False}
    try:
        board = client.create_board(
            str(manifest["board"]["name"]),
            str(manifest["board"]["description"]),
            team_id=config.team_id,
            project_id=config.miro_project_id,
        )
        board_id = str(board["id"])
        frames: dict[str, str] = {}
        for frame in manifest["frames"]:
            remote = client.create_item(
                board_id,
                "frame",
                {
                    "data": {"title": str(frame["title"])},
                    "position": {**frame["position"], "origin": "center"},
                    "geometry": frame["geometry"],
                },
            )
            frames[str(frame["id"])] = str(remote["id"])

        first = reconcile(client, board_id, frames, manifest)
        first_remote = _verify_remote_images(client, board_id, frames, manifest, first)
        second = reconcile(client, board_id, frames, manifest)
        second_remote = _verify_remote_images(client, board_id, frames, manifest, second)
        first_ids = {a["asset_id"]: a["target_item_id"] for a in first["assets"]}
        second_ids = {a["asset_id"]: a["target_item_id"] for a in second["assets"]}
        expected = len(manifest["assets"])
        if (
            first["created"] != expected
            or second["created"]
            or second["updated"]
            or second["unchanged"] != expected
            or first_ids != second_ids
        ):
            raise ValueError("image transport second run was not a stable zero-mutation reconcile")

        report = {
            "status": "PASS",
            "manifest_id": manifest["manifest_id"],
            "board_id": board_id,
            "asset_count": expected,
            "first_run": first,
            "second_run": second,
            "remote_verification": {
                "status": "PASS",
                "first_run": first_remote,
                "second_run": second_remote,
            },
            "stable_item_ids": True,
            "zero_mutation_second_run": True,
            "cleanup": {"state": "pending", "verified": False},
        }
    finally:
        if board_id:
            cleanup = (
                {"state": "preserved", "verified": False}
                if keep_board
                else _delete_board_and_verify(client, board_id)
            )
    if report is None:
        raise AssertionError("image transport probe produced no report")
    report["cleanup"] = cleanup
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ddda_miro.image_probe")
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--platform", type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--keep-board", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = ProjectConfig.load(args.project, args.platform)
        print(
            json.dumps(
                run_probe(
                    config,
                    MiroClient(config.access_token()),
                    args.manifest.resolve(),
                    keep_board=args.keep_board,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(f"DDDA Miro image probe error: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
