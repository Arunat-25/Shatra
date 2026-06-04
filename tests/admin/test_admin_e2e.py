"""E2E: действия через API/WS → отражение в admin stats."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import pytest

from backend.ws_manager import manager
from tests.admin.conftest import backdate_finished_game, set_user_created_at
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
def redis_flush_for_admin_e2e():
    flush_redis()
    yield
    flush_redis()


def _admin_get(client, path: str, headers: dict) -> dict:
    r = client.get(path, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _finish_ai_game(client, client_id: str, *, headers: dict | None = None) -> str:
    room_id = create_room(
        client,
        room_type="ai",
        client_id=client_id,
        headers=headers or {},
    )
    token = None
    if headers and headers.get("Authorization", "").startswith("Bearer "):
        token = headers["Authorization"].removeprefix("Bearer ")
    with client.websocket_connect(ws_path(room_id, client_id, token)) as ws:
        wait_game_started(ws)
        finish_game(client, ws, room_id, db_scalar_fn=db_scalar)
    return room_id


class TestAdminRegistrationsE2E:
    """Регистрация через POST /api/auth/register → GET /api/admin/stats/registrations."""

    def test_periods_reflect_signups_at_different_times(
        self, client, admin_headers, register_user
    ):
        now = datetime.now(timezone.utc)

        register_user("reg_recent")
        reg_2h = register_user("reg_two_hours")
        reg_old = register_user("reg_month_ago")
        set_user_created_at(reg_2h["user"]["id"], now - timedelta(hours=2))
        set_user_created_at(reg_old["user"]["id"], now - timedelta(days=20))

        # adminuser + reg_recent в последний час
        assert _admin_get(
            client, "/api/admin/stats/registrations?period=1h", admin_headers
        )["total"] == 2

        # + reg_two_hours (2 ч назад)
        assert _admin_get(
            client, "/api/admin/stats/registrations?period=3h", admin_headers
        )["total"] == 3

        # reg_month_ago вне 7d
        assert _admin_get(
            client, "/api/admin/stats/registrations?period=7d", admin_headers
        )["total"] == 3
        assert _admin_get(
            client, "/api/admin/stats/registrations?period=30d", admin_headers
        )["total"] == 4

    def test_custom_from_to_window_counts_single_signup(
        self, client, admin_headers, register_user
    ):
        now = datetime.now(timezone.utc)
        reg = register_user("reg_window")
        set_user_created_at(reg["user"]["id"], now - timedelta(hours=5))

        start = quote((now - timedelta(hours=6)).isoformat(), safe="")
        end = quote((now - timedelta(hours=4)).isoformat(), safe="")
        body = _admin_get(
            client,
            f"/api/admin/stats/registrations?from={start}&to={end}",
            admin_headers,
        )
        assert body["total"] == 1

    def test_empty_period_after_signups_outside_window(
        self, client, admin_headers, register_user
    ):
        now = datetime.now(timezone.utc)
        reg = register_user("reg_outside")
        set_user_created_at(reg["user"]["id"], now - timedelta(days=40))

        assert _admin_get(
            client, "/api/admin/stats/registrations?period=7d", admin_headers
        )["total"] == 1  # только adminuser


class TestAdminGamesE2E:
    """REST → WS → archive → GET /api/admin/stats/games."""

    def test_archived_games_appear_in_stats_by_period_and_filters(
        self, client, admin_headers, register_user
    ):
        now = datetime.now(timezone.utc)
        user = register_user("game_player")
        headers = auth_headers(user["access_token"])
        client_id = new_client_id()

        room_recent = _finish_ai_game(client, client_id, headers=headers)
        room_anon = _finish_ai_game(client, new_client_id())
        backdate_finished_game(room_anon, now - timedelta(hours=10))

        body = _admin_get(
            client, "/api/admin/stats/games?period=1h", admin_headers
        )
        assert body["total"] == 1
        assert body["by_room_type"]["ai"] == 1

        body = _admin_get(
            client, "/api/admin/stats/games?period=12h", admin_headers
        )
        assert body["total"] == 2
        assert body["by_anonymous_count"]["0"] == 1
        assert body["by_anonymous_count"]["1"] == 1

        body = _admin_get(
            client,
            "/api/admin/stats/games?period=24h&anonymous_players=1",
            admin_headers,
        )
        assert body["total"] == 1

        body = _admin_get(
            client,
            f"/api/admin/stats/games?period=24h&room_type=ai",
            admin_headers,
        )
        assert body["total"] == 2

        assert db_scalar(
            "SELECT COUNT(*) FROM finished_games WHERE room_id IN (%s, %s)",
            (room_recent, room_anon),
        ) == 2

    def test_games_outside_short_period_excluded(
        self, client, admin_headers, register_user
    ):
        now = datetime.now(timezone.utc)
        room_id = _finish_ai_game(client, new_client_id())
        backdate_finished_game(room_id, now - timedelta(hours=5))

        assert _admin_get(
            client, "/api/admin/stats/games?period=1h", admin_headers
        )["total"] == 0
        assert _admin_get(
            client, "/api/admin/stats/games?period=6h", admin_headers
        )["total"] == 1

    def test_mixed_room_types_in_breakdown(self, client, admin_headers):
        now = datetime.now(timezone.utc)
        from tests.admin.conftest import insert_finished_game

        _finish_ai_game(client, new_client_id())
        insert_finished_game(
            room_id="pub99999",
            room_type="public",
            white_is_anonymous=False,
            black_is_anonymous=True,
            finished_at=now,
        )
        insert_finished_game(
            room_id="priv8888",
            room_type="private",
            white_is_anonymous=True,
            black_is_anonymous=True,
            finished_at=now,
        )

        body = _admin_get(
            client, "/api/admin/stats/games?period=24h", admin_headers
        )
        assert body["total"] == 3
        assert body["by_room_type"] == {"public": 1, "private": 1, "ai": 1}
        assert body["by_anonymous_count"]["1"] == 2
        assert body["by_anonymous_count"]["2"] == 1

        body = _admin_get(
            client,
            "/api/admin/stats/games?period=24h&room_type=private",
            admin_headers,
        )
        assert body["total"] == 1
        assert body["by_room_type"]["private"] == 1


class TestAdminOnlineE2E:
    """WS connect (presence) → GET /api/admin/stats/online?at=..."""

    def test_online_counts_registered_and_anonymous_ws_sessions(
        self, client, admin_headers, register_user
    ):
        user = register_user("online_reg")
        auth_cid = new_client_id()
        anon_cid = new_client_id()

        auth_room = create_room(
            client,
            room_type="ai",
            client_id=auth_cid,
            headers=auth_headers(user["access_token"]),
        )
        anon_room = create_room(client, room_type="ai", client_id=anon_cid)

        with (
            client.websocket_connect(
                ws_path(auth_room, auth_cid, user["access_token"])
            ) as ws_auth,
            client.websocket_connect(ws_path(anon_room, anon_cid)) as ws_anon,
        ):
            wait_game_started(ws_auth)
            wait_game_started(ws_anon)
            at = quote(datetime.now(timezone.utc).isoformat(), safe="")
            body = _admin_get(
                client, f"/api/admin/stats/online?at={at}", admin_headers
            )
            assert body["total_unique"] == 2
            assert body["registered_unique"] == 1
            assert body["anonymous_unique"] == 1

        manager.connections.pop(auth_room, None)
        manager.connections.pop(anon_room, None)

    def test_online_same_user_two_tabs_counted_once(
        self, client, admin_headers, register_user
    ):
        user = register_user("dual_tab")
        room_a = create_room(
            client,
            room_type="ai",
            client_id=new_client_id(),
            headers=auth_headers(user["access_token"]),
        )
        room_b = create_room(
            client,
            room_type="ai",
            client_id=new_client_id(),
            headers=auth_headers(user["access_token"]),
        )
        tab_a = new_client_id()
        tab_b = new_client_id()

        with (
            client.websocket_connect(ws_path(room_a, tab_a, user["access_token"])) as ws_a,
            client.websocket_connect(ws_path(room_b, tab_b, user["access_token"])) as ws_b,
        ):
            wait_game_started(ws_a)
            wait_game_started(ws_b)
            at = quote(datetime.now(timezone.utc).isoformat(), safe="")
            body = _admin_get(
                client, f"/api/admin/stats/online?at={at}", admin_headers
            )
            assert body["total_unique"] == 1
            assert body["registered_unique"] == 1

        manager.connections.pop(room_a, None)
        manager.connections.pop(room_b, None)

    def test_online_excludes_disconnected_session(
        self, client, admin_headers, register_user
    ):
        anon_cid = new_client_id()
        room_id = create_room(client, room_type="ai", client_id=anon_cid)

        with client.websocket_connect(ws_path(room_id, anon_cid)) as ws:
            wait_game_started(ws)
            at_connected = quote(datetime.now(timezone.utc).isoformat(), safe="")
            body = _admin_get(
                client, f"/api/admin/stats/online?at={at_connected}", admin_headers
            )
            assert body["total_unique"] == 1

        # TestClient не всегда дожидается WS disconnect handler — закрываем presence явно
        import asyncio

        from backend.presence import end_session

        asyncio.run(end_session(anon_cid))

        at_after = quote(datetime.now(timezone.utc).isoformat(), safe="")
        body = _admin_get(
            client, f"/api/admin/stats/online?at={at_after}", admin_headers
        )
        assert body["total_unique"] == 0

        manager.connections.pop(room_id, None)
