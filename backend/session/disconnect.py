import asyncio
import logging

from fastapi import WebSocket

from backend.state import (
    get_game,
    delete_game,
    get_room,
    set_room,
    delete_room,
    disconnect_timers,
    DISCONNECT_TIMEOUT,
    drop_room_lock,
)
from backend.session.v2.outbound import send_control_v1
from backend.ws_manager import manager
from backend.timers import stop_game_timer, disconnect_timer as dt_func

logger = logging.getLogger(__name__)


async def _cleanup_orphaned_tasks(room_id: str, *, drop_lock: bool = False) -> None:
    """Останавливает тикер и отменяет «висящие» disconnect-таймеры для комнаты."""
    stop_game_timer(room_id)
    prior = disconnect_timers.pop(room_id, None)
    if prior and not prior.done():
        prior.cancel()
    if drop_lock:
        drop_room_lock(room_id)


async def _remove_room_from_redis(room_id: str) -> None:
    """Удаляет room/game из Redis и освобождает связанные in-memory ресурсы."""
    await _cleanup_orphaned_tasks(room_id, drop_lock=True)
    await delete_game(room_id)
    await delete_room(room_id)
    manager.connections.pop(room_id, None)
    logger.info("Room %s removed from Redis", room_id)


async def _handle_finished_game_disconnect(
    room_id: str,
    disconnected_client_id: str | None,
    room_data: dict | None,
) -> None:
    """После game_over: реванш только пока оба на WS; иначе чистим Redis."""
    if room_data:
        room_data["rematch_ready"] = []
        await set_room(room_id, room_data)

    opponent = (
        manager.get_opponent_ws(room_id, disconnected_client_id)
        if disconnected_client_id
        else None
    )
    if opponent and disconnected_client_id:
        opponent_cid = next(
            (cid for cid, ws in manager.connections.get(room_id, {}).items()
             if cid != disconnected_client_id and ws is opponent),
            None,
        )
        if opponent_cid:
            try:
                await send_control_v1(room_id, opponent_cid, opponent, {
                    "status": "rematch_cancelled",
                    "message_code": "rematch.opponent_left",
                })
            except Exception:
                pass

    if not manager.connections.get(room_id):
        await _remove_room_from_redis(room_id)
    else:
        await _cleanup_orphaned_tasks(room_id)


async def _handle_disconnect(
    room_id: str,
    websocket: WebSocket,
    is_ai_room: bool,
):
    disconnected_client_id = manager.get_client_id(room_id, websocket)
    await manager.disconnect(room_id, websocket)

    game = await get_game(room_id)
    room_data = await get_room(room_id)

    if game and game.get("game_over"):
        if is_ai_room:
            if not manager.connections.get(room_id):
                await _remove_room_from_redis(room_id)
            else:
                await _cleanup_orphaned_tasks(room_id)
            return
        await _handle_finished_game_disconnect(room_id, disconnected_client_id, room_data)
        return

    if is_ai_room:
        logger.info("Player disconnected from AI room %s", room_id)
        return

    if not game:
        await _cleanup_orphaned_tasks(
            room_id,
            drop_lock=not manager.connections.get(room_id),
        )
        return

    opponent = (
        manager.get_opponent_ws(room_id, disconnected_client_id)
        if disconnected_client_id
        else None
    )

    if disconnected_client_id and opponent:
        opponent_cid = next(
            (cid for cid, ws in manager.connections.get(room_id, {}).items()
             if cid != disconnected_client_id and ws is opponent),
            None,
        )
        if opponent_cid:
            try:
                await send_control_v1(room_id, opponent_cid, opponent, {
                    "status": "opponent_disconnected",
                    "timeout": DISCONNECT_TIMEOUT,
                })
            except Exception:
                pass
        prior = disconnect_timers.pop(room_id, None)
        if prior and not prior.done():
            prior.cancel()
        disconnect_timers[room_id] = asyncio.create_task(
            dt_func(room_id, opponent, disconnected_client_id)
        )
    else:
        await _remove_room_from_redis(room_id)
