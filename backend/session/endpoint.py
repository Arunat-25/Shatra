import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from backend.state import get_game, get_room, set_room, game_timers
from backend.ws_manager import manager, handle_player2_join
from backend.timers import game_ticker
from backend.models import Room
from backend.game_helpers import build_game_started_response, get_player_color
from backend.chat import send_chat_history
from backend.db.session import get_session_factory
from backend.player_identity import build_players_info, refresh_pvp_ratings_for_room, resolve_user_from_access_token
from backend.session.ai import _start_ai_game
from backend.session.disconnect import _handle_disconnect
from backend.session.rematch import _broadcast_rematch_status
from backend.session.messages import process_client_message, _send_ws_error

logger = logging.getLogger(__name__)


async def _wait_for_second_player(
    websocket: WebSocket,
    room_id: str,
    room_data: dict,
    client_id: str,
) -> dict | None:
    """Ожидание второго игрока (пока в комнате один участник)."""
    room_type = room_data.get("type")
    await manager.send_to_player(websocket, {
        "status": "waiting",
        "link": room_id,
        "room_type": room_type,
        "show_invite_link": (
            room_type == "private"
            and client_id == room_data.get("creator_client_id")
        ),
        "players_info": build_players_info(room_data),
    })
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


async def websocket_endpoint(websocket: WebSocket, room_id: str):
    client_id = websocket.query_params.get("client_id")
    if not client_id:
        await websocket.close(code=1008)
        return

    access_token = websocket.query_params.get("access_token")
    user = None
    factory = get_session_factory()
    async with factory() as db:
        user = await resolve_user_from_access_token(access_token, db)

    if not await manager.connect(room_id, websocket, client_id, user=user):
        return

    room_data = await get_room(room_id)
    if not room_data:
        return

    is_ai_room = room_data.get("type") == "ai"
    if not is_ai_room:
        await send_chat_history(websocket, room_data)

    room_obj = Room(**room_data)
    mover_for_timer = None
    game_snapshot = None
    if room_data.get("game_started"):
        game_snapshot = await get_game(room_id)
        if game_snapshot:
            mover_for_timer = game_snapshot.get("mover")
    room_obj.correct_timers_after_restart(mover_for_timer, game_snapshot)
    room_data = room_obj.model_dump()
    await set_room(room_id, room_data)

    my_color = get_player_color(room_data, client_id)
    players_in_room = len(room_data.get("players") or {})

    if is_ai_room:
        await _start_ai_game(room_id, websocket, room_data, my_color)
    elif room_data.get("game_started"):
        game = await get_game(room_id)
        if game:
            if room_data.get("type") in ("public", "private"):
                await refresh_pvp_ratings_for_room(room_data)
                await set_room(room_id, room_data)
            response = build_game_started_response(game, room_data, my_color)
            await manager.send_to_player(websocket, response)
            if game.get("game_over") and not is_ai_room:
                await _broadcast_rematch_status(room_id, room_data)
            elif room_data.get("time_control") and room_id not in game_timers:
                game_timers[room_id] = asyncio.create_task(game_ticker(room_id))
    elif players_in_room < 2:
        room_data = await _wait_for_second_player(websocket, room_id, room_data, client_id)
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
                logger.info("WebSocket runtime error in room %s (closing loop): %s", room_id, e)
                break
            except Exception as e:
                msg = str(e)
                if "WebSocket is not connected" in msg:
                    logger.info("WebSocket not connected in room %s (closing loop)", room_id)
                    break
                logger.warning(
                    "Invalid JSON from client %s in room %s: %s",
                    client_id[:6],
                    room_id,
                    e,
                )
                await _send_ws_error(websocket, "ws.invalid_json")
                continue

            if not isinstance(data, dict):
                await _send_ws_error(websocket, "ws.expected_object")
                continue

            if not await process_client_message(
                room_id, client_id, data, websocket, is_ai_room=is_ai_room
            ):
                break

    except WebSocketDisconnect:
        await _handle_disconnect(room_id, websocket, is_ai_room)
