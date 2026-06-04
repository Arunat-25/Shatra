import asyncio
import logging

from fastapi import WebSocket

from game_engine.models import GameEvent, GameEventResult
from game_engine.game_logic import logic
from backend.state import get_game, set_game, set_room, game_timers
from backend.ws_manager import manager, init_game
from backend.timers import game_ticker, stop_game_timer
from backend.ai import get_best_move
from backend.game_helpers import (
    build_game_started_response,
    build_move_response,
    apply_move_result,
    get_ai_color,
)
from backend.game_archive import mark_game_started, on_game_finished

logger = logging.getLogger(__name__)


async def handle_ai_move(room_id: str, game: dict, max_recursion: int = 5):
    """Вычислить и отправить ход AI."""
    if max_recursion <= 0:
        return
    await asyncio.sleep(0.3)

    board = game["board"]
    board_snapshot = dict(board)
    ai_color = game["mover"]

    loop = asyncio.get_running_loop()
    move = await loop.run_in_executor(
        None,
        get_best_move,
        board,
        ai_color,
        3,
        game.get("pending_batyr_captures"),
        game.get("pending_mandatory_position"),
    )
    if move is None:
        logger.warning("AI has no legal moves in room %s — game over", room_id)
        response = build_move_response(
            game,
            GameEventResult(
                message_code="ai.no_move",
                updated_positions=board,
                game_over=True,
                winner_color="белый" if ai_color == "черный" else "черный",
            ),
            ai_color,
        )
        game["board"] = board
        game["game_over"] = True
        game["winner_color"] = "белый" if ai_color == "черный" else "черный"
        game["winner"] = game["winner_color"]
        game["reason"] = "ai.no_move"
        await set_game(room_id, game)
        await manager.send_to_room(room_id, response)
        stop_game_timer(room_id)
        await on_game_finished(room_id)
        return

    from_cell, to_cell = move
    prev_mover = game["mover"]
    result = logic.handle_event(
        GameEvent(
            positions=board,
            mover_color=ai_color,
            from_pos=from_cell,
            to_pos=to_cell,
            position_for_mandatory_capture=game.get("pending_mandatory_position"),
        ),
        batyr_captured_this_turn=game.get("pending_batyr_captures"),
        position_history=game.get("position_history", {}),
    )

    if result.updated_positions and result.updated_positions == board and game["mover"] == ai_color:
        logger.warning(
            "AI move %s->%s rejected in room %s: %s. Retrying...",
            from_cell, to_cell, room_id, result.message_code,
        )
        game.pop("pending_mandatory_position", None)
        game["board"] = board
        await handle_ai_move(room_id, game, max_recursion - 1)
        return

    response = await apply_move_result(room_id, game, result, prev_mover, from_cell, to_cell)
    logger.info(
        "AI move for room %s: %s -> %s, game_over=%s, chain_next=%s",
        room_id,
        from_cell,
        to_cell,
        result.game_over,
        result.position_for_mandatory_capture,
    )
    await manager.send_to_room(room_id, response)

    if not result.updated_positions or result.updated_positions == board_snapshot:
        return

    if result.position_for_mandatory_capture:
        game["pending_mandatory_position"] = result.position_for_mandatory_capture
    else:
        game.pop("pending_mandatory_position", None)

    if result.movers_color == ai_color and not result.game_over:
        await handle_ai_move(room_id, game, max_recursion - 1)


async def _start_ai_game(room_id: str, websocket: WebSocket, room_data: dict, my_color: str):
    """Первый вход в AI-комнату или переподключение."""
    game = await get_game(room_id)

    if game is None:
        await init_game(room_id)
        game = await get_game(room_id)
        room_data["game_started"] = True
        mark_game_started(room_data)
        await set_room(room_id, room_data)
        response = build_game_started_response(game, room_data, my_color)
        await manager.send_to_player(websocket, response)

        if room_data.get("time_control"):
            game_timers[room_id] = asyncio.create_task(game_ticker(room_id))

        if game["mover"] == get_ai_color(room_data):
            await handle_ai_move(room_id, game)
    else:
        response = build_game_started_response(game, room_data, my_color)
        await manager.send_to_player(websocket, response)
        if (
            room_data.get("time_control")
            and room_id not in game_timers
            and not game.get("game_over")
        ):
            game_timers[room_id] = asyncio.create_task(game_ticker(room_id))
