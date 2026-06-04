"""E2E: finished game appears in GET /api/auth/me/games."""

import pytest

from tests.db.conftest import db_scalar
from tests.integration.helpers import (
    auth_headers,
    create_room,
    finish_game,
    flush_redis,
    wait_game_started,
    ws_path,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _flush():
    flush_redis()
    yield
    flush_redis()


def _finish_ai_game(client, user) -> str:
    room_id = create_room(
        client,
        room_type="ai",
        client_id=user["client_id"],
        headers=auth_headers(user["access_token"]),
    )
    with client.websocket_connect(
        ws_path(room_id, user["client_id"], user["access_token"])
    ) as ws:
        wait_game_started(ws)
        finish_game(client, ws, room_id, db_scalar_fn=db_scalar)
    return room_id


class TestProfileGamesE2E:
    def test_ai_game_in_history(self, client, auth_user_factory):
        user = auth_user_factory()
        room_id = _finish_ai_game(client, user)
        r = client.get(
            "/api/auth/me/games",
            headers=auth_headers(user["access_token"]),
        )
        assert r.status_code == 200
        items = r.json()["items"]
        assert any(g["room_id"] == room_id for g in items)
        match = next(g for g in items if g["room_id"] == room_id)
        assert match["room_type"] == "ai"
        assert match["opponent_display"] == "__ai__"
