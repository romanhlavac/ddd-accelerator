from __future__ import annotations

from copy import deepcopy

from ddda_miro.connector_readback_wirefix import (
    connector_contract_mismatches,
    same_connector_canonical,
    update_connector_with_fresh_readback,
)
from ddda_miro import connector_readback_wirefix as wirefix
from ddda_miro.miro_tips_endpoint_wirefix import readable_connector_payload_preserve_endpoint


class _ConnectorClient:
    def __init__(self):
        self.updated = []
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


def _black_callout():
    return {
        "startItem": {"id": "tip", "position": {"x": 0.5, "y": 0.5}},
        "endItem": {"id": "image", "position": {"x": 0.237, "y": 0.081}},
        "shape": "curved",
        "style": {
            "startStrokeCap": "none",
            "endStrokeCap": "stealth",
            "strokeColor": "#000000",
            "strokeStyle": "normal",
        },
        "captions": [],
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


def test_non_tutorial_connector_does_not_gain_endpoint_fidelity_gate():
    client = _ConnectorClient()
    drifted = deepcopy(client.full)
    drifted["endItem"]["position"] = {"x": 0.5, "y": 0.0}
    assert same_connector_canonical(drifted, _expected())


def test_black_miro_tips_callout_requires_exact_reference_attachment_points():
    expected = _black_callout()
    remote = deepcopy(expected)
    assert same_connector_canonical(remote, expected)
    remote["endItem"]["position"] = {"x": 0.5, "y": 0.0}
    assert not same_connector_canonical(remote, expected)
    remote = deepcopy(expected)
    remote["startItem"]["position"] = {"x": 1.0, "y": 0.5}
    assert not same_connector_canonical(remote, expected)
    remote["endItem"]["id"] = "wrong-screenshot"
    assert not same_connector_canonical(remote, expected)


def test_black_miro_tips_callout_normalizes_miro_percent_wire_coordinates():
    expected = _black_callout()
    remote = deepcopy(expected)
    remote["startItem"]["position"] = {"x": "50%", "y": "50%"}
    remote["endItem"]["position"] = {"x": "23.7%", "y": "8.1%"}
    assert same_connector_canonical(remote, expected)


def test_black_miro_tips_control_anchor_accepts_miro_edge_serialization_but_not_the_wrong_anchor():
    expected = _black_callout()
    expected["endItem"] = {"id": "transparent-control-anchor"}
    remote = deepcopy(expected)
    remote["endItem"] = {
        "id": "transparent-control-anchor",
        "position": {"x": "50%", "y": "0%"},
        "snapTo": "top",
    }
    assert same_connector_canonical(remote, expected)
    remote["endItem"]["id"] = "wrong-control-anchor"
    assert not same_connector_canonical(remote, expected)


def test_black_miro_tips_callout_reports_exact_rejected_endpoint_fields():
    expected = _black_callout()
    remote = deepcopy(expected)
    remote["startItem"].pop("position")
    remote["endItem"]["position"] = {"x": 0.5, "y": 0.0}
    assert connector_contract_mismatches(remote, expected) == [
        {
            "endpoint": "startItem",
            "expected": {"id": "tip", "position": {"x": 0.5, "y": 0.5}},
            "actual": {"id": "tip"},
        },
        {
            "endpoint": "endItem",
            "expected": {"id": "image", "position": {"x": 0.237, "y": 0.081}},
            "actual": {"id": "image", "position": {"x": 0.5, "y": 0.0}},
        },
    ]


def test_readable_connector_payload_preserves_complete_reference_endpoint_contract():
    source = {
        "startItem": {"id": "source-start", "position": {"x": 0.18, "y": 0.04}, "snapTo": "top"},
        "endItem": {"id": "source-end", "position": {"x": 0.81, "y": 0.92}, "snapTo": "bottom"},
        "shape": "curved",
        "style": {
            "strokeColor": "#000000",
            "startStrokeCap": "none",
            "endStrokeCap": "stealth",
        },
        "captions": [],
    }
    payload = readable_connector_payload_preserve_endpoint(source, "target-start", "target-end", {})
    assert payload["startItem"] == {
        "id": "target-start", "position": {"x": 0.18, "y": 0.04}, "snapTo": "top"
    }
    assert payload["endItem"] == {
        "id": "target-end", "position": {"x": 0.81, "y": 0.92}, "snapTo": "bottom"
    }


def test_readable_connector_payload_leaves_non_tutorial_connector_on_legacy_wire_contract():
    source = {
        "startItem": {"id": "source-start", "position": {"x": 0.18, "y": 0.04}, "snapTo": "top"},
        "endItem": {"id": "source-end", "position": {"x": 0.81, "y": 0.92}, "snapTo": "bottom"},
        "shape": "straight",
        "style": {"strokeColor": "#365A8C"},
        "captions": [{"content": "G1"}],
    }
    payload = readable_connector_payload_preserve_endpoint(source, "target-start", "target-end", {})
    assert payload["startItem"]["id"] == "target-start"
    assert payload["endItem"]["id"] == "target-end"


def test_runtime_wires_control_anchor_reconciliation_and_unwinds_it(monkeypatch):
    calls = []
    for module, label in (
        (wirefix.miro_tips_endpoint_wirefix, "endpoint"),
        (wirefix.miro_tips_hvr_fix, "tips"),
        (wirefix.miro_tips_hvr_semantic_fix, "semantic"),
        (wirefix.miro_tips_control_anchor_fix, "anchors"),
    ):
        monkeypatch.setattr(module, "install", lambda label=label: calls.append(f"install:{label}"))
        monkeypatch.setattr(module, "uninstall", lambda label=label: calls.append(f"uninstall:{label}"))
    monkeypatch.setattr(wirefix.recovery, "main", lambda argv: calls.append("reconcile") or 0)

    assert wirefix.main(["--fixture"]) == 0
    assert calls == [
        "install:endpoint",
        "install:tips",
        "install:semantic",
        "install:anchors",
        "reconcile",
        "uninstall:anchors",
        "uninstall:semantic",
        "uninstall:tips",
        "uninstall:endpoint",
    ]
