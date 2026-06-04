"""Общий чат на главной странице (лобби)."""

import json
import time
from fastapi import WebSocket

from backend.chat import sanitize_chat_text
from backend.db.models import User
from backend.message_codes import ws_error
from backend.player_identity import display_name, meta_from_user
from backend import state

LOBBY_CHAT_MAX_MESSAGES = 30
LOBBY_CHAT_MAX_LENGTH = 500
LOBBY_CHAT_MIN_INTERVAL = 3.0
LOBBY_CHAT_REDIS_KEY = "lobby_chat:messages"

_memory_messages: list[dict] = []


class LobbyChatManager:
    def __init__(self):
        self.connections: dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        self.connections[client_id] = websocket

    async def disconnect(self, client_id: str) -> None:
        self.connections.pop(client_id, None)

    async def send_to_client(self, client_id: str, data: dict) -> None:
        ws = self.connections.get(client_id)
        if ws:
            await self._send(ws, data)

    async def broadcast(self, data: dict, *, except_client_id: str | None = None) -> None:
        for cid, ws in list(self.connections.items()):
            if except_client_id and cid == except_client_id:
                continue
            await self._send(ws, data)

    @staticmethod
    async def _send(websocket: WebSocket, data: dict) -> None:
        try:
            await websocket.send_json(data)
        except Exception:
            pass


lobby_chat_manager = LobbyChatManager()


async def get_history() -> list[dict]:
    if state.redis_client is not None:
        raw = await state.redis_client.get(LOBBY_CHAT_REDIS_KEY)
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    trimmed = data[-LOBBY_CHAT_MAX_MESSAGES:]
                    if len(data) > len(trimmed):
                        await _save_history(trimmed)
                    return trimmed
            except json.JSONDecodeError:
                pass
        return []
    return list(_memory_messages[-LOBBY_CHAT_MAX_MESSAGES:])


async def _save_history(messages: list[dict]) -> None:
    trimmed = messages[-LOBBY_CHAT_MAX_MESSAGES:]
    if state.redis_client is not None:
        await state.redis_client.set(LOBBY_CHAT_REDIS_KEY, json.dumps(trimmed))
    else:
        global _memory_messages
        _memory_messages = list(trimmed)


async def _cooldown_active(client_id: str) -> bool:
    if state.redis_client is not None:
        key = f"lobby_chat:cooldown:{client_id}"
        exists = await state.redis_client.exists(key)
        return bool(exists)
    messages = await get_history()
    now = time.time()
    for entry in reversed(messages):
        if entry.get("client_id") != client_id:
            continue
        ts = entry.get("ts")
        if isinstance(ts, (int, float)):
            return (now - float(ts)) < LOBBY_CHAT_MIN_INTERVAL
        return False
    return False


async def _set_cooldown(client_id: str) -> None:
    if state.redis_client is not None:
        key = f"lobby_chat:cooldown:{client_id}"
        await state.redis_client.set(key, "1", ex=int(LOBBY_CHAT_MIN_INTERVAL))


def _build_entry(client_id: str, text: str, ts: float, user: User | None) -> dict:
    meta = meta_from_user(user)
    return {
        "client_id": client_id,
        "username": meta.get("username"),
        "text": text,
        "ts": ts,
        "is_anonymous": meta.get("is_anonymous", True),
        "display_name": display_name(meta),
    }


def _to_broadcast(entry: dict) -> dict:
    return {
        "type": "chat",
        "client_id": entry["client_id"],
        "from_client_id": entry["client_id"],
        "username": entry.get("username"),
        "text": entry["text"],
        "is_anonymous": entry.get("is_anonymous", True),
        "ts": entry["ts"],
        "display_name": entry.get("display_name"),
    }


async def send_lobby_chat_history(websocket: WebSocket) -> None:
    history = await get_history()
    await lobby_chat_manager._send(
        websocket,
        {"type": "chat_history", "messages": history},
    )


async def handle_lobby_chat_message(
    client_id: str,
    websocket: WebSocket,
    data: dict,
    user: User | None,
) -> bool:
    text = sanitize_chat_text(str(data.get("text", "")), LOBBY_CHAT_MAX_LENGTH)
    if not text:
        await lobby_chat_manager._send(websocket, ws_error("chat.empty"))
        return True

    if await _cooldown_active(client_id):
        await lobby_chat_manager._send(websocket, ws_error("chat.too_fast"))
        return True

    ts = time.time()
    entry = _build_entry(client_id, text, ts, user)
    messages = await get_history()
    messages.append(entry)
    await _save_history(messages)
    await _set_cooldown(client_id)

    await lobby_chat_manager.broadcast(_to_broadcast(entry))
    return True


async def clear_lobby_chat_storage() -> None:
    """Test helper: reset lobby chat history."""
    global _memory_messages
    _memory_messages = []
    if state.redis_client is not None:
        await state.redis_client.delete(LOBBY_CHAT_REDIS_KEY)
