"""Tests for backend.rating.service — eligibility and score mapping."""

from __future__ import annotations

import uuid

import pytest

from backend.db.models import FinishedGame
from backend.rating.elo import rating_deltas
from backend.rating.service import is_rated_match, score_for_color


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
