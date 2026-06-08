"""Tests for backend.rating.antifraud — pair limits and smurf-farm block."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.db.models import FinishedGame, User
from backend.db.session import get_session_factory
from backend.rating.antifraud import (
    GAIN_BLOCK_DURATION,
    adjust_rating_deltas,
    apply_gain_block,
    cap_positive_delta,
    count_pair_wins,
    count_smurf_farm_wins,
    is_smurf_qualifying_win,
)
from backend.rating.elo import rating_deltas
from tests.rating.conftest import create_test_user

NOW = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)


async def _insert_rated_win(
    *,
    winner_id: uuid.UUID,
    loser_id: uuid.UUID,
    finished_at: datetime,
    moves_count: int = 5,
    loser_games_before: int = 0,
    winner_is_white: bool = True,
) -> None:
    factory = get_session_factory()
    async with factory() as session:
        if winner_is_white:
            record = FinishedGame(
                room_id=uuid.uuid4().hex[:8],
                room_type="public",
                white_user_id=winner_id,
                black_user_id=loser_id,
                winner_color="белый",
                is_rated=True,
                moves_count=moves_count,
                loser_rated_games_before=loser_games_before,
                white_rating_delta=10,
                black_rating_delta=-10,
                finished_at=finished_at,
            )
        else:
            record = FinishedGame(
                room_id=uuid.uuid4().hex[:8],
                room_type="public",
                white_user_id=loser_id,
                black_user_id=winner_id,
                winner_color="черный",
                is_rated=True,
                moves_count=moves_count,
                loser_rated_games_before=loser_games_before,
                white_rating_delta=-10,
                black_rating_delta=10,
                finished_at=finished_at,
            )
        session.add(record)
        await session.commit()


class TestAntifraudPure:
    def test_is_smurf_qualifying_win(self):
        assert is_smurf_qualifying_win(10, 3) is True
        assert is_smurf_qualifying_win(11, 3) is False
        assert is_smurf_qualifying_win(5, 4) is False

    def test_cap_positive_delta(self):
        assert cap_positive_delta(8) == (0, True)
        assert cap_positive_delta(0) == (0, False)
        assert cap_positive_delta(-5) == (-5, False)

    def test_apply_gain_block_active(self):
        user = User(
            id=uuid.uuid4(),
            username="u",
            username_normalized="u",
            password_hash="h",
            rating_gain_blocked_until=NOW + timedelta(hours=1),
        )
        delta, capped = apply_gain_block(10, user, NOW)
        assert delta == 0
        assert capped is True

    def test_apply_gain_block_losses_pass_through(self):
        user = User(
            id=uuid.uuid4(),
            username="u",
            username_normalized="u",
            password_hash="h",
            rating_gain_blocked_until=NOW + timedelta(hours=1),
        )
        delta, capped = apply_gain_block(-8, user, NOW)
        assert delta == -8
        assert capped is False


@pytest.mark.asyncio
class TestAntifraudCounts:
    async def test_count_pair_wins(self):
        winner_id = await create_test_user("winner_a")
        loser_id = await create_test_user("loser_b")
        since = NOW - timedelta(hours=24)
        for hours_ago in (20, 15, 10):
            await _insert_rated_win(
                winner_id=winner_id,
                loser_id=loser_id,
                finished_at=NOW - timedelta(hours=hours_ago),
            )
        factory = get_session_factory()
        async with factory() as session:
            assert await count_pair_wins(session, winner_id, loser_id, since) == 3

    async def test_count_smurf_farm_wins(self):
        winner_id = await create_test_user("smurf_winner")
        loser_id = await create_test_user("smurf_loser")
        since = NOW - timedelta(hours=24)
        for hours_ago in (22, 18):
            await _insert_rated_win(
                winner_id=winner_id,
                loser_id=loser_id,
                finished_at=NOW - timedelta(hours=hours_ago),
                moves_count=8,
                loser_games_before=1,
            )
        factory = get_session_factory()
        async with factory() as session:
            assert await count_smurf_farm_wins(session, winner_id, since) == 2


@pytest.mark.asyncio
class TestAdjustRatingDeltas:
    async def test_fourth_pair_win_caps_winner_only(self):
        winner_id = await create_test_user("pair_winner")
        loser_id = await create_test_user("pair_loser")
        for hours_ago in (20, 15, 10):
            await _insert_rated_win(
                winner_id=winner_id,
                loser_id=loser_id,
                finished_at=NOW - timedelta(hours=hours_ago),
            )

        factory = get_session_factory()
        async with factory() as session:
            white = await session.get(User, winner_id)
            black = await session.get(User, loser_id)
            assert white is not None and black is not None
            white.rated_games_count = 50
            black.rated_games_count = 50
            await session.commit()

            white = await session.get(User, winner_id)
            black = await session.get(User, loser_id)
            raw_w, raw_b = rating_deltas(
                white.rating, black.rating, white.rated_games_count, black.rated_games_count, 1.0
            )
            assert raw_w > 0 and raw_b < 0

            result = await adjust_rating_deltas(
                session,
                delta_white=raw_w,
                delta_black=raw_b,
                white=white,
                black=black,
                score_white=1.0,
                moves_count=20,
                finished_at=NOW,
            )

        assert result.delta_white == 0
        assert result.delta_black == raw_b
        assert result.white_gain_capped is True

    async def test_loser_win_not_capped_by_pair_limit(self):
        a_id = await create_test_user("player_a")
        b_id = await create_test_user("player_b")
        for hours_ago in (20, 15, 10):
            await _insert_rated_win(
                winner_id=a_id,
                loser_id=b_id,
                finished_at=NOW - timedelta(hours=hours_ago),
            )

        factory = get_session_factory()
        async with factory() as session:
            white = await session.get(User, b_id)
            black = await session.get(User, a_id)
            assert white is not None and black is not None
            white.rated_games_count = 50
            black.rated_games_count = 50
            await session.commit()

            white = await session.get(User, b_id)
            black = await session.get(User, a_id)
            raw_w, raw_b = rating_deltas(
                white.rating, black.rating, white.rated_games_count, black.rated_games_count, 1.0
            )
            result = await adjust_rating_deltas(
                session,
                delta_white=raw_w,
                delta_black=raw_b,
                white=white,
                black=black,
                score_white=1.0,
                moves_count=20,
                finished_at=NOW,
            )

        assert result.delta_white == raw_w
        assert result.delta_black == raw_b
        assert result.white_gain_capped is False

    async def test_draw_not_capped_after_pair_limit(self):
        winner_id = await create_test_user("draw_w")
        loser_id = await create_test_user("draw_l")
        for hours_ago in (20, 15, 10):
            await _insert_rated_win(
                winner_id=winner_id,
                loser_id=loser_id,
                finished_at=NOW - timedelta(hours=hours_ago),
            )

        factory = get_session_factory()
        async with factory() as session:
            white = await session.get(User, winner_id)
            black = await session.get(User, loser_id)
            assert white is not None and black is not None
            white.rated_games_count = 50
            black.rated_games_count = 50
            white.rating = 1400
            black.rating = 1800
            await session.commit()

            white = await session.get(User, winner_id)
            black = await session.get(User, loser_id)
            raw_w, raw_b = rating_deltas(
                white.rating, black.rating, white.rated_games_count, black.rated_games_count, 0.5
            )
            result = await adjust_rating_deltas(
                session,
                delta_white=raw_w,
                delta_black=raw_b,
                white=white,
                black=black,
                score_white=0.5,
                moves_count=20,
                finished_at=NOW,
            )

        assert result.delta_white == raw_w
        assert result.delta_black == raw_b

    async def test_third_smurf_win_still_grants_gain(self):
        winner_id = await create_test_user("smurf_boost")
        loser_id = await create_test_user("fresh_acc")
        for hours_ago in (22, 18):
            await _insert_rated_win(
                winner_id=winner_id,
                loser_id=loser_id,
                finished_at=NOW - timedelta(hours=hours_ago),
                moves_count=6,
                loser_games_before=2,
            )

        factory = get_session_factory()
        async with factory() as session:
            white = await session.get(User, winner_id)
            black = await session.get(User, loser_id)
            assert white is not None and black is not None
            black.rated_games_count = 2
            await session.commit()

            white = await session.get(User, winner_id)
            black = await session.get(User, loser_id)
            raw_w, raw_b = rating_deltas(
                white.rating, black.rating, white.rated_games_count, black.rated_games_count, 1.0
            )
            result = await adjust_rating_deltas(
                session,
                delta_white=raw_w,
                delta_black=raw_b,
                white=white,
                black=black,
                score_white=1.0,
                moves_count=8,
                finished_at=NOW,
            )
            await session.commit()

        assert result.delta_white == raw_w
        assert result.delta_white > 0
        assert result.white_gain_capped is False
        async with factory() as session:
            user = await session.get(User, winner_id)
            assert user is not None
            assert user.rating_gain_blocked_until is None

    async def test_fourth_smurf_win_sets_block_and_zeros_gain(self):
        winner_id = await create_test_user("smurf_boost4")
        loser_id = await create_test_user("fresh_acc4")
        for hours_ago in (23, 19, 15):
            await _insert_rated_win(
                winner_id=winner_id,
                loser_id=loser_id,
                finished_at=NOW - timedelta(hours=hours_ago),
                moves_count=6,
                loser_games_before=2,
            )

        factory = get_session_factory()
        async with factory() as session:
            white = await session.get(User, winner_id)
            black = await session.get(User, loser_id)
            assert white is not None and black is not None
            black.rated_games_count = 1
            await session.commit()

            white = await session.get(User, winner_id)
            black = await session.get(User, loser_id)
            raw_w, raw_b = rating_deltas(
                white.rating, black.rating, white.rated_games_count, black.rated_games_count, 1.0
            )
            result = await adjust_rating_deltas(
                session,
                delta_white=raw_w,
                delta_black=raw_b,
                white=white,
                black=black,
                score_white=1.0,
                moves_count=8,
                finished_at=NOW,
            )
            await session.commit()

        assert result.delta_white == 0
        assert result.white_gain_capped is True
        async with factory() as session:
            user = await session.get(User, winner_id)
            assert user is not None
            assert user.rating_gain_blocked_until == NOW + GAIN_BLOCK_DURATION

    async def test_active_block_zeros_gain_not_loss(self):
        winner_id = await create_test_user("blocked_user")
        loser_id = await create_test_user("opponent_x")

        factory = get_session_factory()
        async with factory() as session:
            white = await session.get(User, winner_id)
            black = await session.get(User, loser_id)
            assert white is not None and black is not None
            white.rating_gain_blocked_until = NOW + timedelta(hours=12)
            white.rated_games_count = 50
            black.rated_games_count = 50
            await session.commit()

            white = await session.get(User, winner_id)
            black = await session.get(User, loser_id)
            raw_w, raw_b = rating_deltas(
                white.rating, black.rating, white.rated_games_count, black.rated_games_count, 1.0
            )
            win_result = await adjust_rating_deltas(
                session,
                delta_white=raw_w,
                delta_black=raw_b,
                white=white,
                black=black,
                score_white=1.0,
                moves_count=20,
                finished_at=NOW,
            )
            assert win_result.delta_white == 0

            white = await session.get(User, winner_id)
            black = await session.get(User, loser_id)
            raw_w, raw_b = rating_deltas(
                white.rating, black.rating, white.rated_games_count, black.rated_games_count, 0.0
            )
            loss_result = await adjust_rating_deltas(
                session,
                delta_white=raw_w,
                delta_black=raw_b,
                white=white,
                black=black,
                score_white=0.0,
                moves_count=20,
                finished_at=NOW,
            )
            assert loss_result.delta_white < 0
