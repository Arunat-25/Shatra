"""E2E: rated PvP → DB ratings → API profile/history."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

import tests.test_env  # noqa: F401

from backend.models import CreateRoomRequest
from backend.player_identity import build_players_info
from backend.rating.elo import rating_deltas
from backend.room_manager import create_room
from backend.ws_manager import handle_player2_join, manager
from main import app
from tests.db.conftest import db_fetchone
from tests.integration.helpers import auth_headers, read_room_json
from tests.integration.test_ws_pvp_connect import _connect_player, _register_pair

pytestmark = pytest.mark.integration


def _user_rating(user_id: str) -> tuple[int, int]:
    row = db_fetchone(
        "SELECT rating, rated_games_count FROM users WHERE id = %s",
        (user_id,),
    )
    assert row is not None
    return int(row[0]), int(row[1])


def _finished_game_row(room_id: str) -> tuple:
    row = db_fetchone(
        """
        SELECT is_rated, white_rating_delta, black_rating_delta,
               white_user_id, black_user_id, winner_color
        FROM finished_games WHERE room_id = %s
        """,
        (room_id,),
    )
    assert row is not None
    return row


async def _run_rated_pvp(
    *,
    room_type: str = "public",
    rated: bool = False,
    resign_client_id: str | None = None,
    preset_games: int = 50,
    preset_rating: int = 1500,
):
    from unittest.mock import AsyncMock

    from backend.db.models import User
    from backend.db.session import get_session_factory
    from backend.game_archive import archive_finished_game
    from backend.state import close_redis, init_redis
    from backend.ws_control_handlers import handle_resign

    host, guest = _register_pair()
    await init_redis()
    try:
        factory = get_session_factory()
        async with factory() as session:
            host_user = await session.get(User, uuid.UUID(host["user_id"]))
            guest_user = await session.get(User, uuid.UUID(guest["user_id"]))
            for user in (host_user, guest_user):
                user.rating = preset_rating
                user.rated_games_count = preset_games
            await session.commit()

        result = await create_room(
            CreateRoomRequest(
                type=room_type,
                creator_client_id=host["client_id"],
                rated=rated,
            ),
            user=host_user,
        )
        room_id = result["room_id"]

        await _connect_player(room_id, host["client_id"], host)
        await _connect_player(room_id, guest["client_id"], guest)

        room_data = read_room_json(room_id)
        await handle_player2_join(room_id, room_data)

        resign_id = resign_client_id or guest["client_id"]
        ws = AsyncMock()
        await handle_resign(room_id, resign_id, ws, is_ai_room=False)
        await archive_finished_game(room_id)
        manager.connections.pop(room_id, None)
        return room_id, host, guest
    finally:
        await close_redis()


class TestRatingE2E:
    def test_public_pvp_updates_ratings_in_db(self):
        room_id, host, guest = asyncio.run(_run_rated_pvp(room_type="public"))
        row = _finished_game_row(room_id)
        assert row[0] is True
        assert row[3] is not None and row[4] is not None

        white_id = str(row[3])
        score_white = 1.0 if row[5] == "белый" else 0.0
        expected = rating_deltas(1500, 1500, 50, 50, score_white)

        assert (row[1], row[2]) == expected
        if white_id == host["user_id"]:
            assert _user_rating(host["user_id"]) == (1500 + expected[0], 51)
            assert _user_rating(guest["user_id"]) == (1500 + expected[1], 51)
        else:
            assert _user_rating(guest["user_id"]) == (1500 + expected[0], 51)
            assert _user_rating(host["user_id"]) == (1500 + expected[1], 51)

    def test_private_rated_updates_ratings(self):
        room_id, host, guest = asyncio.run(
            _run_rated_pvp(room_type="private", rated=True)
        )
        row = _finished_game_row(room_id)
        assert row[0] is True
        assert row[1] is not None

    def test_private_unrated_no_rating_change(self):
        room_id, host, guest = asyncio.run(
            _run_rated_pvp(room_type="private", rated=False)
        )
        row = _finished_game_row(room_id)
        assert row[0] is False
        assert _user_rating(host["user_id"]) == (1500, 50)
        assert _user_rating(guest["user_id"]) == (1500, 50)

    def test_me_reflects_new_rating(self):
        room_id, host, guest = asyncio.run(_run_rated_pvp(room_type="public"))
        row = _finished_game_row(room_id)
        score_white = 1.0 if row[5] == "белый" else 0.0
        expected = rating_deltas(1500, 1500, 50, 50, score_white)

        with TestClient(app) as client:
            for user, delta_idx in ((host, 0), (guest, 1)):
                white_id = str(row[3])
                delta = expected[0] if user["user_id"] == white_id else expected[1]
                me = client.get(
                    "/api/auth/me",
                    headers=auth_headers(user["access_token"]),
                )
                assert me.status_code == 200
                assert me.json()["rating"] == 1500 + delta
                assert me.json()["rated_games_count"] == 51

    def test_games_history_rating_delta_both_colors(self):
        room_id, host, guest = asyncio.run(_run_rated_pvp(room_type="public"))
        row = _finished_game_row(room_id)
        white_id = str(row[3])
        expected = rating_deltas(
            1500,
            1500,
            50,
            50,
            1.0 if row[5] == "белый" else 0.0,
        )

        with TestClient(app) as client:
            for user in (host, guest):
                r = client.get(
                    "/api/auth/me/games",
                    headers=auth_headers(user["access_token"]),
                )
                assert r.status_code == 200
                item = next(g for g in r.json()["items"] if g["room_id"] == room_id)
                assert item["is_rated"] is True
                delta = expected[0] if user["user_id"] == white_id else expected[1]
                assert item["rating_delta"] == delta

    def test_refresh_rating_at_game_start(self):
        async def _run():
            from backend.db.models import User
            from backend.db.session import get_session_factory
            from backend.state import close_redis, init_redis

            host, guest = _register_pair()
            await init_redis()
            try:
                factory = get_session_factory()
                async with factory() as session:
                    host_user = await session.get(User, uuid.UUID(host["user_id"]))
                    host_user.rating = 1300
                    await session.commit()

                result = await create_room(
                    CreateRoomRequest(
                        type="public",
                        creator_client_id=host["client_id"],
                    ),
                    user=host_user,
                )
                room_id = result["room_id"]
                await _connect_player(room_id, host["client_id"], host)
                await _connect_player(room_id, guest["client_id"], guest)

                room_data = read_room_json(room_id)
                room_data["player_meta"][host["client_id"]]["rating"] = 1200
                await handle_player2_join(room_id, room_data)

                updated = read_room_json(room_id)
                assert updated["player_meta"][host["client_id"]]["rating"] == 1300
                info = build_players_info(updated)
                host_info = next(
                    p for p in info if p["client_id"] == host["client_id"]
                )
                assert host_info["rating"] == 1300
                manager.connections.pop(room_id, None)
            finally:
                await close_redis()

        asyncio.run(_run())
