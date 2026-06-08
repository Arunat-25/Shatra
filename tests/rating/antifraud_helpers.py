"""Shared helpers for antifraud integration tests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from backend.db.models import FinishedGame, User
from backend.db.session import get_session_factory
from backend.rating.service import apply_rating


@dataclass
class RatedGameResult:
    white_delta: int
    black_delta: int
    white_rating: int
    black_rating: int
    white_blocked_until: datetime | None
    black_blocked_until: datetime | None
    white_gain_capped: bool
    black_gain_capped: bool
    loser_rated_games_before: int | None
    record_id: uuid.UUID


async def set_user_games(user_id: uuid.UUID, rated_games_count: int) -> None:
    factory = get_session_factory()
    async with factory() as session:
        user = await session.get(User, user_id)
        assert user is not None
        user.rated_games_count = rated_games_count
        await session.commit()


async def set_user_block(user_id: uuid.UUID, blocked_until: datetime | None) -> None:
    factory = get_session_factory()
    async with factory() as session:
        user = await session.get(User, user_id)
        assert user is not None
        user.rating_gain_blocked_until = blocked_until
        await session.commit()


async def insert_prior_rated_win(
    *,
    winner_id: uuid.UUID,
    loser_id: uuid.UUID,
    finished_at: datetime,
    moves_count: int = 12,
    loser_games_before: int = 10,
    winner_is_white: bool = True,
    is_rated: bool = True,
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
                is_rated=is_rated,
                moves_count=moves_count,
                loser_rated_games_before=loser_games_before if is_rated else None,
                white_rating_delta=10 if is_rated else None,
                black_rating_delta=-10 if is_rated else None,
                finished_at=finished_at,
            )
        else:
            record = FinishedGame(
                room_id=uuid.uuid4().hex[:8],
                room_type="public",
                white_user_id=loser_id,
                black_user_id=winner_id,
                winner_color="черный",
                is_rated=is_rated,
                moves_count=moves_count,
                loser_rated_games_before=loser_games_before if is_rated else None,
                white_rating_delta=-10 if is_rated else None,
                black_rating_delta=10 if is_rated else None,
                finished_at=finished_at,
            )
        session.add(record)
        await session.commit()


async def play_rated_game(
    white_id: uuid.UUID,
    black_id: uuid.UUID,
    *,
    score_white: float,
    moves_count: int = 20,
    loser_games_before: int | None = None,
    finished_at: datetime,
    game_index: int = 0,
    room_type: str = "public",
) -> RatedGameResult:
    if score_white == 1.0 and loser_games_before is not None:
        await set_user_games(black_id, loser_games_before)
    elif score_white == 0.0 and loser_games_before is not None:
        await set_user_games(white_id, loser_games_before)

    factory = get_session_factory()
    winner_color = "белый" if score_white == 1.0 else "черный" if score_white == 0.0 else None
    record = FinishedGame(
        room_id=f"af{game_index:05d}",
        room_type=room_type,
        white_user_id=white_id,
        black_user_id=black_id,
        winner_color=winner_color,
        moves_count=moves_count,
        finished_at=finished_at,
    )
    async with factory() as session:
        session.add(record)
        await session.flush()
        await apply_rating(
            session,
            record,
            white_user_id=white_id,
            black_user_id=black_id,
            score_white=score_white,
            moves_count=moves_count,
            finished_at=finished_at,
        )
        await session.commit()
        await session.refresh(record)
        record_id = record.id

    async with factory() as session:
        white = await session.get(User, white_id)
        black = await session.get(User, black_id)
        refreshed = await session.get(FinishedGame, record_id)
        assert white is not None and black is not None and refreshed is not None
        return RatedGameResult(
            white_delta=refreshed.white_rating_delta or 0,
            black_delta=refreshed.black_rating_delta or 0,
            white_rating=white.rating,
            black_rating=black.rating,
            white_blocked_until=white.rating_gain_blocked_until,
            black_blocked_until=black.rating_gain_blocked_until,
            white_gain_capped=refreshed.white_gain_capped,
            black_gain_capped=refreshed.black_gain_capped,
            loser_rated_games_before=refreshed.loser_rated_games_before,
            record_id=record_id,
        )


async def play_win(
    winner_id: uuid.UUID,
    loser_id: uuid.UUID,
    *,
    winner_is_white: bool = True,
    **kwargs,
) -> RatedGameResult:
    if winner_is_white:
        return await play_rated_game(winner_id, loser_id, score_white=1.0, **kwargs)
    return await play_rated_game(loser_id, winner_id, score_white=0.0, **kwargs)


async def play_draw(white_id: uuid.UUID, black_id: uuid.UUID, **kwargs) -> RatedGameResult:
    return await play_rated_game(white_id, black_id, score_white=0.5, **kwargs)
