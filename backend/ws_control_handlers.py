"""Обработчики control-сообщений WS (реванш, ничья, сдача)."""

from __future__ import annotations

from fastapi import WebSocket

from backend.board_utils import keys_int_to_str
from backend.game_helpers import color_has_moved, opposite_color
from backend.state import get_game, set_game, get_room, set_room
from backend.ws_manager import manager

CONTROL_MESSAGE_TYPES = frozenset({
    "request_rematch",
    "decline_draw",
    "offer_draw",
    "resign",
    "cancel_game",
})


async def handle_request_rematch(
    room_id: str,
    client_id: str,
    websocket: WebSocket,
    *,
    is_ai_room: bool,
) -> bool:
    if is_ai_room:
        return True
    from backend.game_session import _broadcast_rematch_status, _start_rematch

    game = await get_game(room_id)
    room_data = await get_room(room_id)
    if not game or not room_data or not game.get("game_over", False):
        return True
    if client_id not in manager.connections.get(room_id, {}):
        return True
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
        return True

    await _broadcast_rematch_status(room_id, room_data)
    if len(ready) >= 2 and all(cid in ready for cid in conns):
        await _start_rematch(room_id, room_data)
    return True


async def handle_decline_draw(
    room_id: str,
    client_id: str,
    websocket: WebSocket,
    *,
    is_ai_room: bool,
) -> bool:
    from backend.game_session import _decline_draw_offer

    game = await get_game(room_id)
    if not game or game.get("game_over", False):
        return True
    room_data = await get_room(room_id)
    if not room_data:
        return True
    my_color = room_data.get("players", {}).get(client_id)
    offerer = game.get("draw_offer_from")
    if offerer and my_color and offerer != my_color:
        await _decline_draw_offer(room_id, game, room_data)
    return True


async def handle_offer_draw(
    room_id: str,
    client_id: str,
    websocket: WebSocket,
    *,
    is_ai_room: bool,
) -> bool:
    game = await get_game(room_id)
    if not game or game.get("game_over", False):
        return True
    room_data = await get_room(room_id)
    my_color = room_data.get("players", {}).get(client_id) if room_data else None
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
        return True

    other_color = opposite_color(my_color)
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
        return True

    if pending == my_color:
        await manager.send_to_player(websocket, {
            "status": "draw_offered",
            "message": "Вы уже предложили ничью. Ожидание ответа соперника.",
        })
        return True

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
    return True


async def handle_resign(
    room_id: str,
    client_id: str,
    websocket: WebSocket,
    *,
    is_ai_room: bool,
) -> bool:
    game = await get_game(room_id)
    if not game or game.get("game_over", False):
        return True
    room_data = await get_room(room_id)
    my_color = room_data.get("players", {}).get(client_id) if room_data else None
    if not my_color:
        my_color = "белый"
    winner = opposite_color(my_color)
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
    return True


async def handle_cancel_game(
    room_id: str,
    client_id: str,
    websocket: WebSocket,
    *,
    is_ai_room: bool,
) -> bool:
    if is_ai_room:
        return True

    game = await get_game(room_id)
    if not game or game.get("game_over", False):
        return True
    room_data = await get_room(room_id)
    if not room_data:
        return True
    my_color = room_data.get("players", {}).get(client_id)
    if not my_color:
        await manager.send_to_player(websocket, {
            "status": "error",
            "message": "Не удалось определить ваш цвет.",
        })
        return True

    if color_has_moved(game, my_color):
        await manager.send_to_player(websocket, {
            "status": "error",
            "message": "Игра уже началась — отменить нельзя.",
        })
        return True

    game["game_over"] = True
    game["winner"] = ""
    game["reason"] = "cancelled"
    game.pop("draw_offer_from", None)
    await set_game(room_id, game)
    room_data["rematch_ready"] = []
    await set_room(room_id, room_data)

    try:
        from backend.timers import stop_game_timer
        stop_game_timer(room_id)
    except Exception:
        pass

    for cid, ws in manager.connections.get(room_id, {}).items():
        color = room_data.get("players", {}).get(cid)
        if color == my_color:
            text = "Вы отменили игру."
        else:
            text = "Соперник отменил игру."
        try:
            await ws.send_json({
                "game_over": True,
                "winner": text,
                "reason": "cancelled",
                "desk": keys_int_to_str(game.get("board", {})),
            })
        except Exception:
            pass
    return True


CONTROL_HANDLERS = {
    "request_rematch": handle_request_rematch,
    "decline_draw": handle_decline_draw,
    "offer_draw": handle_offer_draw,
    "resign": handle_resign,
    "cancel_game": handle_cancel_game,
}


async def dispatch_control_message(
    msg_type: str,
    room_id: str,
    client_id: str,
    websocket: WebSocket,
    *,
    is_ai_room: bool,
) -> bool:
    handler = CONTROL_HANDLERS.get(msg_type)
    if not handler:
        return True
    return await handler(room_id, client_id, websocket, is_ai_room=is_ai_room)
