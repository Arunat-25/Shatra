"""Apply Elo rating updates after rated PvP games."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import FinishedGame, User
from backend.rating.antifraud import adjust_rating_deltas
from backend.rating.elo import rating_deltas

ColorKind = Literal["белый", "черный"]


def _both_registered(white: dict, black: dict) -> bool:
    return (
        white.get("user_id") is not None
        and black.get("user_id") is not None
        and not white.get("is_anonymous", False)
        and not black.get("is_anonymous", False)
    )


def is_rated_match(room_data: dict, white: dict, black: dict) -> bool:
    """Whether this finished game should affect player ratings."""
    room_type = room_data.get("type")
    if room_type not in ("public", "private"):
        return False
    if not _both_registered(white, black):
        return False
    if room_type == "public":
        return True
    return bool(room_data.get("rated", False))


def score_for_color(
    my_color: ColorKind,
    winner_color: str | None,
    reason: str | None,
) -> float:
    """Match score from the perspective of my_color: 1.0 / 0.5 / 0.0."""
    if reason == "draw_agreed" or not winner_color:
        return 0.5
    if winner_color == my_color:
        return 1.0
    return 0.0


async def apply_rating(
    session: AsyncSession,
    record: FinishedGame,
    *,
    white_user_id: uuid.UUID,
    black_user_id: uuid.UUID,
    score_white: float,
    moves_count: int,
    finished_at: datetime,
) -> None:
    """Load users with row lock, compute deltas, apply antifraud caps, update ratings."""
    white = await session.scalar(
        select(User).where(User.id == white_user_id).with_for_update()
    )
    black = await session.scalar(
        select(User).where(User.id == black_user_id).with_for_update()
    )
    if white is None or black is None:
        return

    delta_white, delta_black = rating_deltas(
        white.rating,
        black.rating,
        white.rated_games_count,
        black.rated_games_count,
        score_white,
    )

    adjusted = await adjust_rating_deltas(
        session,
        delta_white=delta_white,
        delta_black=delta_black,
        white=white,
        black=black,
        score_white=score_white,
        moves_count=moves_count,
        finished_at=finished_at,
    )

    white.rating += adjusted.delta_white
    black.rating += adjusted.delta_black
    white.rated_games_count += 1
    black.rated_games_count += 1

    record.is_rated = True
    record.white_rating_delta = adjusted.delta_white
    record.black_rating_delta = adjusted.delta_black
    record.loser_rated_games_before = adjusted.loser_rated_games_before
    record.white_gain_capped = adjusted.white_gain_capped
    record.black_gain_capped = adjusted.black_gain_capped


def players_info_with_rating_result(room_data: dict, record: FinishedGame) -> list[dict]:
    """Build players_info with post-game rating and per-player delta."""
    from backend.player_identity import build_players_info

    info = build_players_info(room_data)
    if not record.is_rated:
        return info

    deltas_by_client: dict[str, int | None] = {}
    if record.white_client_id:
        deltas_by_client[record.white_client_id] = record.white_rating_delta
    if record.black_client_id:
        deltas_by_client[record.black_client_id] = record.black_rating_delta

    for entry in info:
        delta = deltas_by_client.get(entry.get("client_id"))
        if delta is None:
            continue
        entry["rating_delta"] = delta
        if entry.get("rating") is not None:
            entry["rating"] = entry["rating"] + delta
    return info
