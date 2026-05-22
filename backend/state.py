import json
import time
from typing import Optional
import redis.asyncio as aioredis

# Redis клиент
redis_client: Optional[aioredis.Redis] = None


async def init_redis():
    """Инициализация Redis-клиента (вызывается при старте приложения)."""
    global redis_client
    redis_client = aioredis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    await redis_client.ping()


async def close_redis():
    """Закрытие Redis-клиента."""
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None


def _ensure_client():
    if redis_client is None:
        raise RuntimeError("Redis not initialized. Did you forget to init_redis()?")


# In-memory: таймеры (asyncio tasks) — не сохраняются в Redis
game_timers: dict[str, object] = {}
disconnect_timers: dict[str, object] = {}

# Константы
DISCONNECT_TIMEOUT = 30


# === GAME STATE ===

async def get_game(room_id: str) -> Optional[dict]:
    """Загружает состояние игры из Redis."""
    _ensure_client()
    data = await redis_client.get(f"game:{room_id}")
    if data is None:
        return None
    return json.loads(data)


async def set_game(room_id: str, data: dict):
    """Сохраняет состояние игры в Redis."""
    _ensure_client()
    await redis_client.set(f"game:{room_id}", json.dumps(data, default=str))


async def delete_game(room_id: str):
    """Удаляет состояние игры из Redis."""
    _ensure_client()
    await redis_client.delete(f"game:{room_id}")


# === ROOM STATE ===

async def get_room(room_id: str) -> Optional[dict]:
    """Загружает комнату из Redis."""
    _ensure_client()
    data = await redis_client.get(f"room:{room_id}")
    if data is None:
        return None
    return json.loads(data)


async def set_room(room_id: str, data: dict):
    """Сохраняет комнату в Redis."""
    _ensure_client()
    await redis_client.set(f"room:{room_id}", json.dumps(data, default=str))


async def delete_room(room_id: str):
    """Удаляет комнату из Redis."""
    _ensure_client()
    await redis_client.delete(f"room:{room_id}")