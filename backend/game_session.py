import asyncio
import logging
import time
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
    get_ai_color,
)
from backend.board_utils import keys_int_to_str

logger = logging.getLogger(__name__)

def _opposite_color(color: str) -> str:
    return "черный" if color == "белый" else "белый"


async def _broadcast_rematch_status(room_id: str, room_data: dict) -> None:
    ready = set(room_data.get("rematch_ready") or [])
    conns = manager.connections.get(room_id, {})
    for cid, ws in list(conns.items()):
        opp_cid = next((c for c in conns if c != cid), None)
        try:
            await ws.send_json({
                "status": "rematch_status",
                "self_ready": cid in ready,
                "opponent_ready": bool(opp_cid and opp_cid in ready),
            })
        except Exception:
            pass


async def _start_rematch(room_id: str, room_data: dict) -> None:
    """Сбрасывает игру и запускает реванш для обоих подключённых игроков."""
    from backend.timers import stop_game_timer, game_ticker as gt

    stop_game_timer(room_id)

    players = room_data.get("players") or {}
    for cid in list(players.keys()):
        players[cid] = _opposite_color(players[cid])
    room_data["players"] = players

    await init_game(room_id)
    game = await get_game(room_id)
    if not game:
        return

    room_data["rematch_ready"] = []
    if room_data.get("time_control"):
        tc = float(room_data["time_control"])
        room_data["timer_white"] = tc
        room_data["timer_black"] = tc
        room_data["last_tick"] = time.time()
    await set_room(room_id, room_data)

    for cid, ws in list(manager.connections.get(room_id, {}).items()):
        color = room_data.get("players", {}).get(cid)
        if ws and color:
            response = build_game_started_response(game, room_data, color)
            await manager.send_to_player(ws, response)

    if room_data.get("time_control"):
        game_timers[room_id] = asyncio.create_task(gt(room_id))


async def _decline_draw_offer(room_id: str, game: dict, room_data: dict) -> bool:
    """Сбрасывает предложение ничьей и уведомляет игроков. Возвращает True, если было активное предложение."""
    offerer = game.get("draw_offer_from")
    if not offerer:
        return False
    game.pop("draw_offer_from", None)
    await set_game(room_id, game)
    for cid, ws in manager.connections.get(room_id, {}).items():
        color = room_data.get("players", {}).get(cid)
        if color == offerer:
            text = "Соперник отклонил предложение ничьей."
        else:
            text = "Предложение ничьей отменено."
        try:
            await ws.send_json({"status": "draw_declined", "message": text})
        except Exception:
            pass
    return True


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
            position_for_mandatory_capture=game.get("pending_mandatory_position"),
        ),
        batyr_captured_this_turn=game.get("pending_batyr_captures"),
        position_history=game.get("position_history", {}),
    )

    # Если ход был отклонён (например, "нужно бить" или "продолжайте взятие"),
    # пробуем следующий ход из списка
    if result.updated_positions and result.updated_positions == board and game["mover"] == ai_color:
        logger.warning(
            "AI move %s->%s rejected in room %s: %s. Retrying...",
            from_cell, to_cell, room_id, result.message,
        )
        # Сброс pending_mandatory, чтобы AI мог выбрать другой ход
        game.pop("pending_mandatory_position", None)
        game["board"] = board  # Восстанавливаем состояние
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

    # Сохраняем обязательное продолжение взятия для следующего AI-хода
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
        if room_data.get("time_control") and room_id not in game_timers:
            game_timers[room_id] = asyncio.create_task(game_ticker(room_id))


async def _wait_for_second_player(websocket: WebSocket, room_id: str, room_data: dict) -> dict | None:
    """Ожидание второго игрока (пока в комнате один участник)."""
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
    room_data = await get_room(room_id)

    if game and game.get("game_over", False) and room_data and room_data.get("type") != "ai":
        room_data["rematch_ready"] = []
        await set_room(room_id, room_data)
        opponent = (
            manager.get_opponent_ws(room_id, disconnected_client_id)
            if disconnected_client_id
            else None
        )
        if opponent:
            try:
                await opponent.send_json({
                    "status": "rematch_cancelled",
                    "message": "Соперник вышел. Реванш отменён.",
                })
            except Exception:
                pass
        return

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
    players_in_room = len(room_data.get("players") or {})

    if is_ai_room:
        await _start_ai_game(room_id, websocket, room_data, my_color)
    elif room_data.get("game_started"):
        game = await get_game(room_id)
        if game:
            response = build_game_started_response(game, room_data, my_color)
            await manager.send_to_player(websocket, response)
            if game.get("game_over") and not is_ai_room:
                await _broadcast_rematch_status(room_id, room_data)
            elif room_data.get("time_control") and room_id not in game_timers:
                game_timers[room_id] = asyncio.create_task(game_ticker(room_id))
    elif players_in_room < 2:
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
            except RuntimeError as e:
                # Starlette может бросать RuntimeError при уже закрытом сокете:
                # "WebSocket is not connected. Need to call \"accept\" first."
                # В этом случае дальнейшее чтение бессмысленно — выходим.
                logger.info("WebSocket runtime error in room %s (closing loop): %s", room_id, e)
                break
            except Exception as e:
                msg = str(e)
                # Если сокет уже закрыт — не зацикливаемся и не спамим логами.
                if "WebSocket is not connected" in msg:
                    logger.info("WebSocket not connected in room %s (closing loop)", room_id)
                    break
                logger.error(
                    "Invalid JSON from client %s in room %s: %s",
                    client_id[:6],
                    room_id,
                    e,
                )
                continue

            # === Rematch / Реванш (только PvP) ===
            if isinstance(data, dict) and data.get("type") == "request_rematch":
                if is_ai_room:
                    continue
                game = await get_game(room_id)
                room_data = await get_room(room_id)
                if not game or not room_data or not game.get("game_over", False):
                    continue
                if client_id not in manager.connections.get(room_id, {}):
                    continue
                ready = list(room_data.get("rematch_ready") or [])
                if client_id not in ready:
                    ready.append(client_id)
                room_data["rematch_ready"] = ready
                await set_room(room_id, room_data)

                conns = manager.connections.get(room_id, {})
                if len(conns) < 2:
                    await manager.send_to_player(websocket, {
                        "status": "rematch_status",
                        "self_ready": True,
                        "opponent_ready": False,
                    })
                    continue

                await _broadcast_rematch_status(room_id, room_data)
                if len(ready) >= 2 and all(cid in ready for cid in conns):
                    await _start_rematch(room_id, room_data)
                continue

            # === Decline draw / Отклонить ничью ===
            if isinstance(data, dict) and data.get("type") == "decline_draw":
                game = await get_game(room_id)
                if not game or game.get("game_over", False):
                    continue
                room_data = await get_room(room_id)
                if not room_data:
                    continue
                my_color = room_data.get("players", {}).get(client_id)
                offerer = game.get("draw_offer_from")
                if offerer and my_color and offerer != my_color:
                    await _decline_draw_offer(room_id, game, room_data)
                continue

            # === Offer draw / Предложить ничью ===
            if isinstance(data, dict) and data.get("type") == "offer_draw":
                game = await get_game(room_id)
                if not game or game.get("game_over", False):
                    continue
                room_data = await get_room(room_id)
                my_color = None
                if room_data:
                    my_color = room_data.get("players", {}).get(client_id)
                if not my_color:
                    my_color = "белый"

                if is_ai_room:
                    if game.get("draw_offer_from"):
                        game.pop("draw_offer_from", None)
                        await set_game(room_id, game)
                    await manager.send_to_player(websocket, {
                        "status": "draw_declined",
                        "message": "Бот не принимает ничью.",
                    })
                    continue

                other_color = _opposite_color(my_color)
                pending = game.get("draw_offer_from")

                if pending == other_color:
                    draw_msg = "Ничья! Обоюдное согласие."
                    game["game_over"] = True
                    game["winner"] = draw_msg
                    game["reason"] = "draw_agreed"
                    game.pop("draw_offer_from", None)
                    await set_game(room_id, game)
                    room_data["rematch_ready"] = []
                    await set_room(room_id, room_data)
                    try:
                        from backend.timers import stop_game_timer
                        stop_game_timer(room_id)
                    except Exception:
                        pass
                    await manager.send_to_room(room_id, {
                        "game_over": True,
                        "winner": draw_msg,
                        "reason": "draw_agreed",
                        "desk": keys_int_to_str(game.get("board", {})),
                    })
                    continue

                if pending == my_color:
                    await manager.send_to_player(websocket, {
                        "status": "draw_offered",
                        "message": "Вы уже предложили ничью. Ожидание ответа соперника.",
                    })
                    continue

                game["draw_offer_from"] = my_color
                await set_game(room_id, game)

                for cid, ws in manager.connections.get(room_id, {}).items():
                    color = room_data.get("players", {}).get(cid)
                    if color == my_color:
                        text = "Вы предложили ничью. Ожидание ответа соперника."
                    else:
                        text = "Соперник предлагает ничью. Нажмите ½, чтобы принять."
                    try:
                        await ws.send_json({"status": "draw_offered", "message": text, "by": my_color})
                    except Exception:
                        pass
                continue

            # === Resign / Сдаться ===
            if isinstance(data, dict) and data.get("type") == "resign":
                game = await get_game(room_id)
                if not game or game.get("game_over", False):
                    continue
                room_data = await get_room(room_id)
                my_color = None
                if room_data:
                    my_color = room_data.get("players", {}).get(client_id)
                if not my_color:
                    # Fallback: if unknown, assume resigning player is white
                    my_color = "белый"
                winner = _opposite_color(my_color)
                game["game_over"] = True
                game["winner"] = winner
                game["reason"] = "resign"
                game.pop("draw_offer_from", None)
                await set_game(room_id, game)
                if not is_ai_room:
                    room_data = await get_room(room_id)
                    if room_data:
                        room_data["rematch_ready"] = []
                        await set_room(room_id, room_data)
                try:
                    from backend.timers import stop_game_timer
                    stop_game_timer(room_id)
                except Exception:
                    pass
                await manager.send_to_room(room_id, {
                    "game_over": True,
                    "winner": winner,
                    "reason": "resign",
                    "desk": keys_int_to_str(game.get("board", {})),
                })
                continue

            event, raw_from, raw_to = parse_client_event(data)

            game = await get_game(room_id)
            if not game:
                break

            room_data = await get_room(room_id) or room_data
            if game.get("draw_offer_from"):
                await _decline_draw_offer(room_id, game, room_data)
                game = await get_game(room_id)
                if not game:
                    break

            prev_mover = game["mover"]
            result = logic.handle_event(
                event,
                batyr_captured_this_turn=game.get("pending_batyr_captures"),
                position_history=game.get("position_history", {}),
                moves_with_two_biys=game.get("moves_with_two_biys", 0),
            )

            # Обновляем счётчик ходов с двумя биями (только когда других фигур нет)
            from game_engine.endgame import _only_two_biys_left
            from game_engine.board import Board
            current_count = game.get("moves_with_two_biys", 0)
            if _only_two_biys_left(Board(result.updated_positions or game["board"])):
                game["moves_with_two_biys"] = current_count + 1
            else:
                game["moves_with_two_biys"] = 0

            # Сбрасываем состояние обязательных взятий после хода человека
            if result.position_for_mandatory_capture:
                game["pending_mandatory_position"] = result.position_for_mandatory_capture
            else:
                game.pop("pending_mandatory_position", None)

            response = await apply_move_result(
                room_id, game, result, prev_mover, raw_from, raw_to
            )
            await manager.send_to_room(room_id, response)

            if is_ai_room and not result.game_over and game["mover"] == get_ai_color(room_data):
                await handle_ai_move(room_id, game)

    except WebSocketDisconnect:
        await _handle_disconnect(room_id, websocket, is_ai_room)
