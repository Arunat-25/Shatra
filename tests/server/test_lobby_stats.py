"""Tests for lobby stats in GET /rooms."""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone

import psycopg2
import pytest

from backend.presence import start_session
from tests.integration.helpers import flush_redis, new_client_id, redis_client
from tests.test_env import SYNC_DB_URL

pytestmark = pytest.mark.server


def _insert_open_lobby_session(
    *,
    client_id: str,
    last_seen_at: datetime | None = None,
    user_id: uuid.UUID | None = None,
    is_anonymous: bool = True,
) -> None:
    now = datetime.now(timezone.utc)
    seen = last_seen_at or now
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO presence_sessions (
                id, client_id, user_id, is_anonymous, room_id,
                connected_at, disconnected_at, last_seen_at
            ) VALUES (%s, %s, %s, %s, NULL, %s, NULL, %s)
            """,
            (
                str(uuid.uuid4()),
                client_id,
                str(user_id) if user_id else None,
                is_anonymous,
                now,
                seen,
            ),
        )
    conn.close()


@pytest.fixture(autouse=True)
def _clean_redis():
    flush_redis()
    yield
    flush_redis()


class TestLobbyStats:
    def test_single_tab_online_is_one(self, client):
        cid = new_client_id()
        stats = client.get(f"/rooms?client_id={cid}").json()["stats"]
        assert stats["online_total"] == 1

    def test_orphan_ws_sessions_not_counted(self, client):
        for i in range(3):
            asyncio.run(
                start_session(
                    client_id=f"ghost-ws-{i}",
                    user_id=None,
                    is_anonymous=True,
                    room_id=f"gh{i:04}",
                )
            )
        cid = new_client_id()
        stats = client.get(f"/rooms?client_id={cid}").json()["stats"]
        assert stats["online_total"] == 1

    def test_stale_lobby_sessions_not_counted(self, client):
        stale_at = datetime.now(timezone.utc) - timedelta(seconds=60)
        for i in range(3):
            _insert_open_lobby_session(
                client_id=f"ghost-lobby-{i}",
                last_seen_at=stale_at,
            )
        cid = new_client_id()
        stats = client.get(f"/rooms?client_id={cid}").json()["stats"]
        assert stats["online_total"] == 1

    def test_duplicate_open_lobby_same_client_counts_once(self, client):
        cid = "dup-lobby-client"
        now = datetime.now(timezone.utc)
        for _ in range(3):
            _insert_open_lobby_session(client_id=cid, last_seen_at=now)
        stats = client.get(f"/rooms?client_id={cid}").json()["stats"]
        assert stats["online_total"] == 1

    def test_stats_shape(self, client):
        cid = new_client_id()
        r = client.get(f"/rooms?client_id={cid}")
        assert r.status_code == 200
        data = r.json()
        assert "stats" in data
        stats = data["stats"]
        assert "online_total" in stats
        assert "active_games" in stats
        assert "waiting_public_rooms" in stats

    def test_poll_increments_online(self, client):
        cid = new_client_id()
        before = client.get(f"/rooms?client_id={cid}").json()["stats"]["online_total"]
        cid2 = new_client_id()
        after = client.get(f"/rooms?client_id={cid2}").json()["stats"]["online_total"]
        assert after >= before + 1

    def test_leave_drops_online_immediately(self, client):
        cid = new_client_id()
        alone = client.get(f"/rooms?client_id={cid}").json()["stats"]["online_total"]
        assert alone == 1
        assert client.post(f"/rooms/presence/leave?client_id={cid}").status_code == 200
        # Без client_id — только читаем счётчик, не создаём новую presence.
        after = client.get("/rooms").json()["stats"]["online_total"]
        assert after == 0

    def test_active_games_count_via_redis_seed(self, client):
        from backend.ws_manager import manager

        room_id = "actv0001"
        room = {
            "room_id": room_id,
            "type": "public",
            "game_started": True,
            "created_at": "2026-01-01T00:00:00",
            "players": {"a": "белый", "b": "черный"},
            "player_meta": {},
        }
        game = {"game_over": False, "board": {}}
        r = redis_client()
        r.set(f"room:{room_id}", json.dumps(room))
        r.set(f"game:{room_id}", json.dumps(game))
        manager.connections[room_id] = {"a": object()}
        try:
            stats = client.get(f"/rooms?client_id={new_client_id()}").json()["stats"]
            assert stats["active_games"] >= 1
        finally:
            manager.connections.pop(room_id, None)

    def test_active_games_ignores_orphan_redis_without_ws(self, client):
        room_id = "orph0001"
        room = {
            "room_id": room_id,
            "type": "ai",
            "game_started": True,
            "created_at": "2026-01-01T00:00:00",
            "players": {"a": "белый"},
            "player_meta": {},
        }
        game = {"game_over": False, "board": {}}
        r = redis_client()
        r.set(f"room:{room_id}", json.dumps(room))
        r.set(f"game:{room_id}", json.dumps(game))
        stats = client.get(f"/rooms?client_id={new_client_id()}").json()["stats"]
        assert stats["active_games"] == 0
