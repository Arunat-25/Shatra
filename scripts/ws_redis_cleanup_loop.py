"""
Dev script: repeat WS connect/disconnect cycles and watch Redis keyspace.

This is useful when you can't "manually" open many games. It will:
- create a room
- connect 2 players (starts game)
- disconnect creator (should delete room/game)
- repeat N times
- report how many room:* and game:* keys exist after each iteration

Run:
  python scripts/ws_redis_cleanup_loop.py --n 50

Env:
  BASE_URL=http://127.0.0.1:8000
  WS_BASE=ws://127.0.0.1:8000
  REDIS_HOST=127.0.0.1
  REDIS_PORT=6379
  REDIS_DB=0
"""

from __future__ import annotations

import argparse
import asyncio
import os
import secrets

import httpx
import redis.asyncio as aioredis
import websockets


def _client_id() -> str:
    return secrets.token_hex(8)


async def _create_room(client: httpx.AsyncClient) -> str:
    r = await client.post("/rooms", json={"type": "friend"})
    r.raise_for_status()
    return r.json()["room_id"]


async def _count_keys(redis: aioredis.Redis, pattern: str) -> int:
    cursor = 0
    total = 0
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=200)
        total += len(keys)
        if cursor == 0:
            return total


async def _create_room_typed(client: httpx.AsyncClient, room_type: str) -> str:
    r = await client.post("/rooms", json={"type": room_type})
    r.raise_for_status()
    return r.json()["room_id"]


async def _one_iteration(base_url: str, ws_base: str, room_type: str) -> str:
    async with httpx.AsyncClient(base_url=base_url, timeout=10) as client:
        room_id = await _create_room_typed(client, room_type=room_type)

    ws_url = f"{ws_base}/ws/{room_id}/?client_id={{cid}}"
    p1 = _client_id()

    if room_type == "ai":
        # AI game starts immediately for the (white) player.
        async with websockets.connect(ws_url.format(cid=p1)) as ws1:
            await ws1.recv()  # game_started
        await asyncio.sleep(0.05)
        return room_id

    # friend/quick: 2 players; first gets waiting, then both get game_started
    p2 = _client_id()
    async with websockets.connect(ws_url.format(cid=p1)) as ws1:
        await ws1.recv()  # waiting
        async with websockets.connect(ws_url.format(cid=p2)) as ws2:
            await ws2.recv()  # game_started
            await ws1.recv()  # game_started
    await asyncio.sleep(0.05)
    return room_id


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--sleep", type=float, default=0.05)
    ap.add_argument("--type", dest="room_type", choices=["friend", "ai", "quick"], default="friend")
    args = ap.parse_args()

    base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    ws_base = os.getenv("WS_BASE", "ws://127.0.0.1:8000").rstrip("/")

    redis = aioredis.Redis(
        host=os.getenv("REDIS_HOST", "127.0.0.1"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True,
    )
    await redis.ping()

    print(f"[cfg] base_url={base_url} ws_base={ws_base}")
    print(f"[cfg] room_type={args.room_type}")
    print(f"[cfg] redis={os.getenv('REDIS_HOST','127.0.0.1')}:{os.getenv('REDIS_PORT','6379')}/{os.getenv('REDIS_DB','0')}")

    for i in range(1, args.n + 1):
        rid = await _one_iteration(base_url, ws_base, room_type=args.room_type)
        await asyncio.sleep(args.sleep)
        rooms = await _count_keys(redis, "room:*")
        games = await _count_keys(redis, "game:*")
        print(f"[{i:03d}] room_id={rid} redis_keys: room:*={rooms} game:*={games}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

