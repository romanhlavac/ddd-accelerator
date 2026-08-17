from __future__ import annotations

from ddda_miro.image_read_normalization_adapter import normalize_miro_image_titles


def test_normalizes_direct_image_title_html_entities():
    source = {
        "id": "image-1",
        "type": "image",
        "data": {"title": "DDDA-IMAGE:asset:sha256&#61;abc&amp;def", "imageUrl": "https://example.invalid/image"},
        "parent": {"id": "frame-1"},
    }

    normalized = normalize_miro_image_titles(source)

    assert normalized["data"]["title"] == "DDDA-IMAGE:asset:sha256=abc&def"
    assert normalized["data"]["imageUrl"] == source["data"]["imageUrl"]
    assert source["data"]["title"].endswith("abc&amp;def")


def test_normalizes_image_titles_inside_paginated_response_only():
    source = {
        "data": [
            {"id": "image-1", "type": "image", "data": {"title": "sha256&#61;abc"}},
            {"id": "text-1", "type": "text", "data": {"title": "keep&#61;encoded"}},
        ],
        "cursor": None,
    }

    normalized = normalize_miro_image_titles(source)

    assert normalized["data"][0]["data"]["title"] == "sha256=abc"
    assert normalized["data"][1]["data"]["title"] == "keep&#61;encoded"
    assert normalized["cursor"] is None
