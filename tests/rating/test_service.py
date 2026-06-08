"""Tests for backend.rating.service — eligibility and score mapping."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend.db.models import FinishedGame, User
from backend.db.session import get_session_factory
from backend.rating.elo import rating_deltas
from backend.rating.service import apply_rating, is_rated_match, score_for_color
from tests.rating.conftest import create_test_user

_APPLY_AT = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)

def _side(user_id=None, is_anonymous=False):
    return {
        "user_id": user_id,
        "client_id": "c1",
        "username": "u",
        "is_anonymous": is_anonymous,
    }


class TestIsRatedMatch:
    def test_public_both_registered(self):
        white = _side(uuid.uuid4(), False)
        black = _side(uuid.uuid4(), False)
        assert is_rated_match({"type": "public"}, white, black) is True

    @pytest.mark.parametrize(
        "black_meta",
        [
            {"user_id": None, "is_anonymous": True},
            {"user_id": uuid.uuid4(), "is_anonymous": True},
            {"user_id": None, "is_anonymous": False},
        ],
    )
    def test_public_opponent_not_fully_registered(self, black_meta):
        white = _side(uuid.uuid4(), False)
        black = _side(black_meta["user_id"], black_meta["is_anonymous"])
        assert is_rated_match({"type": "public"}, white, black) is False

    @pytest.mark.parametrize(
        "white_meta",
        [
            {"user_id": None, "is_anonymous": True},
            {"user_id": uuid.uuid4(), "is_anonymous": True},
        ],
    )
    def test_public_white_not_fully_registered(self, white_meta):
        white = _side(white_meta["user_id"], white_meta["is_anonymous"])
        black = _side(uuid.uuid4(), False)
        assert is_rated_match({"type": "public"}, white, black) is False

    def test_private_unrated_flag(self):
        white = _side(uuid.uuid4(), False)
        black = _side(uuid.uuid4(), False)
        assert is_rated_match({"type": "private", "rated": False}, white, black) is False

    def test_private_rated_flag(self):
        white = _side(uuid.uuid4(), False)
        black = _side(uuid.uuid4(), False)
        assert is_rated_match({"type": "private", "rated": True}, white, black) is True

    def test_private_rated_missing_key(self):
        white = _side(uuid.uuid4(), False)
        black = _side(uuid.uuid4(), False)
        assert is_rated_match({"type": "private"}, white, black) is False

    @pytest.mark.parametrize("room_type", ["ai", "spectator", ""])
    def test_non_pvp_never_rated(self, room_type):
        white = _side(uuid.uuid4(), False)
        black = _side(uuid.uuid4(), False)
        assert is_rated_match({"type": room_type}, white, black) is False


class TestScoreForColor:
    @pytest.mark.parametrize(
        ("my_color", "winner_color", "reason", "expected"),
        [
            ("белый", "белый", "resign", 1.0),
            ("черный", "белый", "resign", 0.0),
            ("белый", "черный", "timeout", 0.0),
            ("черный", "черный", "timeout", 1.0),
            ("белый", "белый", "checkmate", 1.0),
            ("черный", "белый", "opponent_disconnected", 0.0),
        ],
    )
    def test_win_loss_by_color(self, my_color, winner_color, reason, expected):
        assert score_for_color(my_color, winner_color, reason) == expected

    @pytest.mark.parametrize(
        ("my_color", "winner_color", "reason"),
        [
            ("белый", "", "draw_agreed"),
            ("черный", "", "draw_agreed"),
            ("белый", None, "draw_agreed"),
            ("черный", None, "draw_agreed"),
            ("белый", None, "stalemate"),
            ("черный", None, "threefold"),
            ("белый", "", "insufficient_material"),
        ],
    )
    def test_draw_always_half_point(self, my_color, winner_color, reason):
        assert score_for_color(my_color, winner_color, reason) == 0.5

    def test_draw_agreed_ignores_winner_color(self):
        assert score_for_color("белый", "белый", "draw_agreed") == 0.5
        assert score_for_color("черный", "белый", "draw_agreed") == 0.5


class TestServiceToEloIntegration:
    """End-to-end: game result → score → rating_deltas."""

    def _deltas_for_game(
        self,
        *,
        winner_color: str | None,
        reason: str | None,
        white_rating: int,
        black_rating: int,
        white_games: int,
        black_games: int,
    ):
        score_white = score_for_color("белый", winner_color, reason)
        return rating_deltas(
            white_rating,
            black_rating,
            white_games,
            black_games,
            score_white,
        )

    def test_white_resign_black_gains(self):
        dw, db = self._deltas_for_game(
            winner_color="черный",
            reason="resign",
            white_rating=1500,
            black_rating=1500,
            white_games=50,
            black_games=50,
        )
        assert dw == -10
        assert db == 10

    def test_draw_agreed_no_winner(self):
        dw, db = self._deltas_for_game(
            winner_color="",
            reason="draw_agreed",
            white_rating=1500,
            black_rating=1500,
            white_games=50,
            black_games=50,
        )
        assert dw == 0
        assert db == 0

    def test_private_rated_upset(self):
        dw, db = self._deltas_for_game(
            winner_color="белый",
            reason="resign",
            white_rating=1400,
            black_rating=1700,
            white_games=5,
            black_games=50,
        )
        assert dw > 0
        assert db < 0
        assert dw != -db  # different K

    def test_timeout_white_wins(self):
        score = score_for_color("белый", "белый", "timeout")
        assert score == 1.0
        assert rating_deltas(1500, 1500, 50, 50, score) == (10, -10)


class TestPlayersInfoWithRatingResult:
    def test_adds_delta_and_new_rating(self):
        from backend.rating.service import players_info_with_rating_result

        room = {
            "players": {"w": "белый", "b": "черный"},
            "player_meta": {
                "w": {"username": "alice", "is_anonymous": False, "rating": 1500},
                "b": {"username": "bob", "is_anonymous": False, "rating": 1600},
            },
        }
        record = FinishedGame(
            room_id="r1",
            room_type="public",
            is_rated=True,
            white_client_id="w",
            black_client_id="b",
            white_rating_delta=10,
            black_rating_delta=-10,
        )
        info = players_info_with_rating_result(room, record)
        by_id = {p["client_id"]: p for p in info}
        assert by_id["w"]["rating"] == 1510
        assert by_id["w"]["rating_delta"] == 10
        assert by_id["b"]["rating"] == 1590
        assert by_id["b"]["rating_delta"] == -10

    def test_unrated_returns_no_delta(self):
        from backend.rating.service import players_info_with_rating_result

        room = {
            "players": {"w": "белый"},
            "player_meta": {
                "w": {"username": "alice", "is_anonymous": False, "rating": 1500},
            },
        }
        record = FinishedGame(room_id="r1", room_type="public", is_rated=False)
        info = players_info_with_rating_result(room, record)
        assert "rating_delta" not in info[0]

    def test_missing_client_id_skips_delta(self):
        from backend.rating.service import players_info_with_rating_result

        room = {
            "players": {"w": "белый", "b": "черный"},
            "player_meta": {
                "w": {"username": "alice", "is_anonymous": False, "rating": 1500},
                "b": {"username": "bob", "is_anonymous": False, "rating": 1600},
            },
        }
        record = FinishedGame(
            room_id="r1",
            room_type="public",
            is_rated=True,
            black_client_id="b",
            white_rating_delta=10,
            black_rating_delta=-10,
        )
        info = players_info_with_rating_result(room, record)
        by_id = {p["client_id"]: p for p in info}
        assert "rating_delta" not in by_id["w"]
        assert by_id["b"]["rating_delta"] == -10

    def test_stale_room_rating_plus_delta(self):
        from backend.rating.service import players_info_with_rating_result

        room = {
            "players": {"w": "белый"},
            "player_meta": {
                "w": {"username": "alice", "is_anonymous": False, "rating": 1500},
            },
        }
        record = FinishedGame(
            room_id="r1",
            room_type="public",
            is_rated=True,
            white_client_id="w",
            white_rating_delta=10,
            black_rating_delta=-10,
        )
        info = players_info_with_rating_result(room, record)
        assert info[0]["rating"] == 1510
        assert info[0]["rating_delta"] == 10


@pytest.mark.asyncio
class TestApplyRating:
    async def test_updates_both_users_and_record(self):
        white_id = await create_test_user()
        black_id = await create_test_user()
        factory = get_session_factory()
        async with factory() as session:
            white = await session.get(User, white_id)
            black = await session.get(User, black_id)
            white.rated_games_count = 50
            black.rated_games_count = 50
            await session.commit()

        record = FinishedGame(room_id="apply1", room_type="public")
        factory = get_session_factory()
        async with factory() as session:
            session.add(record)
            await session.flush()
            await apply_rating(
                session,
                record,
                white_user_id=white_id,
                black_user_id=black_id,
                score_white=1.0,
                moves_count=20,
                finished_at=_APPLY_AT,
            )
            await session.commit()

        async with factory() as session:
            white = await session.get(User, white_id)
            black = await session.get(User, black_id)
            assert white.rating == 1210
            assert black.rating == 1190
            assert white.rated_games_count == 51
            assert black.rated_games_count == 51
        assert record.is_rated is True
        assert record.white_rating_delta == 10
        assert record.black_rating_delta == -10

    async def test_missing_white_user_no_op(self):
        black_id = await create_test_user()
        record = FinishedGame(room_id="apply2", room_type="public")
        factory = get_session_factory()
        async with factory() as session:
            session.add(record)
            await session.flush()
            await apply_rating(
                session,
                record,
                white_user_id=uuid.uuid4(),
                black_user_id=black_id,
                score_white=1.0,
                moves_count=20,
                finished_at=_APPLY_AT,
            )
            await session.commit()

        async with factory() as session:
            black = await session.get(User, black_id)
            assert black.rating == 1200
            assert black.rated_games_count == 0
        assert record.is_rated is False

    async def test_missing_black_user_no_op(self):
        white_id = await create_test_user()
        record = FinishedGame(room_id="apply3", room_type="public")
        factory = get_session_factory()
        async with factory() as session:
            session.add(record)
            await session.flush()
            await apply_rating(
                session,
                record,
                white_user_id=white_id,
                black_user_id=uuid.uuid4(),
                score_white=1.0,
                moves_count=20,
                finished_at=_APPLY_AT,
            )
            await session.commit()

        async with factory() as session:
            white = await session.get(User, white_id)
            assert white.rating == 1200
            assert white.rated_games_count == 0
        assert record.is_rated is False

    async def test_draw_increments_games_count(self):
        white_id = await create_test_user()
        black_id = await create_test_user()
        record = FinishedGame(room_id="apply4", room_type="public")
        factory = get_session_factory()
        async with factory() as session:
            session.add(record)
            await session.flush()
            await apply_rating(
                session,
                record,
                white_user_id=white_id,
                black_user_id=black_id,
                score_white=0.5,
                moves_count=20,
                finished_at=_APPLY_AT,
            )
            await session.commit()

        async with factory() as session:
            white = await session.get(User, white_id)
            black = await session.get(User, black_id)
            assert white.rating == 1200
            assert black.rating == 1200
            assert white.rated_games_count == 1
            assert black.rated_games_count == 1
        assert record.white_rating_delta == 0
        assert record.black_rating_delta == 0
