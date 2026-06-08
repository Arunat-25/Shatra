from fastapi import HTTPException
import uuid
import json
import logging
from datetime import datetime

from backend.message_codes import ROOM_FULL, ROOM_GAME_STARTED, ROOM_NOT_FOUND

from backend.db.models import User
from backend.models import CreateRoomRequest, Room
from backend.player_identity import meta_from_user
from backend.rating.elo import DEFAULT_RATING
from backend.observability.metrics import record_room_created
from backend.state import get_room, set_room, scan_keys, get_raw, get_game

logger = logging.getLogger(__name__)


def _resolve_creator_username(room_data: dict) -> str | None:
    """Username from room field or registered creator player_meta."""
    username = room_data.get("creator_username")
    if username:
        return username
    creator_id = room_data.get("creator_client_id")
    if not creator_id:
        return None
    meta = (room_data.get("player_meta") or {}).get(creator_id) or {}
    if meta.get("is_anonymous", True):
        return None
    return meta.get("username")


def _resolve_creator_rating(room_data: dict) -> int | None:
    """Elo for registered room creator; None for anonymous."""
    creator_id = room_data.get("creator_client_id")
    if not creator_id:
        return None
    meta = (room_data.get("player_meta") or {}).get(creator_id) or {}
    if meta.get("is_anonymous", True):
        return None
    rating = meta.get("rating")
    return DEFAULT_RATING if rating is None else rating


async def create_room(request: CreateRoomRequest, user: User | None = None) -> dict:
    room_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow()
    room = Room(
        room_id=room_id,
        type=request.type,
        created_at=now,
        time_control=request.time_control,
        increment=request.increment,
        creator_client_id=request.creator_client_id,
        creator_color_preference=request.color_preference,
        ai_difficulty="strong" if request.type == "ai" else "easy",
    )
    if user:
        room.creator_user_id = str(user.id)
        room.creator_username = user.username
    if request.creator_client_id:
        room.player_meta[request.creator_client_id] = meta_from_user(user)
    if request.type == "private" and request.rated:
        room.rated = True
    if request.time_control:
        room.timer_white = float(request.time_control)
        room.timer_black = float(request.time_control)
        room.last_tick = now.timestamp()

    await set_room(room_id, room.model_dump())
    record_room_created(request.type)
    logger.info("Room created: %s (type=%s, time_control=%s)", room_id, request.type, request.time_control)
    return {"room_id": room_id, "type": request.type}


async def count_active_games() -> int:
    """Rooms with a live player connection, game started, and not over."""
    from backend.ws_manager import manager

    live_rooms = manager.connections
    count = 0
    for room_id, conns in live_rooms.items():
        if not conns:
            continue
        room_data = await get_room(room_id)
        if not room_data or not room_data.get("game_started"):
            continue
        game = await get_game(room_id)
        if game and not game.get("game_over", False):
            count += 1
    return count


async def list_rooms() -> dict:
    """Возвращает список активных комнат (ожидающих второго игрока)."""
    keys = await scan_keys("room:*")
    rooms_data = []
    for key in keys:
        raw = await get_raw(key)
        if raw:
            r = json.loads(raw)
            if not r.get("game_started") and r.get("type") == "public":
                rooms_data.append({
                    "room_id": r["room_id"],
                    "type": r["type"],
                    "created_at": r.get("created_at", ""),
                    "time_control": r.get("time_control"),
                    "increment": r.get("increment") or 0,
                    "creator_username": _resolve_creator_username(r),
                    "creator_rating": _resolve_creator_rating(r),
                })
    active_games = await count_active_games()
    return {
        "rooms": rooms_data,
        "stats": {
            "waiting_public_rooms": len(rooms_data),
            "active_games": active_games,
        },
    }


async def join_room(room_id: str) -> dict:
    room_data = await get_room(room_id)
    if not room_data:
        logger.warning("Room not found: %s", room_id)
        raise HTTPException(status_code=404, detail=ROOM_NOT_FOUND)
    if room_data.get("game_started"):
        raise HTTPException(status_code=409, detail=ROOM_GAME_STARTED)
    players = room_data.get("players") or {}
    if len(players) >= 2:
        raise HTTPException(status_code=409, detail=ROOM_FULL)
    return {"room_id": room_id}
