from __future__ import annotations

from ddda_miro import connector_readback_wirefix as wirefix
from ddda_miro import miro_tips_exact_font_wirefix as fontfix
from ddda_miro.connector_readback_wirefix import (
    connector_contract_mismatches,
    same_connector_canonical,
    update_connector_with_fresh_readback,
)


class _ConnectorClient:
    def __init__(self):
        self.full = {
            "id": "connector-1",
            "startItem": {"id": "start", "position": {"x": 1.0, "y": 0.5}},
            "endItem": {"id": "end", "position": {"x": 0.237, "y": 0.081}},
            "shape": "straight",
            "style": {
                "startStrokeCap": "none",
                "endStrokeCap": "stealth",
                "strokeColor": "#365A8C",
                "strokeStyle": "normal",
                "strokeWidth": 2,
                "fontSize": "48",
                "color": "#1A1A1A",
                "textOrientation": "horizontal",
            },
            "captions": [{"content": "G1 · lidské rozhodnutí", "position": "0.5"}],
        }

    def list_connectors(self, board_id):
        assert board_id == "target"
        return [self.full]


def _expected():
    return {
        "startItem": {"id": "start", "position": {"x": 1.0, "y": 0.5}},
        "endItem": {"id": "end", "position": {"x": 0.237, "y": 0.081}},
        "shape": "straight",
        "style": {
            "startStrokeCap": "none",
            "endStrokeCap": "stealth",
            "strokeColor": "#365a8c",
            "strokeStyle": "normal",
            "strokeWidth": 2,
            "fontSize": 48,
            "color": "#1a1a1a",
            "textOrientation": "horizontal",
        },
        "captions": [{"content": "G1 · lidské rozhodnutí", "position": "50%"}],
    }


def test_connector_equality_canonicalizes_percentage_numeric_font_and_hex_case():
    client = _ConnectorClient()
    assert same_connector_canonical(client.full, _expected())


def test_connector_equality_keeps_authored_attachment_points_strict():
    client = _ConnectorClient()
    client.full["endItem"]["position"] = {"x": 0.5, "y": 0.0}
    assert not same_connector_canonical(client.full, _expected())
    assert connector_contract_mismatches(client.full, _expected())[0]["endpoint"] == "endItem"


def test_update_connector_uses_fresh_readback_not_patch_response(monkeypatch):
    client = _ConnectorClient()
    calls = []

    def partial_patch(self, board_id, connector_id, payload):
        calls.append((board_id, connector_id, payload))
        return {"id": connector_id}

    monkeypatch.setattr(
        "ddda_miro.connector_readback_wirefix._ORIGINAL_UPDATE_CONNECTOR",
        partial_patch,
    )
    remote = update_connector_with_fresh_readback(
        client, "target", "connector-1", _expected()
    )
    assert calls and calls[0][0:2] == ("target", "connector-1")
    assert remote == client.full
    assert same_connector_canonical(remote, _expected())


def test_connector_endpoint_percentage_wire_values_preserve_the_same_arrow_target():
    client = _ConnectorClient()
    client.full["startItem"]["position"] = {"x": "100%", "y": "50%"}
    client.full["endItem"]["position"] = {"x": "23.7%", "y": "8.1%"}
    assert same_connector_canonical(client.full, _expected())


def test_exact_miro_tips_font_wirefix_preserves_reference_font_20(monkeypatch):
    source = {
        "type": "text",
        "parent": {"id": fontfix.REFERENCE_FRAME_ID},
        "style": {"fontSize": 20},
    }
    monkeypatch.setattr(
        fontfix,
        "_ORIGINAL_ITEM_PAYLOAD",
        lambda _source, target: {"parent": {"id": target}, "style": {"fontSize": 24}},
    )
    payload = fontfix.exact_reference_item_payload(source, "target")
    assert payload["style"]["fontSize"] == 20

    source["parent"] = {"id": "other-frame"}
    payload = fontfix.exact_reference_item_payload(source, "target")
    assert payload["style"]["fontSize"] == 24


def test_runtime_wires_exact_reference_oracles_before_reconciliation(monkeypatch):
    calls = []
    monkeypatch.setattr(
        wirefix.miro_tips_exact_font_wirefix, "install", lambda: calls.append("install:font")
    )
    monkeypatch.setattr(
        wirefix.miro_tips_reference_oracle, "install", lambda: calls.append("install:oracle")
    )
    monkeypatch.setattr(
        wirefix.miro_tips_hvr_fix, "install", lambda: calls.append("install:exact-reference")
    )
    monkeypatch.setattr(
        wirefix.miro_tips_hvr_fix, "uninstall", lambda: calls.append("uninstall:exact-reference")
    )
    monkeypatch.setattr(
        wirefix.miro_tips_reference_oracle, "uninstall", lambda: calls.append("uninstall:oracle")
    )
    monkeypatch.setattr(
        wirefix.miro_tips_exact_font_wirefix, "uninstall", lambda: calls.append("uninstall:font")
    )
    monkeypatch.setattr(wirefix.recovery, "main", lambda argv: calls.append("reconcile") or 0)

    assert wirefix.main(["--fixture"]) == 0
    assert calls == [
        "install:font",
        "install:oracle",
        "install:exact-reference",
        "reconcile",
        "uninstall:exact-reference",
        "uninstall:oracle",
        "uninstall:font",
    ]
