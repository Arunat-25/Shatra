"""Чат в игровой комнате (PvP)."""

import html
import re
import time

from fastapi import WebSocket

from backend.message_codes import ws_error
from backend.player_identity import display_name
from backend.state import get_room, redis_client, set_room
from backend.ws_manager import manager

CHAT_MAX_LENGTH = 200
CHAT_MAX_MESSAGES = 50
CHAT_RATE_LIMIT = 5
CHAT_RATE_WINDOW = 10
CHAT_MIN_INTERVAL = 1.0

_TAG_RE = re.compile(r"<[^>]+>")


def _last_message_ts(room_data: dict, client_id: str) -> float | None:
    messages = room_data.get("chat_messages") or []
    for entry in reversed(messages):
        if entry.get("client_id") == client_id:
            ts = entry.get("ts")
            if isinstance(ts, (int, float)):
                return float(ts)
    return None


def _is_consecutive_duplicate(room_data: dict, client_id: str, text: str) -> bool:
    """Reject only when the new text matches this player's immediately previous message."""
    messages = room_data.get("chat_messages") or []
    for entry in reversed(messages):
        if entry.get("client_id") != client_id:
            continue
        return entry.get("text") == text
    return False


def _too_soon(room_data: dict, client_id: str, now: float) -> bool:
    last_ts = _last_message_ts(room_data, client_id)
    if last_ts is None:
        return False
    return (now - last_ts) < CHAT_MIN_INTERVAL


def sanitize_chat_text(raw: str) -> str | None:
    text = html.unescape(raw or "").strip()
    text = _TAG_RE.sub("", text)
    text = " ".join(text.split())
    if not text:
        return None
    return text[:CHAT_MAX_LENGTH]


async def _check_rate_limit(room_id: str, client_id: str) -> bool:
    if redis_client is None:
        return True
    key = f"chat_rate:{room_id}:{client_id}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, CHAT_RATE_WINDOW)
    return count <= CHAT_RATE_LIMIT


def _append_message(room_data: dict, entry: dict) -> None:
    messages = room_data.setdefault("chat_messages", [])
    messages.append(entry)
    if len(messages) > CHAT_MAX_MESSAGES:
        room_data["chat_messages"] = messages[-CHAT_MAX_MESSAGES:]


async def send_chat_history(websocket: WebSocket, room_data: dict) -> None:
    history = room_data.get("chat_messages") or []
    if not history:
        return
    await manager.send_to_player(
        websocket,
        {"type": "chat_history", "messages": history},
    )


async def handle_chat_message(
    room_id: str,
    client_id: str,
    websocket: WebSocket,
    data: dict,
    *,
    is_ai_room: bool,
) -> bool:
    if is_ai_room:
        await manager.send_to_player(websocket, ws_error("chat.ai_unavailable"))
        return True

    room_data = await get_room(room_id)
    if not room_data:
        return False

    text = sanitize_chat_text(str(data.get("text", "")))
    if not text:
        await manager.send_to_player(websocket, ws_error("chat.empty"))
        return True

    if not await _check_rate_limit(room_id, client_id):
        await manager.send_to_player(websocket, ws_error("chat.rate_limit"))
        return True

    ts = time.time()
    if _is_consecutive_duplicate(room_data, client_id, text):
        await manager.send_to_player(websocket, ws_error("chat.duplicate"))
        return True

    if _too_soon(room_data, client_id, ts):
        await manager.send_to_player(websocket, ws_error("chat.too_fast"))
        return True

    meta = (room_data.get("player_meta") or {}).get(client_id) or {}
    entry = {
        "client_id": client_id,
        "username": meta.get("username"),
        "text": text,
        "ts": ts,
        "is_anonymous": meta.get("is_anonymous", True),
    }
    _append_message(room_data, entry)
    await set_room(room_id, room_data)

    broadcast = {
        "type": "chat",
        "from_client_id": client_id,
        "username": meta.get("username"),
        "text": text,
        "is_anonymous": meta.get("is_anonymous", True),
        "ts": ts,
        "display_name": display_name(meta),
    }
    await manager.send_to_room(room_id, broadcast)
    return True
