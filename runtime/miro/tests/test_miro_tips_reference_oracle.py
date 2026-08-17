from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from ddda_miro import miro_tips_reference_oracle as oracle


ROOT = Path(__file__).resolve().parents[3]
FREEZE_COMMIT = "67805d87b4195379af5524494c4941926c9a1565"
FREEZE_AT = "2026-08-14T14:05:26Z"


def manifest(raw: bytes) -> dict:
    return {
        "miro_tips": {
            "reference_background_sha256": hashlib.sha256(raw).hexdigest(),
            "reference_freeze_commit": FREEZE_COMMIT,
            "reference_freeze_at": FREEZE_AT,
            "reference_frame_geometry": {"width": 1919.433, "height": 1079.681},
            "reference_text_font_size": 20,
        }
    }


def state() -> dict:
    items = [
        {"id": "image", "type": "image", "style": {}},
        *[
            {"id": f"text-{index}", "type": "text", "style": {"fontSize": 20}}
            for index in range(3)
        ],
    ]
    connectors = [
        {
            "id": f"connector-{index}",
            "shape": "curved",
            "endItem": {"id": "image", "position": {"x": 0.1 + index * 0.01, "y": 0.2}},
            "style": {
                "strokeColor": "#000000",
                "strokeStyle": "normal",
                "endStrokeCap": "stealth",
            },
        }
        for index in range(8)
    ]
    return {"items": items, "connectors": connectors}


class FakeClient:
    pass


def install(
    monkeypatch,
    raw: bytes,
    observed_state: dict,
    *,
    modified_at: str | None = "2026-08-14T14:05:25Z",
):
    monkeypatch.setattr(oracle, "_ORIGINAL_ASSERT_REFERENCE_IDENTITY", lambda *_args: None)
    monkeypatch.setattr(oracle.tips, "_config", lambda _manifest: {"reference_source_image_id": "image"})
    monkeypatch.setattr(oracle.tips, "_state", lambda *_args: deepcopy(observed_state))
    monkeypatch.setattr(
        oracle.base,
        "_get_frame",
        lambda *_args: {"geometry": {"width": 1919.433, "height": 1079.681}},
    )
    image = {"id": "image"}
    if modified_at is not None:
        image["modifiedAt"] = modified_at
    monkeypatch.setattr(
        oracle.image_transport,
        "source_image",
        lambda *_args: (raw, "image/png", deepcopy(image)),
    )


def test_versioned_scaffold_pins_reference_freeze_boundary():
    cfg = YAML(typ="safe").load(
        (ROOT / "scaffolds/miro/rem-012-5-frame-01.yaml").read_text(encoding="utf-8")
    )["miro_tips"]
    assert cfg["reference_source_board_id"] == "uXjVH2vcvRI="
    assert str(cfg["reference_source_frame_id"]) == "3458764679531043366"
    assert str(cfg["reference_source_image_id"]) == "3458764679531043367"
    assert cfg["reference_freeze_commit"] == FREEZE_COMMIT
    assert cfg["reference_freeze_at"] == FREEZE_AT
    assert cfg["reference_background_sha256"] == (
        "04b83ec7d9bc07ae31c7c11c03ec974ff4bde00d7773d7f9e55036e877f6fffd"
    )


def test_frozen_reference_oracle_accepts_the_approved_contract(monkeypatch):
    raw = b"approved-reference"
    observed = state()
    install(monkeypatch, raw, observed)
    oracle.assert_frozen_reference_identity(FakeClient(), "source", "frame", manifest(raw))


def test_frozen_reference_oracle_rejects_font_drift(monkeypatch):
    raw = b"approved-reference"
    observed = state()
    observed["items"][1]["style"]["fontSize"] = 24
    install(monkeypatch, raw, observed)
    with pytest.raises(ValueError, match="font size drifted"):
        oracle.assert_frozen_reference_identity(FakeClient(), "source", "frame", manifest(raw))


def test_frozen_reference_oracle_rejects_arrowhead_endpoint_drift(monkeypatch):
    raw = b"approved-reference"
    observed = state()
    observed["connectors"][0]["endItem"].pop("position")
    install(monkeypatch, raw, observed)
    with pytest.raises(ValueError, match="arrowhead endpoint drifted"):
        oracle.assert_frozen_reference_identity(FakeClient(), "source", "frame", manifest(raw))


def test_frozen_reference_oracle_accepts_miro_rendition_byte_drift_for_unchanged_pinned_image(monkeypatch):
    expected_snapshot = b"approved-reference"
    observed = state()
    install(monkeypatch, b"miro-reencoded-same-reference", observed)
    oracle.assert_frozen_reference_identity(
        FakeClient(), "source", "frame", manifest(expected_snapshot)
    )


def test_frozen_reference_oracle_rejects_image_modified_after_freeze(monkeypatch):
    expected_snapshot = b"approved-reference"
    observed = state()
    install(
        monkeypatch,
        b"changed-reference",
        observed,
        modified_at="2026-08-14T14:05:27Z",
    )
    with pytest.raises(ValueError, match="modified after reference freeze"):
        oracle.assert_frozen_reference_identity(
            FakeClient(), "source", "frame", manifest(expected_snapshot)
        )


def test_frozen_reference_oracle_rejects_missing_image_modified_at(monkeypatch):
    expected_snapshot = b"approved-reference"
    observed = state()
    install(monkeypatch, b"current-rendition", observed, modified_at=None)
    with pytest.raises(ValueError, match="modifiedAt is missing"):
        oracle.assert_frozen_reference_identity(
            FakeClient(), "source", "frame", manifest(expected_snapshot)
        )


def test_frozen_reference_oracle_still_rejects_unreadable_rendition(monkeypatch):
    expected_snapshot = b"approved-reference"
    observed = state()
    install(monkeypatch, b"", observed)
    with pytest.raises(ValueError, match="rendition is unreadable"):
        oracle.assert_frozen_reference_identity(
            FakeClient(), "source", "frame", manifest(expected_snapshot)
        )
