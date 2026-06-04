"""E2E: lobby polling GET /rooms → presence → admin online stats."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import pytest

from backend.presence import count_online_at
from backend.ws_manager import manager
from tests.db.conftest import db_scalar
from tests.integration.helpers import (
    auth_headers,
    create_room,
    finish_game,
    flush_redis,
    new_client_id,
    wait_game_started,
    ws_path,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def redis_flush_for_lobby_presence():
    flush_redis()
    yield
    flush_redis()


def _poll_lobby(client, client_id: str, headers: dict | None = None):
    hdrs = headers or {}
    r = client.get(f"/rooms?client_id={client_id}", headers=hdrs)
    assert r.status_code == 200, r.text
    return r.json()


def _admin_online(client, headers: dict, at: datetime | None = None) -> dict:
    moment = at or datetime.now(timezone.utc)
    qs = quote(moment.isoformat(), safe="")
    r = client.get(f"/api/admin/stats/online?at={qs}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


class TestLobbyPresenceOnline:
    def test_lobby_poll_counts_anonymous_online(self, client, admin_headers):
        client_id = "lobby-anon-1"
        _poll_lobby(client, client_id)

        body = _admin_online(client, admin_headers)
        assert body["total_unique"] == 1
        assert body["anonymous_unique"] == 1
        assert body["registered_unique"] == 0

    def test_lobby_poll_counts_registered_user(self, client, admin_headers, register_user):
        user = register_user("lobby_user")
        client_id = new_client_id()
        _poll_lobby(client, client_id, headers=auth_headers(user["access_token"]))

        body = _admin_online(client, admin_headers)
        assert body["total_unique"] == 1
        assert body["registered_unique"] == 1
        assert body["anonymous_unique"] == 0

    def test_left_lobby_presence_not_counted(self, client, admin_headers):
        client_id = "lobby-left"
        _poll_lobby(client, client_id)
        r = client.post(f"/rooms/presence/leave?client_id={client_id}")
        assert r.status_code == 200

        body = _admin_online(client, admin_headers)
        assert body["total_unique"] == 0

    def test_ws_connect_closes_lobby_session(self, client, admin_headers):
        client_id = new_client_id()
        _poll_lobby(client, client_id)

        room_id = create_room(client, room_type="ai", client_id=client_id)
        with client.websocket_connect(ws_path(room_id, client_id)) as ws:
            wait_game_started(ws)
            body = _admin_online(client, admin_headers)
            assert body["total_unique"] == 1
            assert body["anonymous_unique"] == 1

        manager.connections.pop(room_id, None)

        assert db_scalar(
            """
            SELECT COUNT(*) FROM presence_sessions
            WHERE client_id = %s AND room_id IS NULL AND disconnected_at IS NOT NULL
            """,
            (client_id,),
        ) == 1

    def test_same_user_two_lobby_tabs_counted_once(
        self, client, admin_headers, register_user
    ):
        user = register_user("lobby_dual")
        headers = auth_headers(user["access_token"])
        _poll_lobby(client, new_client_id(), headers=headers)
        _poll_lobby(client, new_client_id(), headers=headers)

        body = _admin_online(client, admin_headers)
        assert body["total_unique"] == 1
        assert body["registered_unique"] == 1

    @pytest.mark.asyncio
    async def test_count_online_at_includes_fresh_lobby_touch(self, client):
        client_id = "lobby-service"
        _poll_lobby(client, client_id)
        data = await count_online_at(datetime.now(timezone.utc) + timedelta(seconds=1))
        assert data["total_unique"] == 1
        assert data["anonymous_unique"] == 1

    def test_poll_without_client_id_does_not_create_presence(self, client, admin_headers):
        r = client.get("/rooms")
        assert r.status_code == 200

        body = _admin_online(client, admin_headers)
        assert body["total_unique"] == 0
