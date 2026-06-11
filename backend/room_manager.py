from fastapi import HTTPException
import uuid
import logging
from datetime import datetime

from backend.message_codes import ROOM_FULL, ROOM_GAME_STARTED, ROOM_NOT_FOUND

from backend.db.models import User
from backend.models import CreateRoomRequest, Room
from backend.player_identity import meta_from_user
from backend.rating.elo import DEFAULT_RATING
from backend.observability.metrics import record_room_created
from backend.state import (
    add_waiting_public_room,
    get_game,
    get_room,
    get_waiting_public_room_ids,
    set_room,
)

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
    if request.type == "public":
        await add_waiting_public_room(room_id)
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
    rooms_data = []
    for room_id in await get_waiting_public_room_ids():
        room_data = await get_room(room_id)
        if not room_data:
            continue
        if room_data.get("game_started") or room_data.get("type") != "public":
            continue
        rooms_data.append({
            "room_id": room_data["room_id"],
            "type": room_data["type"],
            "created_at": room_data.get("created_at", ""),
            "time_control": room_data.get("time_control"),
            "increment": room_data.get("increment") or 0,
            "creator_username": _resolve_creator_username(room_data),
            "creator_rating": _resolve_creator_rating(room_data),
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
