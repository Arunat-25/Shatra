import uuid
import logging
from datetime import datetime
from backend.models import CreateRoomRequest, Room
from backend.state import get_room, set_room, delete_room

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
    )
    if request.time_control:
        room.timer_player1 = float(request.time_control)
        room.timer_player2 = float(request.time_control)
        room.last_tick = now.timestamp()

    await set_room(room_id, room.model_dump())
    logger.info("Room created: %s (type=%s, time_control=%s)", room_id, request.type, request.time_control)
    return {"room_id": room_id, "type": request.type}


async def list_rooms() -> dict:
    """Возвращает список активных комнат (ожидающих второго игрока)."""
    # Redis не поддерживает сканирование по ключам с префиксом через список,
    # используем SCAN. Но для простоты — храним set с room_id активных комнат.
    # Пока что комнаты сканируем, но для продакшена лучше список.
    import redis.asyncio as aioredis
    from backend.state import redis_client
    cursor = 0
    rooms_data = []
    while True:
        cursor, keys = await redis_client.scan(cursor=cursor, match="room:*", count=100)
        for key in keys:
            data = await redis_client.get(key)
            if data:
                import json
                r = json.loads(data)
                if not r.get("game_started") and r.get("type") in ("quick",):
                    rooms_data.append({
                        "room_id": r["room_id"],
                        "type": r["type"],
                        "created_at": r.get("created_at", ""),
                    })
        if cursor == 0:
            break
    return {"rooms": rooms_data}


async def join_room(room_id: str) -> dict:
    room_data = await get_room(room_id)
    if not room_data:
        logger.warning("Room not found: %s", room_id)
        return {"error": "Комната не найдена"}
    return {"room_id": room_id}