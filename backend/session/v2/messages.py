"""Process WebSocket v2 client messages."""

from __future__ import annotations

from fastapi import WebSocket

from game_engine.game_logic import logic
from game_engine.endgame import _only_two_biys_left
from game_engine.board import Board
from backend.state import get_game, get_room, get_room_lock
from backend.ws_manager import manager
from backend.game_helpers import (
    apply_move_result,
    get_player_color,
    get_ai_color,
    is_rejected_move,
    persist_pending_mandatory_position,
    _norm_board_keys,
)
from backend.message_codes import WS_NOT_YOUR_TURN
from backend.chat import handle_chat_message
from backend.ws_control_handlers import CONTROL_MESSAGE_TYPES, dispatch_control_message
from backend.session.rematch import _decline_draw_offer
from backend.session.ai import handle_ai_move
from backend.observability.metrics import record_move, record_move_rejected
from backend.session.v2.protocol import (
    is_v2_message,
    next_ply,
    build_move_event_from_game,
    build_snapshot,
    build_reject,
    build_error,
)


async def _send_v2(websocket: WebSocket, payload: dict) -> None:
    await manager.send_to_player(websocket, payload)


async def _send_reject(
    websocket: WebSocket,
    code: str,
    *,
    game: dict | None = None,
    room_data: dict | None = None,
    my_color: str | None = None,
    ply: int | None = None,
    message_params: dict | None = None,
) -> None:
    snapshot = None
    if game is not None and room_data is not None:
        snapshot = build_snapshot(game, room_data, my_color)
    await _send_v2(
        websocket,
        build_reject(code, ply=ply, snapshot=snapshot, message_params=message_params),
    )


async def _apply_and_broadcast_move(
    room_id: str,
    game: dict,
    result,
    prev_mover: str,
    raw_from: int | None,
    raw_to: int | None,
    *,
    is_ai_room: bool,
    board_before: dict | None = None,
) -> None:
    response = await apply_move_result(
        room_id, game, result, prev_mover, raw_from, raw_to
    )
    record_move("player")
    await manager.broadcast_move(
        room_id, game, result, prev_mover, raw_from, raw_to, board_before=board_before,
    )

    room_data = await get_room(room_id)
    if is_ai_room and not result.game_over and room_data and game["mover"] == get_ai_color(room_data):
        await handle_ai_move(room_id, game)


async def process_v2_client_message(
    room_id: str,
    client_id: str,
    data: dict,
    websocket: WebSocket,
    *,
    is_ai_room: bool,
) -> bool:
    async with get_room_lock(room_id):
        return await _process_v2_client_message_locked(
            room_id, client_id, data, websocket, is_ai_room=is_ai_room
        )


async def _process_v2_client_message_locked(
    room_id: str,
    client_id: str,
    data: dict,
    websocket: WebSocket,
    *,
    is_ai_room: bool,
) -> bool:
    if not is_v2_message(data):
        await _send_v2(websocket, build_error("ws.expected_v2"))
        return True

    msg_type = data.get("t")

    if msg_type == "chat":
        legacy = {"type": "chat", "text": data.get("text", "")}
        return await handle_chat_message(
            room_id, client_id, websocket, legacy, is_ai_room=is_ai_room
        )

    if msg_type == "sync":
        game = await get_game(room_id)
        room_data = await get_room(room_id)
        if not game or not room_data:
            return False
        my_color = get_player_color(room_data, client_id)
        snapshot = build_snapshot(game, room_data, my_color)
        snapshot["resync"] = True
        await _send_v2(websocket, snapshot)
        return True

    if msg_type in CONTROL_MESSAGE_TYPES:
        legacy = {"type": msg_type, **{k: v for k, v in data.items() if k not in ("v", "t")}}
        return await dispatch_control_message(
            msg_type, room_id, client_id, websocket, is_ai_room=is_ai_room
        )

    game = await get_game(room_id)
    if not game:
        return False

    room_data = await get_room(room_id)
    my_color = get_player_color(room_data, client_id) if room_data else None

    if game.get("game_over"):
        await _send_reject(websocket, "ws.game_over", game=game, room_data=room_data, my_color=my_color)
        return True

    if room_data and game.get("draw_offer_from"):
        await _decline_draw_offer(room_id, game, room_data)
        game = await get_game(room_id)
        if not game:
            return False
        room_data = await get_room(room_id)

    if my_color != game.get("mover"):
        await _send_reject(websocket, WS_NOT_YOUR_TURN, game=game, room_data=room_data, my_color=my_color)
        return True

    client_ply = data.get("ply")
    expected_ply = next_ply(game)
    if client_ply != expected_ply:
        await _send_reject(
            websocket,
            "ws.ply_mismatch",
            game=game,
            room_data=room_data,
            my_color=my_color,
            ply=expected_ply,
        )
        return True

    if msg_type == "pass":
        raw_from, raw_to = 0, 0
    elif msg_type == "move":
        raw_from = data.get("from")
        raw_to = data.get("to")
        if not isinstance(raw_from, int) or not isinstance(raw_to, int):
            await _send_reject(websocket, "ws.invalid_move_data", game=game, room_data=room_data, my_color=my_color)
            return True
    else:
        await _send_v2(websocket, build_error("ws.unknown_command"))
        return True

    prev_mover = game["mover"]
    prev_board = _norm_board_keys(game.get("board", {}))
    position_history = game.setdefault("position_history", {})
    event = build_move_event_from_game(game, raw_from, raw_to)
    if msg_type == "pass":
        event = build_move_event_from_game(game, 0, 0)
        event.position_for_mandatory_capture = 0

    result = logic.handle_event(
        event,
        batyr_captured_this_turn=game.get("pending_batyr_captures"),
        position_history=position_history,
        moves_with_two_biys=game.get("moves_with_two_biys", 0),
    )

    if is_rejected_move(result, prev_board, raw_from, raw_to):
        reason = result.message_code or "move.impossible"
        record_move_rejected(reason)
        await _send_reject(
            websocket,
            reason,
            game=game,
            room_data=room_data,
            my_color=my_color,
            ply=expected_ply,
        )
        return True

    current_count = game.get("moves_with_two_biys", 0)
    if _only_two_biys_left(Board(result.updated_positions or game["board"])):
        game["moves_with_two_biys"] = current_count + 1
    else:
        game["moves_with_two_biys"] = 0

    persist_pending_mandatory_position(game, result, prev_mover)

    await _apply_and_broadcast_move(
        room_id, game, result, prev_mover, raw_from, raw_to,
        is_ai_room=is_ai_room,
        board_before=prev_board,
    )
    return True
