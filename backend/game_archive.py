"""Persist finished games to PostgreSQL for later analysis."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from backend.board_utils import keys_int_to_str
from backend.db.models import FinishedGame
from backend.db.session import get_session_factory
from backend.observability.errors import capture_exception
from backend.observability.metrics import record_archive_error, record_game_finished
from backend.rating.service import apply_rating, is_rated_match, players_info_with_rating_result, score_for_color
from backend.state import get_game, get_room, set_game

logger = logging.getLogger(__name__)

ARCHIVABLE_ROOM_TYPES = frozenset({"public", "private", "ai"})


def mark_game_started(room_data: dict) -> None:
    room_data["game_started_at"] = datetime.now(timezone.utc).isoformat()


def _parse_started_at(room_data: dict) -> datetime | None:
    raw = room_data.get("game_started_at")
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _side_for_color(room_data: dict, color: str) -> dict:
    players = room_data.get("players") or {}
    meta_map = room_data.get("player_meta") or {}
    client_id = next((cid for cid, c in players.items() if c == color), None)

    if not client_id:
        return {
            "user_id": None,
            "client_id": None,
            "username": None,
            "is_anonymous": False,
        }

    meta = meta_map.get(client_id) or {}
    user_id = None
    raw_uid = meta.get("user_id")
    if raw_uid:
        try:
            user_id = uuid.UUID(str(raw_uid))
        except ValueError:
            user_id = None
    return {
        "user_id": user_id,
        "client_id": client_id,
        "username": meta.get("username"),
        "is_anonymous": bool(meta.get("is_anonymous", False)),
    }


def filter_move_history(game: dict) -> list[dict]:
    """Same filtering as build_move_response — skip junk/duplicate desk entries."""
    filtered: list[dict] = []
    last_desk = None
    for entry in game.get("move_history") or []:
        desk = entry.get("desk")
        if not entry.get("from_pos") or not entry.get("to_pos") or not desk:
            continue
        if last_desk is not None and desk == last_desk:
            continue
        filtered.append({**entry})
        last_desk = desk
    for i, entry in enumerate(filtered, start=1):
        entry["move_number"] = i
    return filtered


def _normalize_winner_color(game: dict) -> str | None:
    winner = game.get("winner_color")
    if winner is None:
        winner = game.get("winner")
    if not winner:
        return None
    return str(winner)


async def archive_finished_game(room_id: str) -> uuid.UUID | None:
    """Insert finished game if eligible and not yet archived."""
    try:
        game = await get_game(room_id)
        room_data = await get_room(room_id)
        if not game or not room_data:
            return None
        if not game.get("game_over"):
            return None
        if game.get("archived"):
            return None

        room_type = room_data.get("type")
        if room_type not in ARCHIVABLE_ROOM_TYPES:
            return None

        reason = game.get("reason") or ""
        if reason == "cancelled":
            return None

        move_history = filter_move_history(game)
        white = _side_for_color(room_data, "белый")
        black = _side_for_color(room_data, "черный")
        finished_at = datetime.now(timezone.utc)
        started_at = _parse_started_at(room_data)
        plies = len(move_history)
        duration_seconds = None
        if started_at is not None:
            duration_seconds = max(0.0, (finished_at - started_at).total_seconds())

        winner_color = _normalize_winner_color(game)
        record = FinishedGame(
            room_id=room_id,
            room_type=room_type,
            white_user_id=white["user_id"],
            black_user_id=black["user_id"],
            white_client_id=white["client_id"],
            black_client_id=black["client_id"],
            white_is_anonymous=white["is_anonymous"],
            black_is_anonymous=black["is_anonymous"],
            winner_color=winner_color,
            reason=reason or None,
            time_control=room_data.get("time_control"),
            increment=room_data.get("increment"),
            timer_white_final=room_data.get("timer_white"),
            timer_black_final=room_data.get("timer_black"),
            moves_count=len(move_history),
            move_history=move_history,
            final_board=keys_int_to_str(game.get("board") or {}),
            started_at=started_at,
            finished_at=finished_at,
        )

        factory = get_session_factory()
        async with factory() as session:
            session.add(record)
            if is_rated_match(room_data, white, black):
                score_white = score_for_color("белый", winner_color, reason or None)
                await apply_rating(
                    session,
                    record,
                    white_user_id=white["user_id"],
                    black_user_id=black["user_id"],
                    score_white=score_white,
                    moves_count=len(move_history),
                    finished_at=finished_at,
                )
            await session.commit()
            await session.refresh(record)
            record_id = record.id

        game["archived"] = True
        await set_game(room_id, game)
        record_game_finished(
            reason=reason or "unknown",
            room_type=room_type,
            plies=plies,
            duration_seconds=duration_seconds,
        )
        logger.info("Archived finished game %s for room %s", record_id, room_id)
        if record.is_rated:
            await _broadcast_rating_update(room_id, room_data, record)
        return record_id
    except Exception:
        record_archive_error()
        logger.exception("Failed to archive game for room %s", room_id)
        capture_exception()
        return None


async def on_game_finished(room_id: str) -> None:
    await archive_finished_game(room_id)


async def _broadcast_rating_update(room_id: str, room_data: dict, record: FinishedGame) -> None:
    from backend.ws_manager import manager

    players_info = players_info_with_rating_result(room_data, record)
    await manager.send_to_room(room_id, {
        "type": "rating_update",
        "players_info": players_info,
    })
