import uuid
import json
import logging
from datetime import datetime

from fastapi import HTTPException

from backend.models import CreateRoomRequest, Room
from backend.state import get_room, set_room, delete_room, scan_keys, get_raw

logger = logging.getLogger(__name__)


async def create_room(request: CreateRoomRequest) -> dict:
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
    )
    if request.time_control:
        room.timer_white = float(request.time_control)
        room.timer_black = float(request.time_control)
        room.last_tick = now.timestamp()

    await set_room(room_id, room.model_dump())
    logger.info("Room created: %s (type=%s, time_control=%s)", room_id, request.type, request.time_control)
    return {"room_id": room_id, "type": request.type}


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
                })
    return {"rooms": rooms_data}


async def join_room(room_id: str) -> dict:
    room_data = await get_room(room_id)
    if not room_data:
        logger.warning("Room not found: %s", room_id)
        raise HTTPException(status_code=404, detail="Комната не найдена")
    if room_data.get("game_started"):
        raise HTTPException(status_code=409, detail="Игра в этой комнате уже началась")
    players = room_data.get("players") or {}
    if len(players) >= 2:
        raise HTTPException(status_code=409, detail="Комната уже заполнена")
    return {"room_id": room_id}
