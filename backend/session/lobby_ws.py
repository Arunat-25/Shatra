import logging

from fastapi import WebSocket, WebSocketDisconnect

from backend.db.session import get_session_factory
from backend.lobby_chat import (
    handle_lobby_chat_message,
    lobby_chat_manager,
    send_lobby_chat_history,
)
from backend.player_identity import resolve_user_from_access_token
from backend.presence import touch_lobby_presence
from backend.session.messages import _send_ws_error

logger = logging.getLogger(__name__)


async def lobby_websocket_endpoint(websocket: WebSocket) -> None:
    client_id = websocket.query_params.get("client_id")
    if not client_id:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    access_token = websocket.query_params.get("access_token")
    user = None
    factory = get_session_factory()
    async with factory() as db:
        user = await resolve_user_from_access_token(access_token, db)

    await touch_lobby_presence(
        client_id=client_id,
        user_id=user.id if user else None,
        is_anonymous=user is None,
    )

    await lobby_chat_manager.connect(client_id, websocket)
    try:
        await send_lobby_chat_history(websocket)

        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                raise
            except Exception as e:
                msg = str(e)
                if "WebSocket is not connected" in msg:
                    break
                logger.warning(
                    "Invalid JSON from lobby client %s: %s",
                    client_id[:6],
                    e,
                )
                await _send_ws_error(websocket, "ws.invalid_json")
                continue

            if not isinstance(data, dict):
                await _send_ws_error(websocket, "ws.expected_object")
                continue

            if data.get("type") == "chat":
                if not await handle_lobby_chat_message(client_id, websocket, data, user):
                    break
            else:
                await _send_ws_error(websocket, "ws.unknown_type")
    except WebSocketDisconnect:
        pass
    finally:
        await lobby_chat_manager.disconnect(client_id)
