"""Shared game-over flow: state, broadcast, timers, archive."""

from __future__ import annotations

from backend.state import get_game, get_room, set_game, set_room, get_room_lock
from backend.ws_manager import manager


async def finish_game(
    room_id: str,
    *,
    reason: str,
    winner_color: str | None,
    broadcast: dict,
    clear_rematch: bool = True,
    record_timeout_kind: str | None = None,
) -> bool:
    """Finish a game under the room lock. Returns True if the game was ended."""
    async with get_room_lock(room_id):
        return await _finish_game_locked(
            room_id,
            reason=reason,
            winner_color=winner_color,
            broadcast=broadcast,
            clear_rematch=clear_rematch,
            record_timeout_kind=record_timeout_kind,
        )


async def _finish_game_locked(
    room_id: str,
    *,
    reason: str,
    winner_color: str | None,
    broadcast: dict,
    clear_rematch: bool = True,
    record_timeout_kind: str | None = None,
) -> bool:
    """Finish a game. Caller must hold get_room_lock when invoked from locked contexts."""
    game = await get_game(room_id)
    if not game or game.get("game_over"):
        return False

    game["game_over"] = True
    if winner_color is not None:
        game["winner_color"] = winner_color
        game["winner"] = winner_color
    game["reason"] = reason
    game.pop("draw_offer_from", None)
    await set_game(room_id, game)

    if clear_rematch:
        room_data = await get_room(room_id)
        if room_data and room_data.get("type") != "ai":
            room_data["rematch_ready"] = []
            await set_room(room_id, room_data)

    from backend.timers import stop_game_timer

    stop_game_timer(room_id)

    if record_timeout_kind:
        from backend.observability.metrics import record_timeout

        record_timeout(record_timeout_kind)

    await manager.send_to_room(room_id, broadcast)

    from backend.game_archive import _archive_finished_game_locked

    await _archive_finished_game_locked(room_id)
    return True


async def complete_game_after_move(room_id: str) -> None:
    """Stop clock and archive after move processing already saved game_over state."""
    from backend.timers import stop_game_timer
    from backend.game_archive import _archive_finished_game_locked

    stop_game_timer(room_id)
    await _archive_finished_game_locked(room_id)
