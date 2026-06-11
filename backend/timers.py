import asyncio
import logging
from fastapi import WebSocket
from backend.state import (get_room, set_room, get_game,
                            game_timers, disconnect_timers, DISCONNECT_TIMEOUT,
                            get_room_lock)
from backend.config import settings
from backend.board_utils import keys_int_to_str
from backend.game_helpers import color_has_moved, compute_clock_times
from backend.game_finish import _finish_game_locked, finish_game
from backend.ws_manager import manager

logger = logging.getLogger(__name__)
TICK_INTERVAL_SECONDS = settings.tick_interval_seconds


def _opposite_color(color: str) -> str:
    """Чёрный ↔ белый."""
    return "черный" if color == "белый" else "белый"


async def game_ticker(room_id: str):
    """Sync clocks and detect timeout using computed display times (no stored -= 1)."""
    try:
        while True:
            async with get_room_lock(room_id):
                room_data = await get_room(room_id)
                if not room_data:
                    logger.info("game_ticker: room %s not found, stopping", room_id)
                    stop_game_timer(room_id)
                    return

                if not room_data.get("time_control"):
                    stop_game_timer(room_id)
                    return

                game = await get_game(room_id)
                if game and game.get("game_over"):
                    stop_game_timer(room_id)
                    return

                if not game:
                    return

                mover = game.get("mover")
                times = compute_clock_times(room_data, game)
                if not times:
                    return

                timed_out = None
                if (
                    mover == "белый"
                    and color_has_moved(game, "белый")
                    and times["белый"] <= 0
                ):
                    timed_out = "белый"
                    room_data["timer_white"] = 0
                elif (
                    mover == "черный"
                    and color_has_moved(game, "черный")
                    and times["черный"] <= 0
                ):
                    timed_out = "черный"
                    room_data["timer_black"] = 0

                if timed_out:
                    await set_room(room_id, room_data)
                    await manager.send_to_room(room_id, {
                        "type": "timer_tick",
                        "time": {
                            "белый": room_data.get("timer_white") or 0,
                            "черный": room_data.get("timer_black") or 0,
                        },
                    })
                    await handle_timeout(room_id, timed_out)
                    return

                await manager.send_to_room(room_id, {
                    "type": "timer_tick",
                    "time": times,
                })

            await asyncio.sleep(TICK_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("game_ticker error for %s: %s", room_id, e)
        stop_game_timer(room_id)


async def handle_timeout(room_id: str, timed_out_color: str):
    """Обрабатывает окончание времени у одного из игроков. Вызывать под room lock."""
    winner = _opposite_color(timed_out_color)
    game = await get_game(room_id)
    room_data = await get_room(room_id)
    time_payload = None
    if room_data:
        time_payload = compute_clock_times(room_data, game) or {
            "белый": room_data.get("timer_white") or 0,
            "черный": room_data.get("timer_black") or 0,
        }

    payload = {
        "status": "timeout",
        "game_over": True,
        "winner_color": winner,
        "reason": "timeout",
        "desk": keys_int_to_str(game["board"]) if game else {},
    }
    if time_payload:
        payload["time"] = time_payload

    finished = await _finish_game_locked(
        room_id,
        reason="timeout",
        winner_color=winner,
        broadcast=payload,
        record_timeout_kind="clock",
    )
    if finished:
        logger.info("Timeout in %s: %s ran out of time", room_id, timed_out_color)


def stop_game_timer(room_id: str):
    """Останавливает тикер для комнаты."""
    task = game_timers.pop(room_id, None)
    if task and not task.done():
        task.cancel()
        logger.debug("game_timer cancelled for %s", room_id)


async def disconnect_timer(room_id: str, remaining_ws: WebSocket, disconnected_client_id: str):
    """Таймер ожидания переподключения отключившегося игрока."""
    try:
        for i in range(DISCONNECT_TIMEOUT, 0, -1):
            if remaining_ws:
                try:
                    await remaining_ws.send_json({
                        "type": "disconnect_tick",
                        "remaining": i,
                    })
                except Exception:
                    pass
            await asyncio.sleep(TICK_INTERVAL_SECONDS)

        game = await get_game(room_id)
        if not game or game.get("game_over", False):
            disconnect_timers.pop(room_id, None)
            return

        room_data = await get_room(room_id)
        disconnected_color = None
        if room_data:
            players = room_data.get("players", {})
            disconnected_color = players.get(disconnected_client_id)
        winner = _opposite_color(disconnected_color or "белый")

        await finish_game(
            room_id,
            reason="opponent_disconnected",
            winner_color=winner,
            broadcast={
                "game_over": True,
                "winner_color": winner,
                "reason": "opponent_disconnected",
            },
            record_timeout_kind="disconnect",
        )

        disconnect_timers.pop(room_id, None)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("disconnect_timer error for %s: %s", room_id, e)
    finally:
        disconnect_timers.pop(room_id, None)
