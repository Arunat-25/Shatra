"""User game history from finished_games."""

from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models import FinishedGame

ResultKind = Literal["win", "loss", "draw"]
ColorKind = Literal["белый", "черный"]


def _derive_result(
    *,
    my_color: ColorKind,
    winner_color: str | None,
    reason: str | None,
) -> ResultKind:
    if reason in ("draw_agreed",) or winner_color is None:
        return "draw"
    if winner_color == my_color:
        return "win"
    return "loss"


def _opponent_display(
    game: FinishedGame,
    *,
    my_color: ColorKind,
) -> str:
    if game.room_type == "ai":
        return "__ai__"
    if my_color == "белый":
        if game.black_is_anonymous or game.black_user is None:
            return "__anonymous__"
        return game.black_user.username
    if game.white_is_anonymous or game.white_user is None:
        return "__anonymous__"
    return game.white_user.username


async def list_user_games(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    base_filter = or_(
        FinishedGame.white_user_id == user_id,
        FinishedGame.black_user_id == user_id,
    )

    total = int(
        (await db.scalar(select(func.count()).select_from(FinishedGame).where(base_filter)))
        or 0
    )

    stmt = (
        select(FinishedGame)
        .where(base_filter)
        .options(
            selectinload(FinishedGame.white_user),
            selectinload(FinishedGame.black_user),
        )
        .order_by(FinishedGame.finished_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.scalars(stmt)).all()

    items: list[dict] = []
    for game in rows:
        if game.white_user_id == user_id:
            my_color: ColorKind = "белый"
        else:
            my_color = "черный"
        items.append(
            {
                "id": game.id,
                "room_id": game.room_id,
                "room_type": game.room_type,
                "finished_at": game.finished_at,
                "started_at": game.started_at,
                "my_color": my_color,
                "result": _derive_result(
                    my_color=my_color,
                    winner_color=game.winner_color,
                    reason=game.reason,
                ),
                "reason": game.reason,
                "opponent_display": _opponent_display(game, my_color=my_color),
                "moves_count": game.moves_count,
                "time_control": game.time_control,
                "increment": game.increment,
            }
        )
    return items, total


async def get_user_game(
    db: AsyncSession,
    user_id: uuid.UUID,
    game_id: uuid.UUID,
) -> FinishedGame | None:
    stmt = (
        select(FinishedGame)
        .where(
            FinishedGame.id == game_id,
            or_(
                FinishedGame.white_user_id == user_id,
                FinishedGame.black_user_id == user_id,
            ),
        )
        .options(
            selectinload(FinishedGame.white_user),
            selectinload(FinishedGame.black_user),
        )
    )
    return await db.scalar(stmt)
