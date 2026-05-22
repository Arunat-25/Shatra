import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect

from game_engine.models import GameEvent
from game_engine.game_logic import logic
from backend.state import (get_game, set_game, delete_game,
                            get_room, set_room, delete_room,
                            game_timers, disconnect_timers, DISCONNECT_TIMEOUT)
from backend.ws_manager import manager
from backend.board_utils import keys_int_to_str, keys_str_to_int, change_position_name_from_frontend
from backend.timers import game_ticker, disconnect_timer as dt_func, stop_game_timer
from backend.ai import get_best_move

logger = logging.getLogger(__name__)


def build_move_response(game: dict, result, prev_mover: str, move_from: int = None, move_to: int = None) -> dict:
    response = {
        "message": result.message,
        "movers_color": result.movers_color,
        "desk": keys_int_to_str(game["board"]),
        "game_over": result.game_over,
        "winner": result.winner,
        "position_for_mandatory_capture": result.position_for_mandatory_capture,
        "opportunity_pass_the_move": result.opportunity_pass_the_move,
        "essential_positions": result.essential_positions,
        "captured_pieces": result.captured_pieces,
        "captured_positions": result.captured_positions,
        "from_pos": move_from,
        "to_pos": move_to,
        "move_history": game.get("move_history", []),
    }
    if result.movers_color and result.movers_color != prev_mover:
        response["position_for_mandatory_capture"] = None
    return response


def _save_move_to_history(game: dict, mover: str, from_cell: int, to_cell: int):
    history = game.setdefault("move_history", [])
    history.append({
        "move_number": len(history) + 1,
        "mover": mover,
        "from_pos": from_cell,
        "to_pos": to_cell,
        "desk": keys_int_to_str(game["board"]),
    })


async def handle_ai_move(room_id: str, game: dict, max_recursion: int = 5):
    """Вычислить и отправить ход AI."""
    if max_recursion <= 0:
        return
    await asyncio.sleep(1.5)

    board = game["board"]
    board_snapshot = dict(board)
    ai_color = game["mover"]
    move = get_best_move(board, ai_color, depth=3,
                          batyr_captured_this_turn=game.get("pending_batyr_captures"))
    if move is None:
        return

    from_cell, to_cell = move
    data = GameEvent(
        positions=board,
        mover_color=ai_color,
        from_pos=from_cell,
        to_pos=to_cell,
    )
    prev_mover = game["mover"]
    result = logic.handle_event(
        data,
        batyr_captured_this_turn=game["pending_batyr_captures"],
        position_history=game.get("position_history", {}),
    )

    if result.updated_positions:
        game["board"] = result.updated_positions

    if result.movers_color and result.movers_color != prev_mover:
        game["moves_made"] = game.get("moves_made", 0) + 1
        room_data = await get_room(room_id)
        if room_data and room_data.get("increment") and room_data.get("time_control"):
            if prev_mover == "белый" and room_data.get("timer_player1") is not None:
                room_data["timer_player1"] += float(room_data["increment"])
            elif prev_mover == "черный" and room_data.get("timer_player2") is not None:
                room_data["timer_player2"] += float(room_data["increment"])
            await set_room(room_id, room_data)

    if result.movers_color and result.movers_color != prev_mover:
        game["pending_batyr_captures"] = []
    elif result.captured_pieces:
        game["pending_batyr_captures"] = result.captured_pieces

    if result.movers_color:
        game["mover"] = result.movers_color

    if result.movers_color and result.movers_color != prev_mover:
        _save_move_to_history(game, prev_mover, from_cell, to_cell)

    await set_game(room_id, game)

    response = build_move_response(game, result, prev_mover, from_cell, to_cell)
    logger.info("AI move for room %s: %s -> %s, game_over=%s", room_id, from_cell, to_cell, result.game_over)
    await manager.send_to_room(room_id, response)

    if not result.updated_positions or result.updated_positions == board_snapshot:
        return

    if result.movers_color == ai_color and not result.game_over:
        await handle_ai_move(room_id, game, max_recursion - 1)


async def websocket_endpoint(websocket: WebSocket, room_id: str):
    player_id = websocket.query_params.get("player")
    player_id_int = int(player_id) if player_id and player_id.isdigit() else None
    client_id = websocket.query_params.get("client_id")
    if not await manager.connect(room_id, websocket, client_id=client_id, player_id=player_id_int):
        return

    room_data = await get_room(room_id)
    if not room_data:
        return

    # Корректировка таймеров после рестарта
    # (восстанавливаем Room из Pydantic для вызова correct_timers_after_restart)
    from backend.models import Room
    room_obj = Room(**room_data)
    room_obj.correct_timers_after_restart()
    room_data = room_obj.model_dump()
    await set_room(room_id, room_data)

    is_ai_room = room_data["type"] == "ai"
    my_player_id = manager._find_player_id(room_id, websocket)
    is_player1 = my_player_id == 1

    # AI-комнаты: немедленный старт
    if is_ai_room and is_player1:
        room_data["player2_connected"] = True
        await set_room(room_id, room_data)
        await init_game_local(room_id)
        game = await get_game(room_id)

        response = {
            "status": "game_started",
            "movers_color": game["mover"],
            "desk": keys_int_to_str(game["board"]),
        }
        if room_data.get("time_control"):
            response["time_control"] = room_data["time_control"]
            response["increment"] = room_data.get("increment")
            response["time"] = {
                "белый": room_data.get("timer_player1") or 0,
                "черный": room_data.get("timer_player2") or 0,
            }
        await manager.send_to_player(websocket, response)

        if room_data.get("time_control"):
            task = asyncio.create_task(game_ticker(room_id))
            game_timers[room_id] = task

        if game["mover"] == "черный":
            await handle_ai_move(room_id, game)

    elif room_data.get("game_started"):
        game = await get_game(room_id)
        if game:
            response = {
                "status": "game_started",
                "movers_color": game["mover"],
                "desk": keys_int_to_str(game["board"]),
            }
            if room_data.get("time_control"):
                response["time_control"] = room_data["time_control"]
                response["increment"] = room_data.get("increment")
                response["time"] = {
                    "белый": room_data.get("timer_player1") or 0,
                    "черный": room_data.get("timer_player2") or 0,
                }
            await manager.send_to_player(websocket, response)

            # Перезапускаем таймер, если игра идёт и есть time_control
            if room_data.get("time_control") and room_id not in game_timers:
                task = asyncio.create_task(game_ticker(room_id))
                game_timers[room_id] = task

    elif is_player1:
        await manager.send_to_player(websocket, {
            "status": "waiting",
            "link": room_id,
        })
        try:
            while not room_data.get("game_started"):
                try:
                    data = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                    # Если игра началась в другом потоке — выходим
                except asyncio.TimeoutError:
                    pass
                # Перечитываем room_data из Redis
                rd = await get_room(room_id)
                if rd:
                    room_data = rd
        except WebSocketDisconnect:
            await manager.disconnect(room_id, websocket)
            return
        except Exception:
            await manager.disconnect(room_id, websocket)
            return
    else:
        from backend.ws_manager import handle_player2_join
        await handle_player2_join(room_id, room_data)

    if not room_data.get("game_started"):
        await manager.disconnect(room_id, websocket)
        return

    try:
        while True:
            data = await websocket.receive_json()

            raw_from = change_position_name_from_frontend(data.get("move_from")) if data.get("move_from") else None
            raw_to = change_position_name_from_frontend(data.get("move_to")) if data.get("move_to") else None

            event = GameEvent(
                positions=keys_str_to_int(data["board"]),
                mover_color=data["movers_color"],
                from_pos=raw_from,
                to_pos=raw_to,
                position=change_position_name_from_frontend(data.get("position")) if data.get("position") else None,
                position_for_mandatory_capture=data.get("position_for_mandatory_capture"),
            )

            game = await get_game(room_id)
            if not game:
                break

            prev_mover = game["mover"]
            result = logic.handle_event(
                event,
                batyr_captured_this_turn=game["pending_batyr_captures"],
                position_history=game.get("position_history", {}),
            )

            if result.updated_positions:
                game["board"] = result.updated_positions

            if result.movers_color and result.movers_color != prev_mover:
                game["moves_made"] = game.get("moves_made", 0) + 1
                room_data = await get_room(room_id)
                if room_data and room_data.get("increment") and room_data.get("time_control"):
                    if prev_mover == "белый" and room_data.get("timer_player1") is not None:
                        room_data["timer_player1"] += float(room_data["increment"])
                    elif prev_mover == "черный" and room_data.get("timer_player2") is not None:
                        room_data["timer_player2"] += float(room_data["increment"])
                    await set_room(room_id, room_data)

            if result.movers_color and result.movers_color != prev_mover:
                game["pending_batyr_captures"] = []
            elif result.captured_pieces:
                game["pending_batyr_captures"] = result.captured_pieces

            if result.movers_color:
                game["mover"] = result.movers_color

            if result.movers_color and result.movers_color != prev_mover and raw_from is not None and raw_to is not None:
                _save_move_to_history(game, prev_mover, raw_from, raw_to)

            await set_game(room_id, game)

            response = build_move_response(game, result, prev_mover, raw_from, raw_to)
            await manager.send_to_room(room_id, response)

            if is_ai_room and not result.game_over and game["mover"] == "черный":
                await handle_ai_move(room_id, game)

    except WebSocketDisconnect:
        await manager.disconnect(room_id, websocket)

        if is_ai_room:
            await delete_game(room_id)
            await delete_room(room_id)
        else:
            game = await get_game(room_id)
            if game and not game.get("game_over", False):
                disconnected_id = manager._find_player_id(room_id, websocket)
                if disconnected_id == 1:
                    remaining_ws = manager.get_player_ws(room_id, 2)
                elif disconnected_id == 2:
                    remaining_ws = manager.get_player_ws(room_id, 1)
                else:
                    remaining_ws = None

                if disconnected_id and remaining_ws:
                    try:
                        await remaining_ws.send_json({
                            "status": "opponent_disconnected",
                            "timeout": DISCONNECT_TIMEOUT,
                        })
                    except Exception:
                        pass

                    task = asyncio.create_task(
                        dt_func(room_id, remaining_ws, disconnected_id)
                    )
                    disconnect_timers[room_id] = task
                else:
                    await delete_game(room_id)
                    await delete_room(room_id)


async def init_game_local(room_id: str):
    """Создаёт начальное состояние игры в Redis (для AI-режима)."""
    from backend.board_utils import get_starting_board
    from backend.state import set_game
    start_board = get_starting_board()
    game_data = {
        "board": start_board,
        "mover": "белый",
        "players": {},
        "pending_batyr_captures": [],
        "moves_made": 0,
        "move_history": [],
        "position_history": {},
    }
    await set_game(room_id, game_data)