from __future__ import annotations

from ddda_miro import miro_tips_anchor_payload_wirefix as wirefix
from ddda_miro import miro_tips_render_fidelity_fix as fidelity


def test_anchor_payload_wirefix_removes_api_illegal_font_size_and_restores_original():
    original = fidelity._anchor_payload
    wirefix.install()
    try:
        payload = fidelity._anchor_payload("tips-frame", 120.0, 80.0)
        assert payload["parent"] == {"id": "tips-frame"}
        assert payload["geometry"] == {"width": 8.0, "height": 8.0}
        assert payload["style"]["fillOpacity"] == 0.0
        assert payload["style"]["borderOpacity"] == 0.0
        assert "fontSize" not in payload["style"]
    finally:
        wirefix.uninstall()

    assert fidelity._anchor_payload is original
