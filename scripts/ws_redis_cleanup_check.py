"""
Dev script: PVP WebSocket + Redis cleanup verification.

What it does:
- POST /rooms to create a room
- Connect WS player1 (creator) and wait for "waiting"
- Connect WS player2 to start the game
- Close player1 connection (creator) -> server should destroy room + game
- Verify Redis keys room:{room_id} and game:{room_id} are removed

Run:
  python scripts/ws_redis_cleanup_check.py

Env:
  BASE_URL=http://127.0.0.1:8000
  WS_BASE=ws://127.0.0.1:8000
  REDIS_HOST=127.0.0.1
  REDIS_PORT=6379
  REDIS_DB=0
"""

from __future__ import annotations

import asyncio
import os
import secrets
from dataclasses import dataclass
from typing import Any

import httpx
import redis.asyncio as aioredis
import websockets


@dataclass(frozen=True)
class Cfg:
    base_url: str
    ws_base: str
    redis_host: str
    redis_port: int
    redis_db: int


def _cfg() -> Cfg:
    return Cfg(
        base_url=os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
        ws_base=os.getenv("WS_BASE", "ws://127.0.0.1:8000").rstrip("/"),
        redis_host=os.getenv("REDIS_HOST", "127.0.0.1"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        redis_db=int(os.getenv("REDIS_DB", "0")),
    )


def _client_id() -> str:
    # ConnectionManager only checks "truthy" and uniqueness within room.
    return secrets.token_hex(8)


async def _create_room(base_url: str, room_type: str = "friend") -> str:
    async with httpx.AsyncClient(base_url=base_url, timeout=10) as client:
        r = await client.post("/rooms", json={"type": room_type})
        r.raise_for_status()
        data = r.json()
        return data["room_id"]


async def _redis_get_json(redis: aioredis.Redis, key: str) -> Any | None:
    raw = await redis.get(key)
    return raw


async def main() -> int:
    cfg = _cfg()
    redis = aioredis.Redis(
        host=cfg.redis_host,
        port=cfg.redis_port,
        db=cfg.redis_db,
        decode_responses=True,
    )

    try:
        await redis.ping()
    except Exception as e:
        raise SystemExit(f"Redis ping failed: {e}") from e

    room_id = await _create_room(cfg.base_url, room_type="friend")
    p1 = _client_id()
    p2 = _client_id()

    room_key = f"room:{room_id}"
    game_key = f"game:{room_id}"

    ws_url = f"{cfg.ws_base}/ws/{room_id}/?client_id={{cid}}"

    print(f"[info] room_id={room_id} p1={p1} p2={p2}")
    print(f"[info] ws_url={ws_url.format(cid=p1)}")

    # Before WS connections, room exists; game typically does not.
    room_before = await _redis_get_json(redis, room_key)
    game_before = await _redis_get_json(redis, game_key)
    print(f"[redis] before: room={room_before is not None}, game={game_before is not None}")

    async with websockets.connect(ws_url.format(cid=p1)) as ws1:
        # First player should receive {"status":"waiting", ...} until second joins.
        waiting = await ws1.recv()
        print(f"[ws1] first={waiting}")

        async with websockets.connect(ws_url.format(cid=p2)) as ws2:
            # After second joins, both should receive game_started.
            msg2 = await ws2.recv()
            print(f"[ws2] first={msg2}")

            # ws1 may receive game_started now (or already had waiting then game_started)
            msg1_next = await ws1.recv()
            print(f"[ws1] second={msg1_next}")

        # Now close creator connection. ConnectionManager.disconnect() should destroy the room.
        # Exiting context will close ws1.

    # Give server a short moment to process disconnect and Redis deletes.
    await asyncio.sleep(0.25)

    room_after = await _redis_get_json(redis, room_key)
    game_after = await _redis_get_json(redis, game_key)

    print(f"[redis] after: room={room_after is not None}, game={game_after is not None}")

    ok = (room_after is None) and (game_after is None)
    if ok:
        print("[ok] Redis cleanup: room/game keys removed after creator disconnect.")
        return 0

    print("[fail] Redis cleanup: expected room/game keys to be deleted.")
    if room_after is not None:
        print(f"  still present: {room_key}")
    if game_after is not None:
        print(f"  still present: {game_key}")
    return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

