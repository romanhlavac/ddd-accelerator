from __future__ import annotations

from copy import deepcopy

from ddda_miro import miro_tips_full_arrow_fidelity_fix as full


def _connector(connector_id: str, start: dict, end: dict) -> dict:
    return {
        "id": connector_id,
        "startItem": deepcopy(start),
        "endItem": deepcopy(end),
        "shape": "curved",
        "style": {
            "strokeColor": "#000000",
            "strokeStyle": "normal",
            "startStrokeCap": "none",
            "endStrokeCap": "stealth",
        },
    }


def test_reference_connector_classifier_includes_all_eleven_visible_arrows():
    image_id = "image"
    sticky_ids = {f"sticky-{index}" for index in range(8)}
    text_ids = {f"text-{index}" for index in range(3)}
    child_ids = sticky_ids | text_ids | {image_id}
    connectors = [
        _connector(
            f"image-{index}",
            {"id": f"sticky-{index}", "position": {"x": 0.5, "y": 0.5}},
            {"id": image_id, "position": {"x": 0.1 + index * 0.1, "y": 0.2}},
        )
        for index in range(8)
    ]
    connectors.extend(
        _connector(
            f"text-{index}",
            {"id": f"text-{index}", "position": {"x": 0.0, "y": 0.5}},
            {"position": {"x": 0.03, "y": 0.25 + index * 0.1}},
        )
        for index in range(3)
    )
    # An unrelated connector elsewhere on the board must not enter the frame contract.
    connectors.append(_connector("outside", {"id": "other-a"}, {"id": "other-b"}))

    classified = full.classify_reference_connectors(
        connectors, child_ids, image_id, text_ids
    )

    assert len(classified["all"]) == 11
    assert len(classified["direct_image"]) == 8
    assert len(classified["text"]) == 3
    assert {row["id"] for row in classified["text"]} == {
        "text-0",
        "text-1",
        "text-2",
    }


def test_routing_proxy_matches_screenshot_geometry_and_is_invisible():
    image = {
        "position": {"x": 960.0, "y": 540.0},
        "geometry": {"width": 1919.433, "height": 1079.681},
    }
    payload = full._routing_proxy_payload("frame", image)

    assert payload["parent"] == {"id": "frame"}
    assert payload["position"]["x"] == 960.0
    assert payload["position"]["y"] == 540.0
    assert payload["geometry"] == image["geometry"]
    assert payload["style"]["fillOpacity"] == 0.0
    assert payload["style"]["borderOpacity"] == 0.0

    remote = deepcopy(payload)
    remote["id"] = "proxy"
    remote["type"] = "shape"
    assert full.is_routing_proxy(remote, "frame")
    assert full.is_control_artifact(remote, "frame")
    assert full._same_routing_proxy(remote, "frame", image)


def test_direct_screenshot_endpoint_is_rebound_to_same_geometry_proxy():
    source_image = {
        "id": "source-image",
        "position": {"x": 960.0, "y": 540.0},
        "geometry": {"width": 1919.433, "height": 1079.681},
    }
    endpoint = {
        "id": "source-image",
        "position": {"x": "25%", "y": "10%"},
    }
    mapped = full._mapped_endpoint(
        endpoint,
        {},
        {"source-image": source_image},
        source_image,
        "routing-proxy",
    )
    assert mapped == {
        "id": "routing-proxy",
        "position": {"x": 0.25, "y": 0.10},
    }


def test_loose_text_arrow_endpoint_is_rebound_to_proxy_instead_of_being_dropped():
    source_image = {
        "id": "source-image",
        "position": {"x": 960.0, "y": 540.0},
        "geometry": {"width": 1900.0, "height": 1000.0},
    }
    mapped = full._mapped_endpoint(
        {"position": {"x": 0.04, "y": 0.35}},
        {"text": "target-text"},
        {"source-image": source_image},
        source_image,
        "routing-proxy",
    )
    assert mapped == {
        "id": "routing-proxy",
        "position": {"x": 0.04, "y": 0.35},
    }


def test_hvr_compatibility_wrapper_validates_eleven_before_returning_legacy_field():
    class Legacy:
        def __init__(self):
            self.calls = []

        def _assert_connector_copy(self, source, target, mapping):
            self.calls.append((source, target, mapping))
            assert len(source) == len(target)
            return len(target)

    legacy = Legacy()
    # Reset module-level install guard only inside this isolated fake-module test.
    old_installed = full._HVR_INSTALLED
    old_original = full._HVR_ASSERT_ORIGINAL
    full._HVR_INSTALLED = False
    full._HVR_ASSERT_ORIGINAL = None
    try:
        full.install_hvr_contract(legacy)
        assert legacy._assert_connector_copy([{}] * 11, [{}] * 11, {}) == 8
        assert legacy._assert_connector_copy([{}] * 8, [{}] * 8, {}) == 8
    finally:
        full._HVR_INSTALLED = old_installed
        full._HVR_ASSERT_ORIGINAL = old_original
