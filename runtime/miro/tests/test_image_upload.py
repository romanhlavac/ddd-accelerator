import io
import urllib.error

import pytest

from ddda_miro.client import MiroApiError, MiroClient
from ddda_miro.image_upload import upload_image_resource


def test_upload_image_resource_uses_official_multipart_file_contract(monkeypatch):
    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"id":"image-1","type":"image"}'

    def fake_urlopen(request, timeout):
        requests.append(request)
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = MiroClient("token")
    result = upload_image_resource(
        client,
        "board-1",
        {
            "data": {"title": "Managed image", "url": "data:image/png;base64,ignored"},
            "position": {"x": 1400, "y": 950, "origin": "center"},
            "geometry": {"width": 2200},
            "parent": {"id": "frame-1"},
        },
        b"png-bytes",
        "image/png",
    )

    assert result == {"id": "image-1", "type": "image"}
    request = requests[0]
    assert request.method == "POST"
    assert request.full_url.endswith("/boards/board-1/images")
    assert request.headers["Content-type"].startswith("multipart/form-data; boundary=")
    body = request.data
    assert b'name="data"' in body
    assert b"application/json; charset=utf-8" in body
    assert b'"title":"Managed image"' in body
    assert b'{"data":' not in body
    assert b'"url"' not in body
    assert b'name="resource"; filename="managed-image.png"' in body
    assert b"Content-Type: image/png" in body
    assert b"png-bytes" in body


def test_upload_image_resource_rejects_unmapped_nested_image_data_fields(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: pytest.fail("network must not be called"))
    with pytest.raises(ValueError, match="Unsupported Miro multipart image data fields"):
        upload_image_resource(
            MiroClient("token"),
            "board-1",
            {"data": {"title": "x", "altText": "not-supported"}},
            b"x",
            "image/png",
        )


def test_upload_image_resource_rejects_unsupported_type_before_network(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: pytest.fail("network must not be called"))
    with pytest.raises(ValueError, match="Unsupported Miro image content type"):
        upload_image_resource(MiroClient("token"), "board-1", {"data": {"title": "x"}}, b"x", "text/plain")


def test_upload_image_resource_does_not_retry_non_idempotent_post_without_reconcile(monkeypatch):
    attempts = []

    def fake_urlopen(request, timeout):
        attempts.append(request)
        raise urllib.error.HTTPError(request.full_url, 500, "failure", {}, io.BytesIO(b'{}'))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(MiroApiError):
        upload_image_resource(MiroClient("token", max_retries=5), "board-1", {"data": {"title": "x"}}, b"x", "image/png")
    assert len(attempts) == 1


def test_installed_adapter_routes_data_url_image_write_to_multipart(monkeypatch):
    from ddda_miro.image_upload_adapter import install_image_upload_adapter

    requests = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"id":"image-2","type":"image"}'

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: requests.append(request) or Response())
    install_image_upload_adapter()
    result = MiroClient("token")._request(
        "POST",
        "boards/board-1/images",
        body={
            "data": {"title": "Managed", "url": "data:image/png;base64,cG5nLWJ5dGVz"},
            "geometry": {"width": 100},
        },
    )

    assert result == {"id": "image-2", "type": "image"}
    assert requests[0].headers["Content-type"].startswith("multipart/form-data; boundary=")
    assert b"png-bytes" in requests[0].data
    assert b'"url"' not in requests[0].data
