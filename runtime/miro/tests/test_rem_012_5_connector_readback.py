from __future__ import annotations

from copy import deepcopy

from ddda_miro import connector_readback_wirefix as wirefix
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


def test_runtime_wires_only_the_exact_reference_clone(monkeypatch):
    calls = []
    for module, label in (
        (wirefix.miro_tips_hvr_fix, "tips"),
        (wirefix.miro_tips_hvr_semantic_fix, "semantic"),
    ):
        monkeypatch.setattr(module, "install", lambda label=label: calls.append(f"install:{label}"))
        monkeypatch.setattr(module, "uninstall", lambda label=label: calls.append(f"uninstall:{label}"))
    monkeypatch.setattr(wirefix.recovery, "main", lambda argv: calls.append("reconcile") or 0)

    assert wirefix.main(["--fixture"]) == 0
    assert calls == [
        "install:tips",
        "install:semantic",
        "reconcile",
        "uninstall:semantic",
        "uninstall:tips",
    ]
