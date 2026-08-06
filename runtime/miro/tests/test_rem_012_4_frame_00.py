from __future__ import annotations

from pathlib import Path

from ddda_miro import frame00_reconcile
from ddda_miro.anchor_contract import canonical_miro_text
from ddda_miro.frame00_control_center import (
    EXPECTED_ROLES,
    _matches,
    _selector_matches,
    _target_payload,
    load_contract,
)

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "scaffolds" / "miro" / "rem-012-4-frame-00.yaml"


def contract():
    return load_contract(MANIFEST)


def by_role(data):
    return {item["role"]: item for item in data["managed_updates"]}


def test_exact_scope_lineage_and_sources():
    data = contract()
    assert data["remediation_id"] == "REM-PR8-HVA-CC-012.4"
    assert data["authorized_base_sha"] == "cbc9963e13a1674e466cbceebfeff6f0b531a663"
    assert data["target_branch"] == "feat/project-steering-and-documentation"
    assert data["board_id"] == "uXjVH1phki0="
    assert data["frame"]["id"] == "3458764679756478046"
    assert len(data["protected_frame_ids"]) == 17
    assert data["frame"]["id"] not in data["protected_frame_ids"]
    assert {item["role"] for item in data["managed_updates"]} == EXPECTED_ROLES
    assert len({item["id"] for item in data["managed_updates"]}) == 8


def test_project_state_is_source_aligned_and_does_not_approve_g1():
    data = contract()
    state = data["project_state"]
    assert state["phase"] == "ALIGN"
    assert state["gate"] == "G1"
    assert state["gate_state"] == "NOT_READY"
    assert state["decision_owner_role"] == "Acceptance Business Owner"
    assert state["attention_count"] == 1
    assert state["blocker_count"] == 0
    assert "lidskému review" in state["next_action"]
    assert "PASSED" not in " ".join(canonical_miro_text(item["content"]) for item in data["managed_updates"])


def test_information_hierarchy_prioritizes_the_decision_over_artifact_health():
    items = by_role(contract())
    assert items["project_identity"]["y"] < items["decision_now"]["y"]
    assert items["decision_now"]["y"] < items["phase_gate_state"]["y"]
    assert items["attention_blockers"]["y"] < items["artifact_panel"]["y"]
    assert items["decision_now"]["font_size"] > items["artifact_status"]["font_size"]
    assert items["artifact_status"]["font_size"] > items["artifact_legend"]["font_size"]
    assert "ROZHODNUTÍ NYNÍ" in items["decision_now"]["content"]
    assert "OTEVŘÍT AKTUÁLNÍ FÁZI VE FRAMU 01" in items["decision_now"]["content"]


def test_attention_and_blockers_are_explicit_and_not_conflated():
    item = by_role(contract())["attention_blockers"]
    text = canonical_miro_text(item["content"])
    assert "🟧 ATTENTION — 1" in text
    assert "🟩 BLOCKERS — 0" in text
    assert "Postup není blokován" in text
    assert "HEALTH: ATTENTION" not in text


def test_artifact_health_is_one_wide_readable_panel_with_status_first():
    data = contract()
    items = by_role(data)
    panel = items["artifact_panel"]
    status = items["artifact_status"]
    legend = items["artifact_legend"]
    status_text = canonical_miro_text(status["content"])
    legend_text = canonical_miro_text(legend["content"])

    assert panel["type"] == "shape"
    assert status["type"] == legend["type"] == "text"
    assert sum(item["type"] == "shape" for item in (panel, status, legend)) == 1
    assert float(panel["width"]) >= 6000
    assert float(panel["width"]) / float(panel["height"]) >= 4
    assert int(status["font_size"]) >= 64
    assert int(legend["font_size"]) >= 48
    assert int(status["font_size"]) > int(legend["font_size"])
    assert float(status["y"]) < float(legend["y"])
    assert "ARTIFACT HEALTH — CURRENT STATUS" in status_text
    assert "1 SCAFFOLD · 2 WORKING" in status_text
    assert "ATTENTION 1" in status_text and "BLOCKERS 0" in status_text
    assert "MATURITY" in legend_text
    assert "ATTENTION / BLOCKING" in legend_text
    assert "SUPERSEDED 0" in legend_text
    assert "OTEVŘÍT PROJEKTOVÝ ARTIFACT REGISTRY" in legend_text
    assert "Project-owned Git/YAML je source of truth" in legend_text
    assert "Miro ani technický PASS neschvalují gate" in legend_text

    def bounds(item):
        width = float(item["width"])
        height = float(item.get("visual_height") or item.get("height") or 1)
        return (float(item["x"]) - width / 2, float(item["y"]) - height / 2,
                float(item["x"]) + width / 2, float(item["y"]) + height / 2)

    panel_box = bounds(panel)
    for item in (status, legend):
        box = bounds(item)
        assert panel_box[0] <= box[0] and panel_box[1] <= box[1]
        assert panel_box[2] >= box[2] and panel_box[3] >= box[3]
        assert int(item["font_size"]) >= 44

    assert data["artifact_health"]["total"] == 3
    assert data["artifact_health"]["lifecycle_counts"] == {
        "scaffold": 1,
        "working": 2,
        "candidate": 0,
        "validated": 0,
        "accepted": 0,
        "superseded": 0,
    }


def test_every_managed_item_stays_inside_frame_00():
    data = contract()
    width, height = float(data["frame"]["width"]), float(data["frame"]["height"])
    for item in data["managed_updates"]:
        visual_height = float(item.get("visual_height") or item.get("height") or 1)
        assert float(item["x"]) - float(item["width"]) / 2 >= 0
        assert float(item["x"]) + float(item["width"]) / 2 <= width
        assert float(item["y"]) - visual_height / 2 >= 0
        assert float(item["y"]) + visual_height / 2 <= height


def test_cleanup_is_specific_and_cannot_target_new_managed_items():
    data = contract()
    managed = {item["id"] for item in data["managed_updates"]}
    explicit = set(data["cleanup"]["explicit_item_ids"])
    assert not managed & explicit
    assert len(explicit) == 13
    assert all(int(item.get("max_matches") or 0) == 1 for item in data["cleanup"]["selectors"])
    assert all("type" in item and ("exact_text" in item or {"x", "y", "width", "height", "fill_color"} <= set(item)) for item in data["cleanup"]["selectors"])


def test_target_payload_and_readback_matching_for_existing_item():
    update = by_role(contract())["artifact_status"]
    remote = {
        "id": update["id"],
        "type": "text",
        "parent": {"id": "3458764679756478046"},
        "data": {"content": "old"},
        "style": {"color": "#000000", "fontSize": 24},
        "geometry": {"width": 1000},
        "position": {"x": 100, "y": 100, "origin": "center"},
    }
    payload = _target_payload(remote, update, "3458764679756478046")
    assert payload["style"]["fontSize"] == 64
    assert payload["geometry"] == {"width": 6000.0}
    reached = {**remote, **payload, "type": "text"}
    reached["style"] = {
        key: (value.lower() if key in {"fillColor", "borderColor", "color"} and isinstance(value, str) else value)
        for key, value in payload["style"].items()
    }
    assert _matches(reached, payload)


def test_sticky_note_does_not_promote_unmanaged_remote_style_into_target():
    update = by_role(contract())["phase_gate_state"]
    remote = {
        "id": update["id"],
        "type": "sticky_note",
        "parent": {"id": "3458764679756478046"},
        "data": {"shape": "rectangle", "content": "old"},
        "style": {"fillColor": "light_yellow", "textAlign": "center", "textAlignVertical": "middle"},
        "geometry": {"width": 1900, "height": 1237.7142857142858},
        "position": {"x": 1200, "y": 1850, "origin": "center", "relativeTo": "parent_top_left"},
    }
    payload = _target_payload(remote, update, "3458764679756478046")
    assert "style" not in payload
    assert payload["geometry"] == {"width": 1700.0}
    reached = {**remote, **payload, "type": "sticky_note"}
    reached["style"] = {"fillColor": "yellow", "textAlign": "left", "textAlignVertical": "top"}
    reached["geometry"] = {"width": 1700.0, "height": 1107.4285714285713}
    assert _matches(reached, payload)


def test_reconcile_verifies_persisted_get_not_patch_response(monkeypatch):
    frame_id = "frame-00"
    update = {
        "role": "test_text",
        "id": "item-1",
        "type": "text",
        "x": 500,
        "y": 300,
        "width": 900,
        "font_size": 36,
        "content": "<p>target</p>",
    }
    remote = {
        "id": "item-1",
        "type": "text",
        "parent": {"id": frame_id},
        "data": {"content": "<p>old</p>"},
        "style": {"fontSize": 24, "color": "#000000"},
        "geometry": {"width": 700},
        "position": {"x": 100, "y": 100, "origin": "center"},
    }
    payload = _target_payload(remote, update, frame_id)
    persisted = {**remote, **payload, "type": "text"}
    responses = iter([remote, persisted])
    monkeypatch.setattr(frame00_reconcile, "_get_item", lambda *args: next(responses))
    monkeypatch.setattr(frame00_reconcile, "_patch", lambda *args, **kwargs: {"id": "item-1"})

    class Client:
        @staticmethod
        def list_items(_board):
            return []

    result = frame00_reconcile.reconcile_once(
        Client(),
        {"board_id": "board", "frame": {"id": frame_id}, "managed_updates": [update], "cleanup": {}},
        {},
        [],
    )
    assert result == {"updated": 1, "unchanged": 0, "deleted": 0, "cleanup_absent": 0}


def test_cleanup_selector_requires_exact_generated_signature():
    selector = next(item for item in contract()["cleanup"]["selectors"] if item.get("exact_text") == "SCAFFOLD: 1")
    matching = {
        "type": "text",
        "data": {"content": "<p>SCAFFOLD: 1</p>"},
        "position": {"x": 1320, "y": 3400},
        "geometry": {"width": 600},
        "style": {},
    }
    assert _selector_matches(matching, selector)
    matching["position"]["x"] = 1600
    assert not _selector_matches(matching, selector)


def test_forbidden_legacy_guidance_is_not_reintroduced():
    data = contract()
    text = " ".join(canonical_miro_text(item["content"]) for item in data["managed_updates"])
    for phrase in data["verification"]["forbidden_phrases"]:
        assert phrase not in text
    assert "JAK ČÍST STAV GATE" not in text
    assert "PROVENANCE" not in text
