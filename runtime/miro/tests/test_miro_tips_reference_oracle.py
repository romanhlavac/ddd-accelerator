from __future__ import annotations

import hashlib
from copy import deepcopy

import pytest

from ddda_miro import miro_tips_reference_oracle as oracle


def manifest(raw: bytes) -> dict:
    return {
        "miro_tips": {
            "reference_background_sha256": hashlib.sha256(raw).hexdigest(),
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


def install(monkeypatch, raw: bytes, observed_state: dict):
    monkeypatch.setattr(oracle, "_ORIGINAL_ASSERT_REFERENCE_IDENTITY", lambda *_args: None)
    monkeypatch.setattr(oracle.tips, "_config", lambda _manifest: {"reference_source_image_id": "image"})
    monkeypatch.setattr(oracle.tips, "_state", lambda *_args: deepcopy(observed_state))
    monkeypatch.setattr(
        oracle.base,
        "_get_frame",
        lambda *_args: {"geometry": {"width": 1919.433, "height": 1079.681}},
    )
    monkeypatch.setattr(
        oracle.image_transport,
        "source_image",
        lambda *_args: (raw, "image/png", {"id": "image"}),
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


def test_frozen_reference_oracle_accepts_miro_rendition_byte_drift_for_same_pinned_image(monkeypatch):
    expected_snapshot = b"approved-reference"
    observed = state()
    install(monkeypatch, b"miro-reencoded-same-reference", observed)
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
