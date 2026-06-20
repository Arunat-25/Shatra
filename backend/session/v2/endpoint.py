"""WebSocket endpoint for protocol v2 (`/ws/v2/{room_id}/`)."""

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from backend.state import get_game, get_room, set_room, game_timers
from backend.ws_manager import manager, handle_player2_join
from backend.timers import game_ticker
from backend.models import Room
from backend.game_helpers import get_player_color
from backend.chat import send_chat_history
from backend.db.session import get_session_factory
from backend.player_identity import build_players_info, refresh_pvp_ratings_for_room, resolve_user_from_access_token
from backend.session.ai import _start_ai_game
from backend.session.disconnect import _handle_disconnect
from backend.session.rematch import _broadcast_rematch_status
from backend.session.v2.messages import process_v2_client_message
from backend.session.v2.protocol import PROTO_VERSION, build_waiting, build_error

logger = logging.getLogger(__name__)


async def _wait_for_second_player_v2(
    websocket: WebSocket,
    room_id: str,
    room_data: dict,
    client_id: str,
    *,
    is_ai_room: bool,
) -> dict | None:
    room_type = room_data.get("type")
    await manager.send_to_player(
        websocket,
        build_waiting(
            room_id,
            room_data,
            client_id=client_id,
            players_info=build_players_info(room_data),
        ),
    )
    try:
        while not room_data.get("game_started"):
            rd = await get_room(room_id)
            if rd:
                room_data = rd
            if room_data.get("game_started"):
                break
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            if isinstance(data, dict):
                await process_v2_client_message(
                    room_id, client_id, data, websocket, is_ai_room=is_ai_room
                )
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


async def websocket_endpoint_v2(websocket: WebSocket, room_id: str):
    client_id = websocket.query_params.get("client_id")
    if not client_id:
        await websocket.close(code=1008)
        return

    access_token = websocket.query_params.get("access_token")
    user = None
    factory = get_session_factory()
    async with factory() as db:
        user = await resolve_user_from_access_token(access_token, db)

    if not await manager.connect(room_id, websocket, client_id, user=user, proto=PROTO_VERSION):
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
            await manager.send_join_state(websocket, room_id, client_id, game, room_data, my_color)
            if game.get("game_over") and not is_ai_room:
                await _broadcast_rematch_status(room_id, room_data)
            elif room_data.get("time_control") and room_id not in game_timers:
                game_timers[room_id] = asyncio.create_task(game_ticker(room_id))
    elif players_in_room < 2:
        room_data = await _wait_for_second_player_v2(
            websocket, room_id, room_data, client_id, is_ai_room=is_ai_room
        )
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
                logger.info("WebSocket v2 runtime error in room %s (closing loop): %s", room_id, e)
                break
            except Exception as e:
                msg = str(e)
                if "WebSocket is not connected" in msg:
                    logger.info("WebSocket v2 not connected in room %s (closing loop)", room_id)
                    break
                logger.warning(
                    "Invalid JSON from client %s in room %s: %s",
                    client_id[:6],
                    room_id,
                    e,
                )
                await manager.send_to_player(websocket, build_error("ws.invalid_json"))
                continue

            if not isinstance(data, dict):
                await manager.send_to_player(websocket, build_error("ws.expected_object"))
                continue

            if not await process_v2_client_message(
                room_id, client_id, data, websocket, is_ai_room=is_ai_room
            ):
                break

    except WebSocketDisconnect:
        await _handle_disconnect(room_id, websocket, is_ai_room)
