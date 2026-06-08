"""Tests for persisting finished games to PostgreSQL."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import func, select

from backend.board_utils import get_starting_board, keys_int_to_str
from backend.rating.elo import rating_deltas
from backend.rating.service import score_for_color
from backend.db.models import FinishedGame, User
from backend.db.session import get_session_factory
from backend.game_archive import (
    archive_finished_game,
    filter_move_history,
    mark_game_started,
    on_game_finished,
)
from backend.game_helpers import apply_move_result
from backend.session.rematch import _start_rematch
from backend.timers import disconnect_timer, handle_timeout
from backend.ws_control_handlers import handle_cancel_game, handle_offer_draw, handle_resign
from backend.ws_manager import manager
from game_engine.models import GameEventResult
from tests.server.conftest import ensure_users_for_room


def _room(room_id="room1", **extra):
    base = {
        "room_id": room_id,
        "type": "public",
        "game_started": True,
        "game_started_at": "2026-05-29T12:00:00+00:00",
        "players": {"p-white": "белый", "p-black": "черный"},
        "player_meta": {
            "p-white": {
                "user_id": str(uuid.uuid4()),
                "username": "alice",
                "is_anonymous": False,
            },
            "p-black": {
                "user_id": None,
                "username": None,
                "is_anonymous": True,
            },
        },
        "time_control": 300,
        "increment": 5,
        "timer_white": 120.5,
        "timer_black": 200.0,
        "rematch_ready": [],
    }
    base.update(extra)
    return base


def _ai_room(**extra):
    return _room(
        type="ai",
        players={"human-1": "белый"},
        player_meta={
            "human-1": {
                "user_id": str(uuid.uuid4()),
                "username": "solo",
                "is_anonymous": False,
            },
        },
        **extra,
    )


def _finished_game(**extra):
    g = {
        "board": get_starting_board(),
        "mover": "черный",
        "game_over": True,
        "winner_color": "белый",
        "reason": "resign",
        "move_history": [
            {
                "move_number": 1,
                "mover": "белый",
                "from_pos": 53,
                "to_pos": 46,
                "desk": keys_int_to_str(get_starting_board()),
            },
        ],
    }
    g.update(extra)
    return g


class ArchiveState:
    """In-memory Redis stand-in for archive tests."""

    def __init__(self, room_id="room1", game=None, room=None):
        self.room_id = room_id
        self.game = dict(game or _finished_game())
        self.room = dict(room or _room(room_id=room_id))

    async def get_game(self, rid):
        return self.game if rid == self.room_id else None

    async def get_room(self, rid):
        return self.room if rid == self.room_id else None

    async def set_game(self, rid, data):
        if rid == self.room_id:
            self.game = dict(data)

    def patch_targets(self):
        return (
            "backend.game_archive.get_game",
            "backend.game_archive.get_room",
            "backend.game_archive.set_game",
        )


@pytest.fixture
def archive_state():
    st = ArchiveState()
    ensure_users_for_room(st.room)
    return st


async def _count_games() -> int:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.scalar(select(func.count()).select_from(FinishedGame))
        return int(result or 0)


async def _fetch_games(room_id: str | None = None) -> list[FinishedGame]:
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(FinishedGame)
        if room_id:
            stmt = stmt.where(FinishedGame.room_id == room_id)
        result = await session.scalars(stmt.order_by(FinishedGame.finished_at))
        return list(result.all())


def _both_registered_room(room_id="room1", **extra):
    white_id = uuid.uuid4()
    black_id = uuid.uuid4()
    room = _room(
        room_id=room_id,
        player_meta={
            "p-white": {
                "user_id": str(white_id),
                "username": "alice",
                "is_anonymous": False,
            },
            "p-black": {
                "user_id": str(black_id),
                "username": "bob",
                "is_anonymous": False,
            },
        },
        **extra,
    )
    return room, white_id, black_id


async def _get_user_stats(user_id: uuid.UUID) -> tuple[int, int]:
    factory = get_session_factory()
    async with factory() as session:
        user = await session.get(User, user_id)
        assert user is not None
        return user.rating, user.rated_games_count


async def _set_user_stats(user_id: uuid.UUID, rating: int, games: int) -> None:
    factory = get_session_factory()
    async with factory() as session:
        user = await session.get(User, user_id)
        assert user is not None
        user.rating = rating
        user.rated_games_count = games
        await session.commit()


@pytest.mark.asyncio
class TestArchiveRating:
    async def test_public_both_registered_updates_ratings(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(room_id=st.room_id)
        st.room = room
        ensure_users_for_room(st.room)
        await _set_user_stats(white_id, 1500, 50)
        await _set_user_stats(black_id, 1500, 50)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row = (await _fetch_games(st.room_id))[0]
        assert row.is_rated is True
        assert row.white_rating_delta == 10
        assert row.black_rating_delta == -10
        assert await _get_user_stats(white_id) == (1510, 51)
        assert await _get_user_stats(black_id) == (1490, 51)

    async def test_anonymous_opponent_not_rated(self, archive_state):
        st = archive_state
        ensure_users_for_room(st.room)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row = (await _fetch_games(st.room_id))[0]
        assert row.is_rated is False
        assert row.white_rating_delta is None

    async def test_private_unrated_not_applied(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(
            room_id=st.room_id, type="private", rated=False
        )
        st.room = room
        ensure_users_for_room(st.room)
        await _set_user_stats(white_id, 1500, 50)
        await _set_user_stats(black_id, 1500, 50)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row = (await _fetch_games(st.room_id))[0]
        assert row.is_rated is False
        assert await _get_user_stats(white_id) == (1500, 50)

    async def test_private_rated_updates_ratings(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(
            room_id=st.room_id, type="private", rated=True
        )
        st.room = room
        ensure_users_for_room(st.room)
        await _set_user_stats(white_id, 1500, 50)
        await _set_user_stats(black_id, 1500, 50)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row = (await _fetch_games(st.room_id))[0]
        assert row.is_rated is True
        assert row.white_rating_delta == 10
        assert await _get_user_stats(white_id) == (1510, 51)

    async def test_rated_draw_zero_deltas(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(room_id=st.room_id)
        st.room = room
        st.game = _finished_game(winner_color="", reason="draw_agreed")
        ensure_users_for_room(st.room)
        await _set_user_stats(white_id, 1500, 50)
        await _set_user_stats(black_id, 1500, 50)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row = (await _fetch_games(st.room_id))[0]
        assert row.is_rated is True
        assert row.white_rating_delta == 0
        assert row.black_rating_delta == 0
        assert await _get_user_stats(white_id) == (1500, 51)

    async def test_black_win_negative_white_delta(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(room_id=st.room_id)
        st.room = room
        st.game = _finished_game(winner_color="черный", reason="timeout")
        ensure_users_for_room(st.room)
        await _set_user_stats(white_id, 1500, 50)
        await _set_user_stats(black_id, 1500, 50)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row = (await _fetch_games(st.room_id))[0]
        assert row.white_rating_delta == -10
        assert row.black_rating_delta == 10

    async def test_upset_underdog_gains_more_than_standard(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(room_id=st.room_id)
        st.room = room
        st.game = _finished_game(winner_color="белый", reason="resign")
        ensure_users_for_room(st.room)
        await _set_user_stats(white_id, 1400, 50)
        await _set_user_stats(black_id, 1800, 50)

        expected = rating_deltas(1400, 1800, 50, 50, 1.0)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row = (await _fetch_games(st.room_id))[0]
        assert (row.white_rating_delta, row.black_rating_delta) == expected
        assert row.white_rating_delta == 18
        assert await _get_user_stats(white_id) == (1418, 51)

    async def test_novice_calibration_k40(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(room_id=st.room_id)
        st.room = room
        ensure_users_for_room(st.room)
        await _set_user_stats(white_id, 1500, 0)
        await _set_user_stats(black_id, 1500, 0)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row = (await _fetch_games(st.room_id))[0]
        assert row.white_rating_delta == 20
        assert row.black_rating_delta == -20

    async def test_deltas_match_elo_module(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(room_id=st.room_id)
        st.room = room
        ensure_users_for_room(st.room)
        white_rating, white_games = 1620, 29
        black_rating, black_games = 1580, 45
        await _set_user_stats(white_id, white_rating, white_games)
        await _set_user_stats(black_id, black_rating, black_games)
        score = score_for_color("белый", st.game.get("winner_color"), st.game.get("reason"))
        expected = rating_deltas(
            white_rating, black_rating, white_games, black_games, score
        )

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row = (await _fetch_games(st.room_id))[0]
        assert (row.white_rating_delta, row.black_rating_delta) == expected

    async def test_rated_game_broadcasts_rating_update(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(room_id=st.room_id)
        room["player_meta"]["p-white"]["rating"] = 1500
        room["player_meta"]["p-black"]["rating"] = 1500
        st.room = room
        ensure_users_for_room(st.room)
        await _set_user_stats(white_id, 1500, 50)
        await _set_user_stats(black_id, 1500, 50)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
            patch("backend.ws_manager.manager.send_to_room", new_callable=AsyncMock) as send,
        ):
            await archive_finished_game(st.room_id)

        rating_calls = [
            c for c in send.call_args_list
            if c.args[1].get("type") == "rating_update"
        ]
        assert len(rating_calls) == 1
        payload = rating_calls[0].args[1]
        by_id = {p["client_id"]: p for p in payload["players_info"]}
        assert by_id["p-white"]["rating"] == 1510
        assert by_id["p-white"]["rating_delta"] == 10
        assert by_id["p-black"]["rating_delta"] == -10

    async def test_unrated_game_no_rating_broadcast(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(
            room_id=st.room_id, type="private", rated=False
        )
        st.room = room
        ensure_users_for_room(st.room)
        await _set_user_stats(white_id, 1500, 50)
        await _set_user_stats(black_id, 1500, 50)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
            patch("backend.ws_manager.manager.send_to_room", new_callable=AsyncMock) as send,
        ):
            await archive_finished_game(st.room_id)

        rating_calls = [
            c for c in send.call_args_list
            if c.args[1].get("type") == "rating_update"
        ]
        assert rating_calls == []

    async def test_idempotent_archive_does_not_double_rating(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(room_id=st.room_id)
        st.room = room
        ensure_users_for_room(st.room)
        await _set_user_stats(white_id, 1500, 50)
        await _set_user_stats(black_id, 1500, 50)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            first = await archive_finished_game(st.room_id)
            second = await archive_finished_game(st.room_id)

        assert first is not None
        assert second is None
        assert await _get_user_stats(white_id) == (1510, 51)
        assert await _get_user_stats(black_id) == (1490, 51)

    async def test_master_k10_via_archive(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(room_id=st.room_id)
        st.room = room
        ensure_users_for_room(st.room)
        await _set_user_stats(white_id, 2050, 50)
        await _set_user_stats(black_id, 2050, 50)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row = (await _fetch_games(st.room_id))[0]
        assert row.white_rating_delta == 5
        assert row.black_rating_delta == -5
        assert await _get_user_stats(white_id) == (2055, 51)

    async def test_novice_to_standard_k_transition(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(room_id=st.room_id)
        st.room = room
        ensure_users_for_room(st.room)
        await _set_user_stats(white_id, 1500, 9)
        await _set_user_stats(black_id, 1500, 50)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row1 = (await _fetch_games(st.room_id))[0]
        assert row1.white_rating_delta == 20  # K=40
        assert (await _get_user_stats(white_id))[1] == 10

        room2_id = "room-k2"
        room2, _, _ = _both_registered_room(room_id=room2_id)
        room2["player_meta"]["p-white"]["user_id"] = str(white_id)
        room2["player_meta"]["p-black"]["user_id"] = str(black_id)
        await _set_user_stats(white_id, 1500, 10)
        await _set_user_stats(black_id, 1500, 50)
        st2 = ArchiveState(room_id=room2_id, room=room2, game=_finished_game())

        with (
            patch(st2.patch_targets()[0], side_effect=st2.get_game),
            patch(st2.patch_targets()[1], side_effect=st2.get_room),
            patch(st2.patch_targets()[2], side_effect=st2.set_game),
        ):
            await archive_finished_game(room2_id)

        row2 = (await _fetch_games(room2_id))[0]
        assert row2.white_rating_delta == 15  # K=30 after 10th game
        assert (await _get_user_stats(white_id)) == (1515, 11)

        room3_id = "room-k3"
        room3, _, _ = _both_registered_room(room_id=room3_id)
        room3["player_meta"]["p-white"]["user_id"] = str(white_id)
        room3["player_meta"]["p-black"]["user_id"] = str(black_id)
        await _set_user_stats(white_id, 1500, 20)
        await _set_user_stats(black_id, 1500, 50)
        st3 = ArchiveState(room_id=room3_id, room=room3, game=_finished_game())

        with (
            patch(st3.patch_targets()[0], side_effect=st3.get_game),
            patch(st3.patch_targets()[1], side_effect=st3.get_room),
            patch(st3.patch_targets()[2], side_effect=st3.set_game),
        ):
            await archive_finished_game(room3_id)

        row3 = (await _fetch_games(room3_id))[0]
        assert row3.white_rating_delta == 10  # K=20 after 20th game
        assert await _get_user_stats(white_id) == (1510, 21)


@pytest.mark.asyncio
class TestArchiveAntifraud:
    async def _seed_pair_wins(self, winner_id, loser_id, count: int) -> None:
        finished_at = datetime.now(timezone.utc) - timedelta(hours=2)
        factory = get_session_factory()
        async with factory() as session:
            for _ in range(count):
                session.add(
                    FinishedGame(
                        room_id=uuid.uuid4().hex[:8],
                        room_type="public",
                        white_user_id=winner_id,
                        black_user_id=loser_id,
                        winner_color="белый",
                        is_rated=True,
                        moves_count=12,
                        loser_rated_games_before=10,
                        white_rating_delta=10,
                        black_rating_delta=-10,
                        finished_at=finished_at,
                    )
                )
            await session.commit()

    async def test_fourth_win_over_same_opponent_caps_winner_gain(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(room_id=st.room_id)
        st.room = room
        ensure_users_for_room(st.room)
        await _set_user_stats(white_id, 1500, 50)
        await _set_user_stats(black_id, 1500, 50)
        await self._seed_pair_wins(white_id, black_id, 3)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row = (await _fetch_games(st.room_id))[0]
        assert row.white_rating_delta == 0
        assert row.black_rating_delta == -10
        assert row.white_gain_capped is True
        assert await _get_user_stats(white_id) == (1500, 51)
        assert await _get_user_stats(black_id) == (1490, 51)

    async def _seed_smurf_wins(self, winner_id, count: int) -> None:
        finished_at = datetime.now(timezone.utc) - timedelta(hours=1)
        factory = get_session_factory()
        async with factory() as session:
            for i in range(count):
                session.add(
                    FinishedGame(
                        room_id=uuid.uuid4().hex[:8],
                        room_type="public",
                        white_user_id=winner_id,
                        black_user_id=None,
                        winner_color="белый",
                        is_rated=True,
                        moves_count=6,
                        loser_rated_games_before=i,
                        white_rating_delta=10,
                        black_rating_delta=-10,
                        finished_at=finished_at,
                    )
                )
            await session.commit()

    async def test_fourth_smurf_win_via_archive_sets_block(self, archive_state):
        st = archive_state
        room, white_id, black_id = _both_registered_room(room_id=st.room_id)
        st.room = room
        st.game = _finished_game(
            winner_color="белый",
            reason="resign",
            move_history=[
                {
                    "move_number": 1,
                    "mover": "белый",
                    "from_pos": 53,
                    "to_pos": 46,
                    "desk": keys_int_to_str(get_starting_board()),
                },
            ],
        )
        ensure_users_for_room(st.room)
        await _set_user_stats(white_id, 1500, 50)
        await _set_user_stats(black_id, 1200, 1)
        await self._seed_smurf_wins(white_id, 3)

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row = (await _fetch_games(st.room_id))[0]
        assert row.white_rating_delta == 0
        assert row.white_gain_capped is True
        assert row.loser_rated_games_before == 1
        assert row.moves_count == 1

        factory = get_session_factory()
        async with factory() as session:
            user = await session.get(User, white_id)
            assert user is not None
            assert user.rating_gain_blocked_until is not None


@pytest.mark.asyncio
class TestArchiveBasics:
    async def test_pvp_resign_archives_players_and_result(self, archive_state):
        st = archive_state
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            record_id = await archive_finished_game(st.room_id)

        assert record_id is not None
        assert await _count_games() == 1
        rows = await _fetch_games(st.room_id)
        row = rows[0]
        assert row.room_type == "public"
        assert row.winner_color == "белый"
        assert row.reason == "resign"
        assert row.white_client_id == "p-white"
        assert row.black_client_id == "p-black"
        assert row.white_is_anonymous is False
        assert row.black_is_anonymous is True
        assert row.moves_count == 1
        assert row.time_control == 300
        assert row.timer_white_final == 120.5
        assert st.game.get("archived") is True

    async def test_ai_game_archives_human_and_null_bot_side(self, archive_state):
        st = archive_state
        st.room = _ai_room(room_id=st.room_id)
        ensure_users_for_room(st.room)
        st.game = _finished_game(reason="ai.no_move", winner_color="черный")

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row = (await _fetch_games())[0]
        assert row.room_type == "ai"
        assert row.black_client_id is None
        assert row.black_user_id is None
        assert row.white_is_anonymous is False
        assert row.black_is_anonymous is False

    async def test_cancelled_not_archived(self, archive_state):
        st = archive_state
        st.game["reason"] = "cancelled"

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
            patch("backend.game_archive.record_game_finished") as record_finished,
        ):
            assert await archive_finished_game(st.room_id) is None

        record_finished.assert_not_called()
        assert await _count_games() == 0
        assert st.game.get("archived") is not True

    async def test_successful_archive_records_finished_metric(self, archive_state):
        st = archive_state
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
            patch("backend.game_archive.record_game_finished") as record_finished,
        ):
            await archive_finished_game(st.room_id)

        record_finished.assert_called_once()
        kwargs = record_finished.call_args.kwargs
        assert kwargs["reason"] == "resign"
        assert kwargs["room_type"] == "public"
        assert kwargs["plies"] == 1
        assert kwargs["duration_seconds"] is not None

    async def test_idempotent_second_call_records_finished_once(self, archive_state):
        st = archive_state
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
            patch("backend.game_archive.record_game_finished") as record_finished,
        ):
            first = await archive_finished_game(st.room_id)
            second = await archive_finished_game(st.room_id)

        assert first is not None
        assert second is None
        record_finished.assert_called_once()
        assert record_finished.call_args.kwargs["plies"] == 1

    async def test_archive_db_error_records_archive_error(self, archive_state):
        st = archive_state

        class BrokenSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            def add(self, _record):
                return None

            async def commit(self):
                raise RuntimeError("db down")

            async def refresh(self, _record):
                return None

        broken_factory = MagicMock(return_value=BrokenSession())

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
            patch("backend.game_archive.get_session_factory", return_value=broken_factory),
            patch("backend.game_archive.record_archive_error") as record_error,
            patch("backend.game_archive.capture_exception") as capture,
        ):
            assert await archive_finished_game(st.room_id) is None

        record_error.assert_called_once()
        capture.assert_called_once()

    async def test_not_game_over_not_archived(self, archive_state):
        st = archive_state
        st.game["game_over"] = False

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            assert await archive_finished_game(st.room_id) is None

        assert await _count_games() == 0

    async def test_idempotent_second_call_skips(self, archive_state):
        st = archive_state
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            first = await archive_finished_game(st.room_id)
            second = await archive_finished_game(st.room_id)

        assert first is not None
        assert second is None
        assert await _count_games() == 1

    async def test_missing_room_is_noop(self, archive_state):
        st = archive_state
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch("backend.game_archive.get_room", AsyncMock(return_value=None)),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            assert await archive_finished_game(st.room_id) is None
        assert await _count_games() == 0

    async def test_missing_game_is_noop(self, archive_state):
        st = archive_state
        with (
            patch("backend.game_archive.get_game", AsyncMock(return_value=None)),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            assert await archive_finished_game(st.room_id) is None
        assert await _count_games() == 0

    async def test_already_archived_flag_skips(self, archive_state):
        st = archive_state
        st.game["archived"] = True
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            assert await archive_finished_game(st.room_id) is None
        assert await _count_games() == 0


class TestArchiveMoveHistory:
    def test_filter_skips_junk_and_duplicate_desk(self):
        board_a = keys_int_to_str(get_starting_board())
        game = {
            "move_history": [
                {"from_pos": 1, "to_pos": 2, "desk": board_a, "mover": "белый"},
                {"from_pos": 0, "to_pos": 0, "desk": board_a, "mover": "белый"},
                {"from_pos": 3, "to_pos": 4, "desk": board_a, "mover": "черный"},
                {"from_pos": 5, "to_pos": 6, "desk": board_a, "mover": "белый"},
            ],
        }
        filtered = filter_move_history(game)
        assert len(filtered) == 1
        assert filtered[0]["move_number"] == 1
        assert filtered[0]["from_pos"] == 1

    def test_filter_empty_history(self):
        assert filter_move_history({"move_history": []}) == []
        assert filter_move_history({}) == []

    @pytest.mark.asyncio
    async def test_archived_moves_count_matches_filtered_history(self, archive_state):
        st = archive_state
        board_after_white = dict(get_starting_board())
        board_after_white[53] = None
        board_after_white[46] = "белая шатра"
        st.game["move_history"] = [
            {"from_pos": 53, "to_pos": 46, "desk": keys_int_to_str(get_starting_board()), "mover": "белый"},
            {"from_pos": 0, "to_pos": 0, "mover": "белый"},
            {"from_pos": 12, "to_pos": 19, "desk": keys_int_to_str(board_after_white), "mover": "черный"},
        ]
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)
        row = (await _fetch_games())[0]
        assert row.moves_count == 2
        assert len(row.move_history) == 2


@pytest.mark.asyncio
class TestArchiveIntegrationHooks:
    async def test_handle_resign_triggers_archive(self, archive_state):
        st = archive_state
        st.game["game_over"] = False
        ws = AsyncMock()

        with (
            patch("backend.ws_control_handlers.get_game", side_effect=st.get_game),
            patch("backend.ws_control_handlers.get_room", side_effect=st.get_room),
            patch("backend.ws_control_handlers.set_game", side_effect=st.set_game),
            patch("backend.ws_control_handlers.set_room", AsyncMock()),
            patch("backend.ws_control_handlers.manager.send_to_room", AsyncMock()),
            patch("backend.game_archive.get_game", side_effect=st.get_game),
            patch("backend.game_archive.get_room", side_effect=st.get_room),
            patch("backend.game_archive.set_game", side_effect=st.set_game),
        ):
            await handle_resign(st.room_id, "p-black", ws, is_ai_room=False)

        assert await _count_games() == 1
        row = (await _fetch_games())[0]
        assert row.reason == "resign"
        assert row.winner_color == "белый"

    async def test_handle_cancel_does_not_archive(self, archive_state):
        st = archive_state
        st.game["game_over"] = False
        ws = AsyncMock()

        with (
            patch("backend.ws_control_handlers.get_game", side_effect=st.get_game),
            patch("backend.ws_control_handlers.get_room", side_effect=st.get_room),
            patch("backend.ws_control_handlers.set_game", side_effect=st.set_game),
            patch("backend.ws_control_handlers.set_room", side_effect=st.set_game),
            patch("backend.ws_control_handlers.manager.send_to_room", AsyncMock()),
            patch("backend.game_archive.get_game", side_effect=st.get_game),
            patch("backend.game_archive.get_room", side_effect=st.get_room),
            patch("backend.game_archive.set_game", side_effect=st.set_game),
        ):
            await handle_cancel_game(st.room_id, "p-white", ws, is_ai_room=False)

        assert await _count_games() == 0

    async def test_handle_timeout_persists_winner_in_db(self, archive_state):
        st = archive_state
        st.game["game_over"] = False

        with (
            patch("backend.timers.get_game", side_effect=st.get_game),
            patch("backend.timers.get_room", side_effect=st.get_room),
            patch("backend.timers.set_game", side_effect=st.set_game),
            patch("backend.timers.manager.send_to_room", AsyncMock()),
            patch("backend.timers.stop_game_timer"),
            patch("backend.game_archive.get_game", side_effect=st.get_game),
            patch("backend.game_archive.get_room", side_effect=st.get_room),
            patch("backend.game_archive.set_game", side_effect=st.set_game),
        ):
            await handle_timeout(st.room_id, "белый")

        assert st.game["winner_color"] == "черный"
        assert st.game["reason"] == "timeout"
        row = (await _fetch_games())[0]
        assert row.winner_color == "черный"
        assert row.reason == "timeout"

    async def test_handle_offer_draw_accepted_archives(self, archive_state):
        st = archive_state
        st.game["game_over"] = False
        st.game["draw_offer_from"] = "белый"
        ws = AsyncMock()

        with (
            patch("backend.ws_control_handlers.get_game", side_effect=st.get_game),
            patch("backend.ws_control_handlers.get_room", side_effect=st.get_room),
            patch("backend.ws_control_handlers.set_game", side_effect=st.set_game),
            patch("backend.ws_control_handlers.set_room", AsyncMock()),
            patch("backend.ws_control_handlers.manager.send_to_room", AsyncMock()),
            patch("backend.timers.stop_game_timer"),
            patch("backend.game_archive.get_game", side_effect=st.get_game),
            patch("backend.game_archive.get_room", side_effect=st.get_room),
            patch("backend.game_archive.set_game", side_effect=st.set_game),
        ):
            await handle_offer_draw(st.room_id, "p-black", ws, is_ai_room=False)

        assert st.game["reason"] == "draw_agreed"
        row = (await _fetch_games())[0]
        assert row.reason == "draw_agreed"
        assert row.winner_color is None

    async def test_apply_move_result_game_over_archives(self, archive_state):
        st = archive_state
        st.game["game_over"] = False
        result = GameEventResult(
            message_code="turn.now",
            updated_positions=get_starting_board(),
            movers_color="черный",
            game_over=True,
            winner_color="белый",
        )

        with (
            patch("backend.game_helpers.get_room", side_effect=st.get_room),
            patch("backend.game_helpers.set_room", AsyncMock()),
            patch("backend.game_helpers.set_game", side_effect=st.set_game),
            patch("backend.game_archive.get_game", side_effect=st.get_game),
            patch("backend.game_archive.get_room", side_effect=st.get_room),
            patch("backend.game_archive.set_game", side_effect=st.set_game),
            patch("backend.game_archive.record_game_finished") as record_finished,
        ):
            await apply_move_result(st.room_id, st.game, result, "белый", 53, 46)

        assert st.game["reason"] == "biy_wins"
        record_finished.assert_called_once()
        kwargs = record_finished.call_args.kwargs
        assert kwargs["reason"] == "biy_wins"
        assert kwargs["room_type"] == "public"
        assert kwargs["plies"] == 1
        assert await _count_games() == 1

    async def test_draw_agreed_stores_null_winner(self, archive_state):
        st = archive_state
        st.game["winner_color"] = ""
        st.game["reason"] = "draw_agreed"

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        row = (await _fetch_games())[0]
        assert row.winner_color is None
        assert row.reason == "draw_agreed"


@pytest.mark.asyncio
class TestArchivePlayerIdentity:
    async def test_both_players_registered_not_anonymous(self, archive_state):
        st = archive_state
        uid_white = str(uuid.uuid4())
        uid_black = str(uuid.uuid4())
        st.room["player_meta"] = {
            "p-white": {"user_id": uid_white, "username": "w1", "is_anonymous": False},
            "p-black": {"user_id": uid_black, "username": "b1", "is_anonymous": False},
        }
        ensure_users_for_room(st.room)
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)
        row = (await _fetch_games())[0]
        assert row.white_is_anonymous is False
        assert row.black_is_anonymous is False
        assert str(row.white_user_id) == uid_white
        assert str(row.black_user_id) == uid_black

    async def test_both_anonymous_pvp(self, archive_state):
        st = archive_state
        st.room["player_meta"] = {
            "p-white": {"user_id": None, "username": None, "is_anonymous": True},
            "p-black": {"user_id": None, "username": None, "is_anonymous": True},
        }
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)
        row = (await _fetch_games())[0]
        assert row.white_is_anonymous is True
        assert row.black_is_anonymous is True
        assert row.white_user_id is None
        assert row.black_user_id is None

    async def test_ai_anonymous_human_archived(self, archive_state):
        st = archive_state
        st.room = _room(
            room_id=st.room_id,
            type="ai",
            players={"human-1": "белый"},
            player_meta={
                "human-1": {"user_id": None, "username": None, "is_anonymous": True},
            },
        )
        st.game = _finished_game(reason="ai.no_move", winner_color="черный")
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)
        row = (await _fetch_games())[0]
        assert row.room_type == "ai"
        assert row.white_is_anonymous is True
        assert row.reason == "ai.no_move"


@pytest.mark.asyncio
class TestArchivePersistedFields:
    async def test_empty_move_history_zero_moves(self, archive_state):
        st = archive_state
        st.game["move_history"] = []
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)
        row = (await _fetch_games())[0]
        assert row.moves_count == 0
        assert row.move_history == []

    async def test_started_at_null_when_missing(self, archive_state):
        st = archive_state
        st.room.pop("game_started_at", None)
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)
        assert (await _fetch_games())[0].started_at is None

    async def test_increment_and_untimed_room(self, archive_state):
        st = archive_state
        st.room["time_control"] = None
        st.room["increment"] = None
        st.room["timer_white"] = None
        st.room["timer_black"] = None
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)
        row = (await _fetch_games())[0]
        assert row.time_control is None
        assert row.increment is None
        assert row.timer_white_final is None

    async def test_move_history_fields_preserved_in_db(self, archive_state):
        st = archive_state
        desk = keys_int_to_str(get_starting_board())
        st.game["move_history"] = [
            {"from_pos": 53, "to_pos": 46, "desk": desk, "mover": "белый", "extra": "ignored"},
        ]
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)
        move = (await _fetch_games())[0].move_history[0]
        assert move["from_pos"] == 53
        assert move["to_pos"] == 46
        assert move["move_number"] == 1
        assert move["mover"] == "белый"

    async def test_engine_draw_reason_persisted(self, archive_state):
        st = archive_state
        st.game["reason"] = "DRAW_REPETITION"
        st.game["winner_color"] = ""
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)
        row = (await _fetch_games())[0]
        assert row.reason == "DRAW_REPETITION"
        assert row.winner_color is None

    async def test_finished_at_is_set(self, archive_state):
        st = archive_state
        before = datetime.now(timezone.utc)
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)
        row = (await _fetch_games())[0]
        assert row.finished_at >= before
        assert row.id is not None


@pytest.mark.asyncio
class TestArchiveCriticalEdgeCases:
    async def test_db_failure_does_not_mark_archived(self, archive_state):
        st = archive_state

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
            patch(
                "backend.game_archive.get_session_factory",
                side_effect=RuntimeError("db down"),
            ),
        ):
            assert await archive_finished_game(st.room_id) is None

        assert await _count_games() == 0
        assert st.game.get("archived") is not True

    async def test_rematch_archives_before_reset(self):
        room_id = "rematch1"
        finished = _finished_game(reason="resign", winner_color="черный")
        room = _room(room_id=room_id, rematch_ready=["p-white", "p-black"])
        ensure_users_for_room(room)
        stored_game = dict(finished)

        async def get_game(rid):
            return stored_game if rid == room_id else None

        async def get_room(rid):
            return room if rid == room_id else None

        async def set_game(rid, data):
            nonlocal stored_game
            if rid == room_id:
                stored_game = dict(data)

        async def set_room(rid, data):
            nonlocal room
            if rid == room_id:
                room = dict(data)

        ws = AsyncMock()
        manager.connections[room_id] = {"p-white": ws, "p-black": ws}

        with (
            patch("backend.game_archive.get_game", side_effect=get_game),
            patch("backend.game_archive.get_room", side_effect=get_room),
            patch("backend.game_archive.set_game", side_effect=set_game),
            patch("backend.session.rematch.get_game", side_effect=get_game),
            patch("backend.session.rematch.set_room", side_effect=set_room),
            patch("backend.session.rematch.init_game", AsyncMock()),
            patch("backend.session.rematch.stop_game_timer"),
            patch("backend.session.rematch.game_ticker"),
            patch("backend.session.rematch.manager.send_to_player", AsyncMock()),
        ):
            await _start_rematch(room_id, room)

        rows = await _fetch_games(room_id)
        assert len(rows) == 1
        assert rows[0].reason == "resign"
        manager.connections.pop(room_id, None)

    async def test_on_game_finished_wrapper(self, archive_state):
        st = archive_state
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await on_game_finished(st.room_id)
        assert await _count_games() == 1

    async def test_private_room_type_archived(self, archive_state):
        st = archive_state
        st.room["type"] = "private"
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)
        assert (await _fetch_games())[0].room_type == "private"

    async def test_private_friend_both_registered_full_snapshot(self, archive_state):
        st = archive_state
        uid_w = str(uuid.uuid4())
        uid_b = str(uuid.uuid4())
        st.room = _room(
            room_id=st.room_id,
            type="private",
            players={"host-1": "белый", "friend-1": "черный"},
            player_meta={
                "host-1": {
                    "user_id": uid_w,
                    "username": "host_user",
                    "is_anonymous": False,
                },
                "friend-1": {
                    "user_id": uid_b,
                    "username": "friend_user",
                    "is_anonymous": False,
                },
            },
        )
        ensure_users_for_room(st.room)
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)
        row = (await _fetch_games())[0]
        assert row.room_type == "private"
        assert str(row.white_user_id) == uid_w
        assert str(row.black_user_id) == uid_b
        assert row.white_is_anonymous is False
        assert row.black_is_anonymous is False

    async def test_ai_no_move_integration_archives_to_db(self, archive_state):
        st = archive_state
        st.room = _ai_room(room_id=st.room_id)
        ensure_users_for_room(st.room)
        st.game = {
            "board": get_starting_board(),
            "mover": "черный",
            "game_over": False,
            "move_history": [],
        }

        with (
            patch("backend.session.ai.get_ai_move", return_value=None),
            patch("backend.session.ai.set_game", side_effect=st.set_game),
            patch("backend.session.ai.manager.send_to_room", AsyncMock()),
            patch("backend.game_archive.get_game", side_effect=st.get_game),
            patch("backend.game_archive.get_room", side_effect=st.get_room),
            patch("backend.game_archive.set_game", side_effect=st.set_game),
        ):
            from backend.session.ai import handle_ai_move

            await handle_ai_move(
                st.room_id, st.game, max_retries=1, room_data=st.room,
            )

        row = (await _fetch_games())[0]
        assert row.room_type == "ai"
        assert row.reason == "ai.no_move"
        assert row.winner_color == "белый"
        assert row.white_client_id == "human-1"
        assert row.black_client_id is None

    async def test_started_at_parsed_from_room(self, archive_state):
        st = archive_state
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)
        row = (await _fetch_games())[0]
        assert row.started_at is not None
        assert row.started_at.year == 2026

    async def test_final_board_snapshot_saved(self, archive_state):
        st = archive_state
        board = get_starting_board()
        board[53] = None
        st.game["board"] = board
        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)
        row = (await _fetch_games())[0]
        assert row.final_board.get("position53") is None

    async def test_winner_legacy_field_used_when_winner_color_missing(self, archive_state):
        st = archive_state
        st.game.pop("winner_color", None)
        st.game["winner"] = "черный"

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        assert (await _fetch_games())[0].winner_color == "черный"

    async def test_invalid_user_id_stored_as_null(self, archive_state):
        st = archive_state
        st.room["player_meta"]["p-white"]["user_id"] = "not-a-uuid"

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            await archive_finished_game(st.room_id)

        assert (await _fetch_games())[0].white_user_id is None

    async def test_unknown_room_type_not_archived(self, archive_state):
        st = archive_state
        st.room["type"] = "training"

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            assert await archive_finished_game(st.room_id) is None

        assert await _count_games() == 0

    async def test_same_room_id_can_have_multiple_finished_rows(self, archive_state):
        st = archive_state

        with (
            patch(st.patch_targets()[0], side_effect=st.get_game),
            patch(st.patch_targets()[1], side_effect=st.get_room),
            patch(st.patch_targets()[2], side_effect=st.set_game),
        ):
            first_id = await archive_finished_game(st.room_id)
            st.game["archived"] = False
            st.game["reason"] = "timeout"
            st.game["winner_color"] = "черный"
            second_id = await archive_finished_game(st.room_id)

        assert first_id != second_id
        rows = await _fetch_games(st.room_id)
        assert len(rows) == 2
        reasons = {row.reason for row in rows}
        assert reasons == {"resign", "timeout"}

    async def test_disconnect_timer_archives_opponent_disconnect(self, archive_state):
        st = archive_state
        st.game["game_over"] = False
        ws = AsyncMock()

        with (
            patch("backend.timers.DISCONNECT_TIMEOUT", 1),
            patch("backend.timers.TICK_INTERVAL_SECONDS", 0),
            patch("backend.timers.get_game", side_effect=st.get_game),
            patch("backend.timers.get_room", side_effect=st.get_room),
            patch("backend.timers.set_game", side_effect=st.set_game),
            patch("backend.timers.manager.send_to_room", AsyncMock()),
            patch("backend.timers.stop_game_timer"),
            patch("backend.game_archive.get_game", side_effect=st.get_game),
            patch("backend.game_archive.get_room", side_effect=st.get_room),
            patch("backend.game_archive.set_game", side_effect=st.set_game),
        ):
            await disconnect_timer(st.room_id, ws, "p-black")

        row = (await _fetch_games())[0]
        assert row.reason == "opponent_disconnected"
        assert row.winner_color == "белый"


class TestArchiveHelpers:
    def test_mark_game_started_sets_iso_timestamp(self):
        room = _room()
        room.pop("game_started_at", None)
        mark_game_started(room)
        assert room["game_started_at"]
        assert "T" in room["game_started_at"]
