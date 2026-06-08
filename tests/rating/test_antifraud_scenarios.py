"""Сценарные тесты анти-буста Elo (по запросу пользователя)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from backend.auth.service import user_to_public
from backend.db.models import FinishedGame, User
from backend.db.session import get_session_factory
from backend.rating.antifraud import GAIN_BLOCK_DURATION
from backend.rating.service import apply_rating
from tests.rating.conftest import create_test_user

BASE_TIME = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)


@dataclass
class GameOutcome:
    white_delta: int
    black_delta: int
    white_rating: int
    black_rating: int
    white_blocked_until: datetime | None
    white_gain_capped: bool
    black_gain_capped: bool


async def _set_user_games(user_id: uuid.UUID, rated_games_count: int) -> None:
    factory = get_session_factory()
    async with factory() as session:
        user = await session.get(User, user_id)
        assert user is not None
        user.rated_games_count = rated_games_count
        await session.commit()


async def _play_rated_win(
    winner_id: uuid.UUID,
    loser_id: uuid.UUID,
    *,
    moves_count: int = 20,
    loser_games_before: int | None = None,
    finished_at: datetime,
    game_index: int = 0,
) -> GameOutcome:
    """Winner always plays white; simulates archive_finished_game rating path."""
    if loser_games_before is not None:
        await _set_user_games(loser_id, loser_games_before)

    factory = get_session_factory()
    record = FinishedGame(
        room_id=f"scn{game_index:04d}",
        room_type="public",
        white_user_id=winner_id,
        black_user_id=loser_id,
        winner_color="белый",
        moves_count=moves_count,
        finished_at=finished_at,
    )
    async with factory() as session:
        session.add(record)
        await session.flush()
        await apply_rating(
            session,
            record,
            white_user_id=winner_id,
            black_user_id=loser_id,
            score_white=1.0,
            moves_count=moves_count,
            finished_at=finished_at,
        )
        await session.commit()
        await session.refresh(record)

    async with factory() as session:
        white = await session.get(User, winner_id)
        black = await session.get(User, loser_id)
        assert white is not None and black is not None
        return GameOutcome(
            white_delta=record.white_rating_delta or 0,
            black_delta=record.black_rating_delta or 0,
            white_rating=white.rating,
            black_rating=black.rating,
            white_blocked_until=white.rating_gain_blocked_until,
            white_gain_capped=record.white_gain_capped,
            black_gain_capped=record.black_gain_capped,
        )


def _t(minutes: int) -> datetime:
    return BASE_TIME + timedelta(minutes=minutes)


@pytest.mark.asyncio
class TestScenario1PairLimitAB:
    """
    A побеждает B×2, V, проигрывает C, побеждает B×2.
    4-я победа над B без прироста; затем B побеждает A — очки снимаются/начисляются.
    """

    async def test_pair_limit_sequence(self):
        a_id = await create_test_user("player_a")
        b_id = await create_test_user("player_b")
        v_id = await create_test_user("player_v")
        c_id = await create_test_user("player_c")

        for both in (a_id, b_id, v_id, c_id):
            await _set_user_games(both, 50)

        r1 = await _play_rated_win(a_id, b_id, finished_at=_t(0), game_index=1)
        assert r1.white_delta > 0
        assert r1.black_delta < 0

        r2 = await _play_rated_win(a_id, b_id, finished_at=_t(10), game_index=2)
        assert r2.white_delta > 0

        r3 = await _play_rated_win(a_id, v_id, finished_at=_t(20), game_index=3)
        assert r3.white_delta > 0

        r4 = await _play_rated_win(c_id, a_id, finished_at=_t(30), game_index=4)
        assert r4.white_delta > 0
        assert r4.black_delta < 0
        a_rating_after_loss = r4.black_rating

        r5 = await _play_rated_win(a_id, b_id, finished_at=_t(40), game_index=5)
        assert r5.white_delta > 0, "3-я победа A над B за 24ч всё ещё даёт Elo"

        r6 = await _play_rated_win(a_id, b_id, finished_at=_t(50), game_index=6)
        assert r6.white_delta == 0, "4-я победа A над B не должна давать Elo"
        assert r6.black_delta < 0, "B всё равно теряет очки"
        assert r6.white_gain_capped is True
        a_rating_after_cap = r6.white_rating

        r7 = await _play_rated_win(b_id, a_id, finished_at=_t(60), game_index=7)
        assert r7.white_delta > 0, "B должен получить Elo за победу над A"
        assert r7.black_delta < 0, "A должен потерять Elo"
        assert r7.black_rating < a_rating_after_cap
        assert r7.black_rating < a_rating_after_loss or r7.black_delta < 0


@pytest.mark.asyncio
class TestScenario2SmurfFarmTriggersBlock:
    """
    D: быстрые победы над G(2 игры), H(1), F(0, 3 хода), U(2).
    3-я квалифицирующая (F) даёт +Elo; 4-я (U) — блок и предупреждение в API.
    """

    async def test_smurf_block_after_three_qualifying_wins(self):
        d_id = await create_test_user("player_d")
        g_id = await create_test_user("player_g")
        h_id = await create_test_user("player_h")
        f_id = await create_test_user("player_f")
        u_id = await create_test_user("player_u")

        await _set_user_games(d_id, 50)

        r1 = await _play_rated_win(
            d_id, g_id, moves_count=6, loser_games_before=2, finished_at=_t(0), game_index=11
        )
        assert r1.white_delta > 0
        assert r1.white_blocked_until is None

        r2 = await _play_rated_win(
            d_id, h_id, moves_count=9, loser_games_before=1, finished_at=_t(10), game_index=12
        )
        assert r2.white_delta > 0
        assert r2.white_blocked_until is None

        r3 = await _play_rated_win(
            d_id, f_id, moves_count=3, loser_games_before=0, finished_at=_t(20), game_index=13
        )
        assert r3.white_delta > 0, "3-я smurf-победа всё ещё даёт Elo"
        assert r3.white_blocked_until is None

        r4 = await _play_rated_win(
            d_id, u_id, moves_count=5, loser_games_before=2, finished_at=_t(30), game_index=14
        )
        assert r4.white_delta == 0, "4-я smurf-победа без прироста"
        assert r4.white_gain_capped is True
        assert r4.white_blocked_until == _t(30) + GAIN_BLOCK_DURATION

        factory = get_session_factory()
        async with factory() as session:
            d_user = await session.get(User, d_id)
            assert d_user is not None
            public = user_to_public(d_user)
            assert public.rating_gain_blocked_until is not None
            assert public.rating_gain_blocked_until > _t(30)


@pytest.mark.asyncio
class TestScenario3MixedOpponentsSmurfBlock:
    """
    D: G(2,6 ходов), H(6 игр — не smurf), F(0,3 хода), U(2,5 ходов), Z(7,8 ходов).
    U — 3-я квалифицирующая (+Elo). Z — не smurf, обычный прирост, блока нет.
    """

    async def test_mixed_smurf_sequence(self):
        d_id = await create_test_user("player_d2")
        g_id = await create_test_user("player_g2")
        h_id = await create_test_user("player_h6")
        f_id = await create_test_user("player_f2")
        u_id = await create_test_user("player_u2")
        z_id = await create_test_user("player_z7")

        await _set_user_games(d_id, 50)

        r1 = await _play_rated_win(
            d_id, g_id, moves_count=6, loser_games_before=2, finished_at=_t(0), game_index=21
        )
        assert r1.white_delta > 0

        r2 = await _play_rated_win(
            d_id, h_id, moves_count=9, loser_games_before=6, finished_at=_t(10), game_index=22
        )
        assert r2.white_delta > 0, "победа над H (6 игр) — обычный Elo, не smurf"

        r3 = await _play_rated_win(
            d_id, f_id, moves_count=3, loser_games_before=0, finished_at=_t(20), game_index=23
        )
        assert r3.white_delta > 0, "2-я smurf-победа (G, F) — с приростом"
        assert r3.white_blocked_until is None

        r4 = await _play_rated_win(
            d_id, u_id, moves_count=5, loser_games_before=2, finished_at=_t(30), game_index=24
        )
        assert r4.white_delta > 0, "3-я smurf-победа (G, F, U) — с приростом"
        assert r4.white_blocked_until is None

        r5 = await _play_rated_win(
            d_id, z_id, moves_count=8, loser_games_before=7, finished_at=_t(40), game_index=25
        )
        assert r5.white_delta > 0, "Z не smurf — обычный прирост"
        assert r5.white_blocked_until is None

        factory = get_session_factory()
        async with factory() as session:
            d_user = await session.get(User, d_id)
            assert d_user is not None
            public = user_to_public(d_user)
            assert public.rating_gain_blocked_until is None


@pytest.mark.asyncio
class TestScenario4FourthSmurfWinTriggersBlock:
    """
    D: G(2,6), H(6,9 — не smurf), F(0,3), U(2,5), Z(1,8).
    U — 3-я smurf (+Elo). Z — 4-я smurf (блок, предупреждение, без +Elo).
    """

    async def test_fourth_smurf_on_z_triggers_warning(self):
        d_id = await create_test_user("player_d4")
        g_id = await create_test_user("player_g4")
        h_id = await create_test_user("player_h4")
        f_id = await create_test_user("player_f4")
        u_id = await create_test_user("player_u4")
        z_id = await create_test_user("player_z1")

        await _set_user_games(d_id, 50)

        r1 = await _play_rated_win(
            d_id, g_id, moves_count=6, loser_games_before=2, finished_at=_t(0), game_index=31
        )
        assert r1.white_delta > 0

        r2 = await _play_rated_win(
            d_id, h_id, moves_count=9, loser_games_before=6, finished_at=_t(10), game_index=32
        )
        assert r2.white_delta > 0

        r3 = await _play_rated_win(
            d_id, f_id, moves_count=3, loser_games_before=0, finished_at=_t(20), game_index=33
        )
        assert r3.white_delta > 0

        r4 = await _play_rated_win(
            d_id, u_id, moves_count=5, loser_games_before=2, finished_at=_t(30), game_index=34
        )
        assert r4.white_delta > 0, "3-я smurf-победа (G, F, U) — с приростом"
        assert r4.white_blocked_until is None

        r5 = await _play_rated_win(
            d_id, z_id, moves_count=8, loser_games_before=1, finished_at=_t(40), game_index=35
        )
        assert r5.white_delta == 0, "4-я smurf-победа (Z) — без прироста"
        assert r5.white_gain_capped is True
        assert r5.white_blocked_until == _t(40) + GAIN_BLOCK_DURATION

        factory = get_session_factory()
        async with factory() as session:
            d_user = await session.get(User, d_id)
            assert d_user is not None
            public = user_to_public(d_user)
            assert public.rating_gain_blocked_until is not None
            assert public.rating_gain_blocked_until > _t(40)
