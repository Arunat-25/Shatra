"""Разнообразные сценарии анти-буста: пары, smurf, блок, границы, комбинации."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.auth.service import user_to_public
from backend.db.models import User
from backend.db.session import get_session_factory
from backend.rating.antifraud import (
    GAIN_BLOCK_DURATION,
    PAIR_WIN_GAIN_LIMIT,
    SMURF_ALLOWED_WINS,
    is_smurf_qualifying_win,
)
from tests.rating.antifraud_helpers import (
    insert_prior_rated_win,
    play_draw,
    play_rated_game,
    play_win,
    set_user_block,
    set_user_games,
)
from tests.rating.conftest import create_test_user

T0 = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)


def _t(minutes: int = 0, hours: int = 0) -> datetime:
    return T0 + timedelta(hours=hours, minutes=minutes)


class TestSmurfQualifyingBoundaries:
    @pytest.mark.parametrize(
        ("moves", "loser_games", "expected"),
        [
            (1, 0, True),
            (10, 3, True),
            (10, 0, True),
            (11, 3, False),
            (5, 4, False),
            (8, 7, False),
            (0, 0, True),
        ],
    )
    def test_is_smurf_qualifying_boundaries(self, moves, loser_games, expected):
        assert is_smurf_qualifying_win(moves, loser_games) is expected


@pytest.mark.asyncio
class TestPairLimitVariants:
    async def test_exactly_three_wins_over_pair_all_grant_elo(self):
        winner = await create_test_user("pair3w")
        loser = await create_test_user("pair3l")
        await set_user_games(winner, 50)
        await set_user_games(loser, 50)

        for i in range(PAIR_WIN_GAIN_LIMIT):
            r = await play_win(
                winner, loser, finished_at=_t(minutes=i * 5), game_index=i + 100
            )
            assert r.white_delta > 0, f"win {i + 1} should grant Elo"

    async def test_fourth_win_capped_loser_still_loses(self):
        winner = await create_test_user("pair4w")
        loser = await create_test_user("pair4l")
        await set_user_games(winner, 50)
        await set_user_games(loser, 50)

        for i in range(PAIR_WIN_GAIN_LIMIT):
            await play_win(winner, loser, finished_at=_t(minutes=i * 5), game_index=110 + i)

        r4 = await play_win(winner, loser, finished_at=_t(30), game_index=114)
        assert r4.white_delta == 0
        assert r4.black_delta < 0
        assert r4.white_gain_capped is True

    async def test_pair_limits_are_independent_per_opponent(self):
        booster = await create_test_user("multi_boost")
        victim1 = await create_test_user("victim1")
        victim2 = await create_test_user("victim2")
        for uid in (booster, victim1, victim2):
            await set_user_games(uid, 50)

        for i in range(PAIR_WIN_GAIN_LIMIT + 1):
            await play_win(
                booster, victim1, finished_at=_t(minutes=i * 3), game_index=200 + i
            )

        capped = await play_win(booster, victim1, finished_at=_t(20), game_index=204)
        assert capped.white_delta == 0

        fresh = await play_win(booster, victim2, finished_at=_t(25), game_index=205)
        assert fresh.white_delta > 0, "лимит пар привязан к сопернику, не к игроку"

    async def test_wins_outside_rolling_window_do_not_count(self):
        winner = await create_test_user("roll_w")
        loser = await create_test_user("roll_l")
        await set_user_games(winner, 50)
        await set_user_games(loser, 50)

        for i in range(PAIR_WIN_GAIN_LIMIT):
            await insert_prior_rated_win(
                winner_id=winner,
                loser_id=loser,
                finished_at=_t(hours=-25 - i),
            )

        r = await play_win(winner, loser, finished_at=_t(0), game_index=300)
        assert r.white_delta > 0, "старые победы вне 24ч не учитываются"

    async def test_unrated_prior_games_do_not_count_toward_pair_limit(self):
        winner = await create_test_user("unrated_w")
        loser = await create_test_user("unrated_l")
        await set_user_games(winner, 50)
        await set_user_games(loser, 50)

        for i in range(5):
            await insert_prior_rated_win(
                winner_id=winner,
                loser_id=loser,
                finished_at=_t(minutes=i),
                is_rated=False,
            )

        r = await play_win(winner, loser, finished_at=_t(30), game_index=310)
        assert r.white_delta > 0

    async def test_black_winning_as_winner_not_capped_by_victims_prior_wins(self):
        dominant = await create_test_user("dominant")
        underdog = await create_test_user("underdog")
        await set_user_games(dominant, 50)
        await set_user_games(underdog, 50)

        for i in range(PAIR_WIN_GAIN_LIMIT):
            await play_win(
                dominant, underdog, finished_at=_t(minutes=i * 4), game_index=320 + i
            )

        comeback = await play_win(
            underdog,
            dominant,
            winner_is_white=False,
            finished_at=_t(25),
            game_index=324,
        )
        assert comeback.black_delta > 0
        assert comeback.white_delta < 0
        assert comeback.black_gain_capped is False

    async def test_draw_after_pair_exhausted_still_applies_elo(self):
        farmer = await create_test_user("draw_farmer")
        victim = await create_test_user("draw_victim")
        await set_user_games(farmer, 50)
        await set_user_games(victim, 50)
        factory = get_session_factory()
        async with factory() as session:
            w = await session.get(User, farmer)
            b = await session.get(User, victim)
            assert w and b
            w.rating = 1400
            b.rating = 1800
            await session.commit()

        for i in range(PAIR_WIN_GAIN_LIMIT):
            await play_win(farmer, victim, finished_at=_t(minutes=i * 3), game_index=330 + i)

        draw = await play_draw(farmer, victim, finished_at=_t(20), game_index=334)
        assert draw.white_delta != 0 or draw.black_delta != 0
        assert draw.white_gain_capped is False


@pytest.mark.asyncio
class TestSmurfFarmVariants:
    async def test_three_qualifying_wins_grant_elo_fourth_blocks(self):
        farmer = await create_test_user("smurf_farmer")
        await set_user_games(farmer, 50)
        losers = [await create_test_user(f"smurf_l{i}") for i in range(4)]

        for i in range(SMURF_ALLOWED_WINS):
            r = await play_win(
                farmer,
                losers[i],
                moves_count=5 + i,
                loser_games_before=i,
                finished_at=_t(minutes=i * 8),
                game_index=400 + i,
            )
            assert r.white_delta > 0
            assert r.white_blocked_until is None

        blocked = await play_win(
            farmer,
            losers[3],
            moves_count=7,
            loser_games_before=1,
            finished_at=_t(40),
            game_index=404,
        )
        assert blocked.white_delta == 0
        assert blocked.white_blocked_until == _t(40) + GAIN_BLOCK_DURATION

    async def test_long_games_do_not_count_as_smurf_wins(self):
        farmer = await create_test_user("long_farmer")
        await set_user_games(farmer, 50)

        for i in range(3):
            loser = await create_test_user(f"long_l{i}")
            await play_win(
                farmer,
                loser,
                moves_count=50,
                loser_games_before=0,
                finished_at=_t(minutes=i * 5),
                game_index=410 + i,
            )

        smurf_loser = await create_test_user("long_smurf")
        r = await play_win(
            farmer,
            smurf_loser,
            moves_count=8,
            loser_games_before=0,
            finished_at=_t(20),
            game_index=413,
        )
        assert r.white_delta > 0
        assert r.white_blocked_until is None

    async def test_experienced_opponent_breaks_smurf_chain_but_next_qualifies(self):
        farmer = await create_test_user("chain_farmer")
        await set_user_games(farmer, 50)
        novice = await create_test_user("chain_nov")
        veteran = await create_test_user("chain_vet")

        await play_win(
            farmer, novice, moves_count=6, loser_games_before=1,
            finished_at=_t(0), game_index=420,
        )
        await play_win(
            farmer, veteran, moves_count=9, loser_games_before=20,
            finished_at=_t(10), game_index=421,
        )
        r3 = await play_win(
            farmer, novice, moves_count=4, loser_games_before=2,
            finished_at=_t(20), game_index=422,
        )
        assert r3.white_delta > 0
        assert r3.white_blocked_until is None

    async def test_fifth_smurf_while_blocked_stays_zero_without_extending_block_absurdly(self):
        farmer = await create_test_user("blocked5")
        await set_user_games(farmer, 50)
        losers = [await create_test_user(f"b5_l{i}") for i in range(5)]

        for i in range(SMURF_ALLOWED_WINS + 1):
            await play_win(
                farmer, losers[i], moves_count=5, loser_games_before=0,
                finished_at=_t(minutes=i * 5), game_index=430 + i,
            )

        block_time = _t(minutes=15) + GAIN_BLOCK_DURATION
        r5 = await play_win(
            farmer, losers[4], moves_count=6, loser_games_before=1,
            finished_at=_t(30), game_index=435,
        )
        assert r5.white_delta == 0
        assert r5.white_blocked_until == block_time

    async def test_expired_block_allows_gains_again(self):
        farmer = await create_test_user("expired_blk")
        opponent = await create_test_user("expired_opp")
        await set_user_games(farmer, 50)
        await set_user_games(opponent, 50)
        await set_user_block(farmer, _t(hours=-1))

        r = await play_win(
            farmer, opponent, moves_count=30,
            finished_at=_t(0), game_index=440,
        )
        assert r.white_delta > 0
        assert r.white_blocked_until is None or r.white_blocked_until <= _t(0)

    async def test_black_smurf_win_fourth_triggers_block_on_black(self):
        farmer = await create_test_user("black_smurf")
        await set_user_games(farmer, 50)
        losers = [await create_test_user(f"bs_l{i}") for i in range(4)]

        for i in range(SMURF_ALLOWED_WINS):
            await play_win(
                farmer, losers[i], winner_is_white=False,
                moves_count=6, loser_games_before=i,
                finished_at=_t(minutes=i * 6), game_index=450 + i,
            )

        r4 = await play_win(
            farmer, losers[3], winner_is_white=False,
            moves_count=8, loser_games_before=2,
            finished_at=_t(30), game_index=454,
        )
        assert r4.black_delta == 0
        assert r4.black_gain_capped is True
        assert r4.black_blocked_until == _t(30) + GAIN_BLOCK_DURATION


@pytest.mark.asyncio
class TestActiveBlockBehavior:
    async def test_blocked_player_wins_get_zero_opponent_loses_normally(self):
        blocked = await create_test_user("active_blk")
        opponent = await create_test_user("active_opp")
        await set_user_games(blocked, 50)
        await set_user_games(opponent, 50)
        await set_user_block(blocked, _t(hours=12))

        r = await play_win(
            blocked, opponent, moves_count=25,
            finished_at=_t(0), game_index=500,
        )
        assert r.white_delta == 0
        assert r.black_delta < 0
        assert r.white_gain_capped is True

    async def test_blocked_player_losing_still_loses_rating(self):
        blocked = await create_test_user("active_loss")
        opponent = await create_test_user("active_win")
        await set_user_games(blocked, 50)
        await set_user_games(opponent, 50)
        await set_user_block(blocked, _t(hours=12))

        r = await play_win(
            opponent, blocked, moves_count=25,
            finished_at=_t(0), game_index=501,
        )
        assert r.white_delta > 0
        assert r.black_delta < 0
        assert r.black_gain_capped is False

    async def test_api_exposes_block_for_ui_warning(self):
        user_id = await create_test_user("api_block")
        await set_user_block(user_id, _t(hours=6))

        factory = get_session_factory()
        async with factory() as session:
            user = await session.get(User, user_id)
            assert user is not None
            public = user_to_public(user)
            assert public.rating_gain_blocked_until is not None
            assert public.rating_gain_blocked_until > _t(0)


@pytest.mark.asyncio
class TestCombinedRules:
    async def test_pair_cap_and_active_block_both_zero_winner_gain(self):
        farmer = await create_test_user("combo_farmer")
        victim = await create_test_user("combo_victim")
        await set_user_games(farmer, 50)
        await set_user_games(victim, 50)
        await set_user_block(farmer, _t(hours=10))

        for i in range(PAIR_WIN_GAIN_LIMIT):
            await play_win(
                farmer, victim, finished_at=_t(minutes=i * 3), game_index=600 + i
            )

        r = await play_win(farmer, victim, finished_at=_t(20), game_index=604)
        assert r.white_delta == 0
        assert r.black_delta < 0

    async def test_pair_cap_does_not_block_unrelated_smurf_fourth(self):
        """4-я победа над парой ≠ smurf-блок, если smurf-счётчик < 4."""
        winner = await create_test_user("combo2_w")
        victim = await create_test_user("combo2_v")
        novice = await create_test_user("combo2_n")
        for uid in (winner, victim, novice):
            await set_user_games(uid, 50)

        for i in range(PAIR_WIN_GAIN_LIMIT + 1):
            await play_win(
                winner, victim, finished_at=_t(minutes=i * 2), game_index=610 + i
            )

        smurf = await play_win(
            winner, novice, moves_count=7, loser_games_before=0,
            finished_at=_t(15), game_index=615,
        )
        assert smurf.white_delta > 0
        assert smurf.white_blocked_until is None

    async def test_loser_rated_games_before_persisted_on_record(self):
        winner = await create_test_user("persist_w")
        loser = await create_test_user("persist_l")
        await set_user_games(winner, 50)
        await set_user_games(loser, 2)

        r = await play_win(
            winner, loser, moves_count=8, finished_at=_t(0), game_index=620,
        )
        assert r.loser_rated_games_before == 2

    async def test_rated_games_count_increments_even_when_gain_capped(self):
        winner = await create_test_user("inc_w")
        loser = await create_test_user("inc_l")
        await set_user_games(winner, 50)
        await set_user_games(loser, 50)

        for i in range(PAIR_WIN_GAIN_LIMIT + 1):
            await play_win(
                winner, loser, finished_at=_t(minutes=i * 2), game_index=630 + i
            )

        w = await _get_user(winner)
        l = await _get_user(loser)
        assert w.rated_games_count == 50 + PAIR_WIN_GAIN_LIMIT + 1
        assert l.rated_games_count == 50 + PAIR_WIN_GAIN_LIMIT + 1


@pytest.mark.asyncio
class TestDrawAndEdgeScores:
    async def test_draw_never_triggers_pair_or_smurf_caps(self):
        white = await create_test_user("draw_w")
        black = await create_test_user("draw_b")
        await set_user_games(white, 50)
        await set_user_games(black, 50)

        for i in range(5):
            await play_win(white, black, finished_at=_t(minutes=i), game_index=700 + i)

        draw = await play_draw(white, black, finished_at=_t(30), game_index=705)
        assert draw.white_gain_capped is False
        assert draw.black_gain_capped is False

    async def test_upset_win_under_pair_cap_still_zeros_only_positive(self):
        """Даже большой потенциальный прирост обнуляется при лимите пар."""
        giant = await create_test_user("giant")
        dwarf = await create_test_user("dwarf")
        await set_user_games(giant, 50)
        await set_user_games(dwarf, 50)
        async with get_session_factory()() as session:
            g = await session.get(User, giant)
            d = await session.get(User, dwarf)
            assert g and d
            g.rating = 1800
            d.rating = 1200
            await session.commit()

        for i in range(PAIR_WIN_GAIN_LIMIT):
            await play_win(giant, dwarf, finished_at=_t(minutes=i * 2), game_index=710 + i)

        r = await play_win(giant, dwarf, finished_at=_t(15), game_index=714)
        assert r.white_delta == 0
        assert r.black_delta < 0


async def _get_user(user_id: uuid.UUID) -> User:
    factory = get_session_factory()
    async with factory() as session:
        user = await session.get(User, user_id)
        assert user is not None
        return user
