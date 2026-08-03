from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .client import MiroClient
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


def run_probe(config: ProjectConfig, client: MiroClient, path: Path, *, keep_board: bool = False) -> dict[str, Any]:
    manifest = load_manifest(path)
    board_id: str | None = None
    report: dict[str, Any] | None = None
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
            remote = client.create_item(board_id, "frame", {"data": {"title": str(frame["title"])}, "position": {**frame["position"], "origin": "center"}, "geometry": frame["geometry"]})
            frames[str(frame["id"])] = str(remote["id"])
        first = reconcile(client, board_id, frames, manifest)
        second = reconcile(client, board_id, frames, manifest)
        first_ids = {a["asset_id"]: a["target_item_id"] for a in first["assets"]}
        second_ids = {a["asset_id"]: a["target_item_id"] for a in second["assets"]}
        expected = len(manifest["assets"])
        if first["created"] != expected or second["created"] or second["updated"] or second["unchanged"] != expected or first_ids != second_ids:
            raise ValueError("image transport second run was not a stable zero-mutation reconcile")
        report = {"status": "PASS", "manifest_id": manifest["manifest_id"], "board_id": board_id, "asset_count": expected, "first_run": first, "second_run": second, "stable_item_ids": True, "cleanup": {"state": "pending"}}
    finally:
        if board_id and not keep_board:
            client._request("DELETE", f"boards/{board_id}")
    if report is None:
        raise AssertionError("image transport probe produced no report")
    report["cleanup"] = {"state": "preserved" if keep_board else "deleted"}
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
        print(json.dumps(run_probe(config, MiroClient(config.access_token()), args.manifest.resolve(), keep_board=args.keep_board), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"DDDA Miro image probe error: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
