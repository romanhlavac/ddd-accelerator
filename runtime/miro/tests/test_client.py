from ddda_miro.client import MiroClient, normalize_miro_font_size, normalize_miro_percentage


def test_client_converts_child_position_using_cached_parent_geometry(monkeypatch):
    calls = []

    def fake_request(self, method, path, *, query=None, body=None):
        calls.append((method, path, body))
        if path.endswith("/frames"):
            return {"id": "frame-1", "geometry": {"width": 5000, "height": 3200}}
        return {"id": "text-1", **(body or {})}

    monkeypatch.setattr(MiroClient, "_request", fake_request)
    client = MiroClient("token")
    client.create_item(
        "board-1",
        "frame",
        {
            "data": {"title": "Control Center"},
            "position": {"x": -17500, "y": 0, "origin": "center"},
            "geometry": {"width": 5000, "height": 3200},
        },
    )
    authored = {
        "data": {"content": "Instructions"},
        "position": {"x": 0, "y": -250, "origin": "center"},
        "geometry": {"width": 4650},
        "parent": {"id": "frame-1"},
    }
    client.create_item("board-1", "text", authored)

    posted = calls[-1][2]
    assert posted["position"] == {"x": 2500.0, "y": 1350.0, "origin": "center"}
    assert authored["position"] == {"x": 0, "y": -250, "origin": "center"}
    assert not any(method == "GET" for method, _, _ in calls)


def test_client_fetches_parent_geometry_when_cache_is_empty(monkeypatch):
    calls = []

    def fake_request(self, method, path, *, query=None, body=None):
        calls.append((method, path, body))
        if method == "GET":
            return {"id": "frame-existing", "geometry": {"width": 5000, "height": 3200}}
        return {"id": "shape-1", **(body or {})}

    monkeypatch.setattr(MiroClient, "_request", fake_request)
    client = MiroClient("token")
    client.update_item(
        "board-1",
        "shape",
        "shape-1",
        {
            "data": {"content": "Legend"},
            "position": {"x": -1900, "y": 1200, "origin": "center"},
            "geometry": {"width": 850, "height": 550},
            "parent": {"id": "frame-existing"},
        },
    )

    assert calls[0][0] == "GET"
    assert calls[0][1].endswith("/frames/frame-existing")
    patched = calls[-1][2]
    assert patched["position"] == {"x": 600.0, "y": 2800.0, "origin": "center"}


def test_font_size_normalization_uses_supported_rest_scale():
    assert normalize_miro_font_size(20) == 24
    assert normalize_miro_font_size(24) == 24
    assert normalize_miro_font_size(26) == 36
    assert normalize_miro_font_size(34) == 36
    assert normalize_miro_font_size(500) == 288



def test_connector_caption_percentage_normalization_uses_rest_wire_format():
    assert normalize_miro_percentage(0) == "0%"
    assert normalize_miro_percentage(0.5) == "50%"
    assert normalize_miro_percentage(1) == "100%"
    assert normalize_miro_percentage("50.0%") == "50%"


def test_client_normalizes_text_font_size_before_api_call(monkeypatch):
    calls = []

    def fake_request(self, method, path, *, query=None, body=None):
        calls.append((method, path, body))
        return {"id": "text-1", **(body or {})}

    monkeypatch.setattr(MiroClient, "_request", fake_request)
    client = MiroClient("token")
    authored = {
        "data": {"content": "Readable heading"},
        "style": {"fontSize": 34, "fontFamily": "arial"},
        "position": {"x": 0, "y": 0, "origin": "center"},
        "geometry": {"width": 1200},
    }
    client.create_item("board-1", "text", authored)

    assert calls[-1][2]["style"]["fontSize"] == 36
    assert authored["style"]["fontSize"] == 34


def test_connector_api_uses_dedicated_endpoints_and_does_not_mutate_payload(monkeypatch):
    calls = []

    def fake_request(self, method, path, *, query=None, body=None):
        calls.append((method, path, query, body))
        if method == "GET":
            return {"data": [{"id": "connector-existing"}], "cursor": None}
        return {"id": "connector-1", **(body or {})}

    monkeypatch.setattr(MiroClient, "_request", fake_request)
    client = MiroClient("token")
    authored = {
        "startItem": {"id": "shape-1"},
        "endItem": {"id": "shape-2"},
        "shape": "elbowed",
        "captions": [{"content": "evidence → boundary", "position": 0.5}],
    }
    client.create_connector("board-1", authored)
    client.update_connector("board-1", "connector-1", authored)
    listed = client.list_connectors("board-1")
    client.delete_connector("board-1", "connector-1")

    assert calls[0][0:2] == ("POST", "boards/board-1/connectors")
    assert calls[0][3]["captions"][0]["position"] == "50%"
    assert calls[1][0:2] == ("PATCH", "boards/board-1/connectors/connector-1")
    assert calls[1][3]["captions"][0]["position"] == "50%"
    assert calls[2][0:2] == ("GET", "boards/board-1/connectors")
    assert calls[3][0:2] == ("DELETE", "boards/board-1/connectors/connector-1")
    assert listed == [{"id": "connector-existing"}]
    assert authored["captions"][0] == {"content": "evidence → boundary", "position": 0.5}
