import json
import time
from typing import Optional
import redis.asyncio as aioredis
import os

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


def ensure_redis(fn):
    """Декоратор: проверяет, что Redis инициализирован, перед вызовом."""
    import functools
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        if redis_client is None:
            raise RuntimeError("Redis not initialized. Did you forget to init_redis()?")
        return await fn(*args, **kwargs)
    return wrapper


# === REDIS UTILITY ===

@ensure_redis
async def scan_keys(pattern: str, count: int = 100) -> list[str]:
    """Сканирует Redis по паттерну и возвращает список ключей."""
    cursor = 0
    all_keys = []
    while True:
        cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=count)
        all_keys.extend(keys)
        if cursor == 0:
            break
    return all_keys


@ensure_redis
async def get_raw(key: str) -> Optional[str]:
    """Возвращает сырое значение из Redis."""
    return await redis_client.get(key)


# In-memory: таймеры (asyncio tasks) — не сохраняются в Redis
game_timers: dict[str, object] = {}
disconnect_timers: dict[str, object] = {}

# Константы
DISCONNECT_TIMEOUT = 30


# === GAME STATE ===

def _redis_ttl_seconds() -> int:
    """
    TTL для ключей room:* и game:* (секунды).
    По умолчанию 4 часа, можно переопределить через env REDIS_TTL_SECONDS.
    """
    raw = os.getenv("REDIS_TTL_SECONDS", "").strip()
    if not raw:
        return 4 * 60 * 60
    try:
        ttl = int(raw)
        return ttl if ttl > 0 else 4 * 60 * 60
    except Exception:
        return 4 * 60 * 60


@ensure_redis
async def get_game(room_id: str) -> Optional[dict]:
    """Загружает состояние игры из Redis."""
    data = await redis_client.get(f"game:{room_id}")
    if data is None:
        return None
    return json.loads(data)


@ensure_redis
async def set_game(room_id: str, data: dict):
    """Сохраняет состояние игры в Redis."""
    await redis_client.set(
        f"game:{room_id}",
        json.dumps(data, default=str),
        ex=_redis_ttl_seconds(),
    )


@ensure_redis
async def delete_game(room_id: str):
    """Удаляет состояние игры из Redis."""
    await redis_client.delete(f"game:{room_id}")


# === ROOM STATE ===

@ensure_redis
async def get_room(room_id: str) -> Optional[dict]:
    """Загружает комнату из Redis."""
    data = await redis_client.get(f"room:{room_id}")
    if data is None:
        return None
    return json.loads(data)


@ensure_redis
async def set_room(room_id: str, data: dict):
    """Сохраняет комнату в Redis."""
    await redis_client.set(
        f"room:{room_id}",
        json.dumps(data, default=str),
        ex=_redis_ttl_seconds(),
    )


@ensure_redis
async def delete_room(room_id: str):
    """Удаляет комнату из Redis."""
    await redis_client.delete(f"room:{room_id}")