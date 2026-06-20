import asyncio
import json
from typing import Optional
import redis.asyncio as aioredis

from backend.config import settings

# Redis клиент
redis_client: Optional[aioredis.Redis] = None


async def init_redis():
    """Инициализация Redis-клиента (вызывается при старте приложения)."""
    global redis_client
    if settings.redis_url:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    else:
        redis_client = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )
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


LOBBY_WAITING_PUBLIC_KEY = "lobby:waiting_public"


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

# In-memory: локи на комнату для сериализации read-modify-write над game/room.
# Защищают от потери обновлений при гонке тика часов и обработки хода.
_room_locks: dict[str, asyncio.Lock] = {}

# Константы (значения берутся из конфигурации, env-переопределяемы)
DISCONNECT_TIMEOUT = settings.disconnect_timeout


def get_room_lock(room_id: str) -> asyncio.Lock:
    """Per-room mutex for read-modify-write on game/room Redis keys.

    Callers already holding this lock must use ``_*_locked`` helpers
    (e.g. ``_finish_game_locked``, ``_archive_finished_game_locked``) —
    never the public wrappers that acquire the lock again (deadlock).
    """
    lock = _room_locks.get(room_id)
    if lock is None:
        lock = asyncio.Lock()
        _room_locks[room_id] = lock
    return lock


def drop_room_lock(room_id: str) -> None:
    """Убирает лок комнаты, если он свободен (вызывать после удаления комнаты)."""
    lock = _room_locks.get(room_id)
    if lock is not None and not lock.locked():
        _room_locks.pop(room_id, None)


# === GAME STATE ===

def _redis_ttl_seconds() -> int:
    """TTL для ключей room:* и game:* (секунды)."""
    return settings.redis_ttl_seconds


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
    await redis_client.srem(LOBBY_WAITING_PUBLIC_KEY, room_id)


@ensure_redis
async def add_waiting_public_room(room_id: str) -> None:
    """Track a public room waiting for the second player."""
    await redis_client.sadd(LOBBY_WAITING_PUBLIC_KEY, room_id)


@ensure_redis
async def remove_waiting_public_room(room_id: str) -> None:
    """Remove a room from the waiting-public lobby index."""
    await redis_client.srem(LOBBY_WAITING_PUBLIC_KEY, room_id)


@ensure_redis
async def get_waiting_public_room_ids() -> list[str]:
    """Return room ids of public rooms waiting for an opponent."""
    return list(await redis_client.smembers(LOBBY_WAITING_PUBLIC_KEY))