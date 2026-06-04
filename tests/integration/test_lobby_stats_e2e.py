"""E2E: lobby stats reflect active games."""

import pytest

from tests.integration.helpers import (
    auth_headers,
    create_room,
    flush_redis,
    new_client_id,
    wait_game_started,
    ws_path,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _flush():
    flush_redis()
    yield
    flush_redis()


class TestLobbyStatsE2E:
    def test_active_games_increases_after_ai_start(self, client, auth_user_factory):
        user = auth_user_factory()
        cid = new_client_id()
        before = client.get(f"/rooms?client_id={cid}").json()["stats"]["active_games"]

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
            # active_games считает только комнаты с живым WS (не зомби в Redis)
            after = client.get(f"/rooms?client_id={cid}").json()["stats"]["active_games"]
            assert after >= before + 1
