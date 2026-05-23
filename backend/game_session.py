import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect

from game_engine.models import GameEvent, GameEventResult
from game_engine.game_logic import logic
from backend.state import (
    get_game,
    set_game,
    delete_game,
    get_room,
    set_room,
    delete_room,
    game_timers,
    disconnect_timers,
    DISCONNECT_TIMEOUT,
)
from backend.ws_manager import manager, init_game, handle_player2_join
from backend.timers import game_ticker, disconnect_timer as dt_func
from backend.ai import get_best_move
from backend.models import Room
from backend.game_helpers import (
    build_game_started_response,
    build_move_response,
    apply_move_result,
    parse_client_event,
    get_player_color,
)

logger = logging.getLogger(__name__)


async def handle_ai_move(room_id: str, game: dict, max_recursion: int = 5):
    """Вычислить и отправить ход AI."""
    if max_recursion <= 0:
        return
    await asyncio.sleep(1.5)

    board = game["board"]
    board_snapshot = dict(board)
    ai_color = game["mover"]
    move = get_best_move(
        board,
        ai_color,
        depth=3,
        batyr_captured_this_turn=game.get("pending_batyr_captures"),
    )
    if move is None:
        logger.warning("AI has no legal moves in room %s — game over", room_id)
        response = build_move_response(
            game,
            GameEventResult(
                message="Игра окончена: AI не может сделать ход",
                updated_positions=board,
                game_over=True,
                winner="белый" if ai_color == "черный" else "черный",
            ),
            ai_color,
        )
        game["board"] = board
        game["game_over"] = True
        await set_game(room_id, game)
        await manager.send_to_room(room_id, response)
        return

    from_cell, to_cell = move
    prev_mover = game["mover"]
    result = logic.handle_event(
        GameEvent(
            positions=board,
            mover_color=ai_color,
            from_pos=from_cell,
            to_pos=to_cell,
        ),
        batyr_captured_this_turn=game.get("pending_batyr_captures"),
        position_history=game.get("position_history", {}),
    )

    response = await apply_move_result(room_id, game, result, prev_mover, from_cell, to_cell)
    logger.info(
        "AI move for room %s: %s -> %s, game_over=%s",
        room_id,
        from_cell,
        to_cell,
        result.game_over,
    )
    await manager.send_to_room(room_id, response)

    if not result.updated_positions or result.updated_positions == board_snapshot:
        return

    if result.movers_color == ai_color and not result.game_over:
        await handle_ai_move(room_id, game, max_recursion - 1)


async def _start_ai_game(room_id: str, websocket: WebSocket, room_data: dict, my_color: str):
    """Первый вход в AI-комнату или переподключение."""
    game = await get_game(room_id)

    if game is None:
        await init_game(room_id)
        game = await get_game(room_id)
        room_data["game_started"] = True
        await set_room(room_id, room_data)
        response = build_game_started_response(game, room_data, my_color)
        await manager.send_to_player(websocket, response)

        if room_data.get("time_control"):
            game_timers[room_id] = asyncio.create_task(game_ticker(room_id))

        if game["mover"] == "черный":
            await handle_ai_move(room_id, game)
    else:
        response = build_game_started_response(game, room_data, my_color)
        await manager.send_to_player(websocket, response)
        if room_data.get("time_control") and room_id not in game_timers:
            game_timers[room_id] = asyncio.create_task(game_ticker(room_id))


async def _wait_for_second_player(websocket: WebSocket, room_id: str, room_data: dict) -> dict | None:
    """Первый игрок (белые) ждёт присоединения соперника."""
    await manager.send_to_player(websocket, {"status": "waiting", "link": room_id})
    try:
        while not room_data.get("game_started"):
            try:
                await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
            rd = await get_room(room_id)
            if rd:
                room_data = rd
        return room_data
    except WebSocketDisconnect:
        await manager.disconnect(room_id, websocket)
        return None
    except Exception:
        await manager.disconnect(room_id, websocket)
        return None


async def _handle_disconnect(
    room_id: str,
    websocket: WebSocket,
    is_ai_room: bool,
):
    disconnected_client_id = manager.get_client_id(room_id, websocket)
    await manager.disconnect(room_id, websocket)

    if is_ai_room:
        logger.info("Player disconnected from AI room %s", room_id)
        return

    game = await get_game(room_id)
    if not game or game.get("game_over", False):
        return

    opponent = (
        manager.get_opponent_ws(room_id, disconnected_client_id)
        if disconnected_client_id
        else None
    )

    if disconnected_client_id and opponent:
        try:
            await opponent.send_json({
                "status": "opponent_disconnected",
                "timeout": DISCONNECT_TIMEOUT,
            })
        except Exception:
            pass
        disconnect_timers[room_id] = asyncio.create_task(
            dt_func(room_id, opponent, disconnected_client_id)
        )
    else:
        await delete_game(room_id)
        await delete_room(room_id)


async def websocket_endpoint(websocket: WebSocket, room_id: str):
    client_id = websocket.query_params.get("client_id")
    if not client_id:
        await websocket.close(code=1008)
        return

    if not await manager.connect(room_id, websocket, client_id):
        return

    room_data = await get_room(room_id)
    if not room_data:
        return

    room_obj = Room(**room_data)
    room_obj.correct_timers_after_restart()
    room_data = room_obj.model_dump()
    await set_room(room_id, room_data)

    is_ai_room = room_data["type"] == "ai"
    my_color = get_player_color(room_data, client_id)
    is_player_white = my_color == "белый"

    if is_ai_room and is_player_white:
        await _start_ai_game(room_id, websocket, room_data, my_color)
    elif room_data.get("game_started"):
        game = await get_game(room_id)
        if game:
            response = build_game_started_response(game, room_data, my_color)
            await manager.send_to_player(websocket, response)
            if room_data.get("time_control") and room_id not in game_timers:
                game_timers[room_id] = asyncio.create_task(game_ticker(room_id))
    elif is_player_white:
        room_data = await _wait_for_second_player(websocket, room_id, room_data)
        if room_data is None:
            return
    else:
        await handle_player2_join(room_id, room_data)

    if not room_data.get("game_started"):
        await manager.disconnect(room_id, websocket)
        return

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.error(
                    "Invalid JSON from client %s in room %s: %s",
                    client_id[:6],
                    room_id,
                    e,
                )
                continue

            event, raw_from, raw_to = parse_client_event(data)

            game = await get_game(room_id)
            if not game:
                break

            prev_mover = game["mover"]
            result = logic.handle_event(
                event,
                batyr_captured_this_turn=game.get("pending_batyr_captures"),
                position_history=game.get("position_history", {}),
            )

            response = await apply_move_result(
                room_id, game, result, prev_mover, raw_from, raw_to
            )
            await manager.send_to_room(room_id, response)

            if is_ai_room and not result.game_over and game["mover"] == "черный":
                await handle_ai_move(room_id, game)

    except WebSocketDisconnect:
        await _handle_disconnect(room_id, websocket, is_ai_room)
