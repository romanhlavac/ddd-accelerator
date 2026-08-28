from __future__ import annotations

from ddda_miro.cli import BOARD_IDENTITY_HANDOFF_PREFIX, _BoardIdentityHandoffClient


class _FakeClient:
    def __init__(self):
        self.calls = []

    def create_board(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return {"id": "uXjV-ImmediateHandoff="}

    def get_board(self, board_id):
        return {"id": board_id}


def test_create_board_proxy_emits_identity_immediately(capsys):
    inner = _FakeClient()
    client = _BoardIdentityHandoffClient(inner)

    board = client.create_board("name", "description", team_id="team")

    assert board["id"] == "uXjV-ImmediateHandoff="
    assert len(inner.calls) == 1
    assert capsys.readouterr().err.strip() == (
        f"{BOARD_IDENTITY_HANDOFF_PREFIX}uXjV-ImmediateHandoff="
    )


def test_proxy_delegates_non_create_calls():
    client = _BoardIdentityHandoffClient(_FakeClient())
    assert client.get_board("uXjV-Existing=") == {"id": "uXjV-Existing="}
