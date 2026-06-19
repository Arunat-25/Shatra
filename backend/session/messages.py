from fastapi import WebSocket

from game_engine.game_logic import logic
from backend.state import get_game, get_room, get_room_lock
from backend.ws_manager import manager
from backend.game_helpers import (
    apply_move_result,
    parse_client_event,
    get_ai_color,
    ws_error_payload,
    is_move_message,
    is_rejected_move,
    _norm_board_keys,
)
from backend.chat import handle_chat_message
from backend.ws_control_handlers import CONTROL_MESSAGE_TYPES, dispatch_control_message
from backend.session.rematch import _decline_draw_offer
from backend.observability.metrics import record_move, record_move_rejected
from backend.session.ai import handle_ai_move


async def _send_ws_error(websocket: WebSocket, code: str, **params) -> None:
    await manager.send_to_player(websocket, ws_error_payload(code, **params))


async def process_client_message(
    room_id: str,
    client_id: str,
    data: dict,
    websocket: WebSocket,
    *,
    is_ai_room: bool,
) -> bool:
    """Обрабатывает одно входящее WS-сообщение под локом комнаты.

    Лок сериализует read-modify-write над game/room с тиком часов и другими
    сообщениями, исключая потерю обновлений (например, начисление инкремента).
    """
    async with get_room_lock(room_id):
        return await _process_client_message_locked(
            room_id, client_id, data, websocket, is_ai_room=is_ai_room
        )


async def _process_client_message_locked(
    room_id: str,
    client_id: str,
    data: dict,
    websocket: WebSocket,
    *,
    is_ai_room: bool,
) -> bool:
    """Тело обработки сообщения. Вызывать только из process_client_message (под локом)."""
    msg_type = data.get("type")
    if msg_type == "chat":
        return await handle_chat_message(
            room_id, client_id, websocket, data, is_ai_room=is_ai_room
        )

    if msg_type in CONTROL_MESSAGE_TYPES:
        return await dispatch_control_message(
            msg_type, room_id, client_id, websocket, is_ai_room=is_ai_room
        )

    if msg_type:
        await _send_ws_error(websocket, "ws.unknown_command")
        return True

    if not is_move_message(data):
        await _send_ws_error(websocket, "ws.unknown_message")
        return True

    try:
        event, raw_from, raw_to = parse_client_event(data)
    except ValueError as exc:
        await _send_ws_error(websocket, str(exc))
        return True
    except (KeyError, TypeError):
        await _send_ws_error(websocket, "ws.invalid_move_data")
        return True

    game = await get_game(room_id)
    if not game:
        return False

    if game.get("game_over"):
        await _send_ws_error(websocket, "ws.game_over")
        return True

    room_data = await get_room(room_id)
    if game.get("draw_offer_from") and room_data:
        await _decline_draw_offer(room_id, game, room_data)
        game = await get_game(room_id)
        if not game:
            return False

    client_ply = data.get("ply")
    if client_ply is not None:
        expected_ply = int(game.get("ply", 0)) + 1
        if int(client_ply) != expected_ply:
            await _send_ws_error(websocket, "ws.ply_mismatch", ply=expected_ply)
            return True

    prev_mover = game["mover"]
    prev_board = _norm_board_keys(game.get("board", {}))
    position_history = game.setdefault("position_history", {})
    result = logic.handle_event(
        event,
        batyr_captured_this_turn=game.get("pending_batyr_captures"),
        position_history=position_history,
        moves_with_two_biys=game.get("moves_with_two_biys", 0),
    )

    if is_rejected_move(result, prev_board, raw_from, raw_to):
        reason = result.message_code or "move.impossible"
        record_move_rejected(reason)
        await _send_ws_error(websocket, reason)
        return True

    from game_engine.endgame import _only_two_biys_left
    from game_engine.board import Board

    current_count = game.get("moves_with_two_biys", 0)
    if _only_two_biys_left(Board(result.updated_positions or game["board"])):
        game["moves_with_two_biys"] = current_count + 1
    else:
        game["moves_with_two_biys"] = 0

    if result.position_for_mandatory_capture:
        game["pending_mandatory_position"] = result.position_for_mandatory_capture
    else:
        game.pop("pending_mandatory_position", None)

    response = await apply_move_result(
        room_id, game, result, prev_mover, raw_from, raw_to
    )
    record_move("player")
    await manager.broadcast_move(room_id, game, result, prev_mover, raw_from, raw_to)

    room_data = await get_room(room_id)
    if is_ai_room and not result.game_over and room_data and game["mover"] == get_ai_color(room_data):
        await handle_ai_move(room_id, game)

    return True
