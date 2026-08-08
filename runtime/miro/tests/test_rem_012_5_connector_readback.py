from __future__ import annotations

from ddda_miro.connector_readback_wirefix import (
    same_connector_canonical,
    update_connector_with_fresh_readback,
)


class _ConnectorClient:
    def __init__(self):
        self.updated = []
        self.full = {
            "id": "connector-1",
            "startItem": {"id": "start"},
            "endItem": {"id": "end"},
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
        "startItem": {"id": "start"},
        "endItem": {"id": "end"},
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


def test_connector_equality_keeps_readability_contract_strict():
    client = _ConnectorClient()
    client.full["style"]["fontSize"] = 14
    assert not same_connector_canonical(client.full, _expected())
    client.full["style"]["fontSize"] = 48
    client.full["style"]["textOrientation"] = "aligned"
    assert not same_connector_canonical(client.full, _expected())


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
