"""Anti-boost rules: pair win limits and smurf-farm gain block."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import FinishedGame, User

PAIR_WIN_GAIN_LIMIT = 3
PAIR_WINDOW = timedelta(hours=24)
SMURF_OPPONENT_MAX_GAMES = 3
SMURF_MAX_MOVES = 10
SMURF_ALLOWED_WINS = 3  # first 3 qualifying wins per 24h still grant Elo
GAIN_BLOCK_DURATION = timedelta(hours=24)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def is_smurf_qualifying_win(moves_count: int, loser_rated_games_before: int) -> bool:
    return (
        moves_count <= SMURF_MAX_MOVES
        and loser_rated_games_before <= SMURF_OPPONENT_MAX_GAMES
    )


def cap_positive_delta(delta: int) -> tuple[int, bool]:
    if delta > 0:
        return 0, True
    return delta, False


def apply_gain_block(delta: int, user: User, now: datetime) -> tuple[int, bool]:
    """Zero positive delta while rating_gain_blocked_until is active."""
    blocked_until = user.rating_gain_blocked_until
    if delta > 0 and blocked_until is not None and _ensure_utc(blocked_until) > _ensure_utc(now):
        return 0, True
    return delta, False


def _pair_win_condition(winner_id: uuid.UUID, loser_id: uuid.UUID):
    white_wins = and_(
        FinishedGame.winner_color == "белый",
        FinishedGame.white_user_id == winner_id,
        FinishedGame.black_user_id == loser_id,
    )
    black_wins = and_(
        FinishedGame.winner_color == "черный",
        FinishedGame.black_user_id == winner_id,
        FinishedGame.white_user_id == loser_id,
    )
    return or_(white_wins, black_wins)


def _user_win_condition(user_id: uuid.UUID):
    return or_(
        and_(
            FinishedGame.winner_color == "белый",
            FinishedGame.white_user_id == user_id,
        ),
        and_(
            FinishedGame.winner_color == "черный",
            FinishedGame.black_user_id == user_id,
        ),
    )


async def count_pair_wins(
    session: AsyncSession,
    winner_id: uuid.UUID,
    loser_id: uuid.UUID,
    since: datetime,
) -> int:
    """Rated wins by winner over loser since `since` (excluding current game)."""
    q = select(func.count()).select_from(FinishedGame).where(
        FinishedGame.is_rated.is_(True),
        FinishedGame.finished_at >= since,
        _pair_win_condition(winner_id, loser_id),
    )
    return int(await session.scalar(q) or 0)


async def count_smurf_farm_wins(
    session: AsyncSession,
    winner_id: uuid.UUID,
    since: datetime,
) -> int:
    """Prior smurf-qualifying rated wins by user since `since`."""
    q = select(func.count()).select_from(FinishedGame).where(
        FinishedGame.is_rated.is_(True),
        FinishedGame.finished_at >= since,
        FinishedGame.moves_count <= SMURF_MAX_MOVES,
        FinishedGame.loser_rated_games_before <= SMURF_OPPONENT_MAX_GAMES,
        FinishedGame.loser_rated_games_before.isnot(None),
        _user_win_condition(winner_id),
    )
    return int(await session.scalar(q) or 0)


@dataclass
class AntifraudAdjustResult:
    delta_white: int
    delta_black: int
    white_gain_capped: bool
    black_gain_capped: bool
    loser_rated_games_before: int | None


async def adjust_rating_deltas(
    session: AsyncSession,
    *,
    delta_white: int,
    delta_black: int,
    white: User,
    black: User,
    score_white: float,
    moves_count: int,
    finished_at: datetime,
) -> AntifraudAdjustResult:
    """Apply pair cap, smurf-farm block trigger, and active gain block."""
    now = _ensure_utc(finished_at)
    since = now - PAIR_WINDOW

    dw, db = delta_white, delta_black
    white_capped = False
    black_capped = False
    loser_games_before: int | None = None

    if score_white == 1.0:
        winner, loser, delta_w, delta_b, winner_is_white = white, black, dw, db, True
    elif score_white == 0.0:
        winner, loser, delta_w, delta_b, winner_is_white = black, white, db, dw, False
    else:
        winner = loser = None
        winner_is_white = None

    if winner is not None and loser is not None:
        loser_games_before = loser.rated_games_count

        pair_wins = await count_pair_wins(session, winner.id, loser.id, since)
        if pair_wins >= PAIR_WIN_GAIN_LIMIT and delta_w > 0:
            delta_w, capped = cap_positive_delta(delta_w)
            if capped:
                if winner_is_white:
                    white_capped = True
                else:
                    black_capped = True

        if is_smurf_qualifying_win(moves_count, loser_games_before):
            smurf_wins_before = await count_smurf_farm_wins(session, winner.id, since)
            if smurf_wins_before >= SMURF_ALLOWED_WINS:
                if delta_w > 0:
                    delta_w, capped = cap_positive_delta(delta_w)
                    if capped:
                        if winner_is_white:
                            white_capped = True
                        else:
                            black_capped = True
                if smurf_wins_before == SMURF_ALLOWED_WINS:
                    new_block = now + GAIN_BLOCK_DURATION
                    existing = winner.rating_gain_blocked_until
                    if existing is None or _ensure_utc(existing) < new_block:
                        winner.rating_gain_blocked_until = new_block

        if winner_is_white:
            dw, db = delta_w, delta_b
        else:
            dw, db = delta_b, delta_w

    dw, capped = apply_gain_block(dw, white, now)
    if capped:
        white_capped = True
    db, capped = apply_gain_block(db, black, now)
    if capped:
        black_capped = True

    return AntifraudAdjustResult(
        delta_white=dw,
        delta_black=db,
        white_gain_capped=white_capped,
        black_gain_capped=black_capped,
        loser_rated_games_before=loser_games_before,
    )
