from __future__ import annotations

from ddda_miro import image_upload
from ddda_miro import multipart_image_read_normalization_adapter as adapter


def test_multipart_image_upload_normalizes_html_escaped_title_readback(monkeypatch):
    def raw_upload(*_args, **_kwargs):
        return {
            "id": "image-1",
            "type": "image",
            "data": {"title": "DDDA-MIRO-TIPS-ARROW-V5:shortcut:sha256&#61;abc123"},
        }

    monkeypatch.setattr(image_upload, "upload_image_resource", raw_upload)
    adapter.install_multipart_image_read_normalization_adapter()

    result = image_upload.upload_image_resource(None, "board", {}, b"png", "image/png")

    assert result["data"]["title"] == "DDDA-MIRO-TIPS-ARROW-V5:shortcut:sha256=abc123"
