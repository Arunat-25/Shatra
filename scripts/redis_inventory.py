"""
Dev script: Redis inventory for Shatra.

Shows:
- counts of room:* and game:* keys
- breakdown of rooms by type and game_started
- orphan keys (room without game, game without room)
- top N oldest rooms (by created_at when available)

Run:
  python scripts/redis_inventory.py

Env:
  REDIS_HOST=127.0.0.1
  REDIS_PORT=6379
  REDIS_DB=0
  LIMIT=10
"""

from __future__ import annotations

import asyncio
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis


def _dt_parse(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.utcfromtimestamp(float(value))
        except Exception:
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # pydantic datetime -> ISO string
        try:
            # Handle trailing 'Z' (common)
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return datetime.fromisoformat(s)
        except Exception:
            return None
    return None


async def _scan_keys(redis: aioredis.Redis, pattern: str) -> list[str]:
    cursor = 0
    out: list[str] = []
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=500)
        out.extend(keys)
        if cursor == 0:
            return out


async def _get_json(redis: aioredis.Redis, key: str) -> dict | None:
    raw = await redis.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return {"__raw__": raw}


async def main() -> int:
    host = os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    limit = int(os.getenv("LIMIT", "10"))

    redis = aioredis.Redis(host=host, port=port, db=db, decode_responses=True)
    await redis.ping()

    room_keys = await _scan_keys(redis, "room:*")
    game_keys = await _scan_keys(redis, "game:*")

    print(f"[counts] room:*={len(room_keys)} game:*={len(game_keys)}")

    rooms_by_type_started: Counter[tuple[str, bool]] = Counter()
    rooms_by_type: Counter[str] = Counter()
    rooms_missing_fields = 0
    parsed_rooms: list[dict] = []

    for rk in room_keys:
        data = await _get_json(redis, rk)
        if not data:
            continue
        rtype = data.get("type") or "unknown"
        started = bool(data.get("game_started", False))
        rooms_by_type_started[(rtype, started)] += 1
        rooms_by_type[rtype] += 1
        if "created_at" not in data:
            rooms_missing_fields += 1
        created = _dt_parse(data.get("created_at"))
        parsed_rooms.append(
            {
                "key": rk,
                "room_id": data.get("room_id"),
                "type": rtype,
                "game_started": started,
                "created_at": created,
                "creator_client_id": data.get("creator_client_id"),
                "players_count": len((data.get("players") or {}).keys()),
            }
        )

    if rooms_by_type:
        print("[rooms] by type:")
        for t, c in rooms_by_type.most_common():
            print(f"  - {t}: {c}")

    if rooms_by_type_started:
        print("[rooms] by (type, game_started):")
        for (t, started), c in sorted(rooms_by_type_started.items(), key=lambda x: (-x[1], x[0][0], x[0][1])):
            print(f"  - ({t}, started={started}): {c}")

    if rooms_missing_fields:
        print(f"[rooms] missing created_at: {rooms_missing_fields}")

    room_ids = {k.split("room:", 1)[1] for k in room_keys if k.startswith("room:")}
    game_ids = {k.split("game:", 1)[1] for k in game_keys if k.startswith("game:")}

    orphan_rooms = sorted(room_ids - game_ids)
    orphan_games = sorted(game_ids - room_ids)

    print(f"[orphan] rooms_without_game={len(orphan_rooms)} games_without_room={len(orphan_games)}")
    if orphan_rooms[: min(5, len(orphan_rooms))]:
        print(f"  sample rooms_without_game: {orphan_rooms[:5]}")
    if orphan_games[: min(5, len(orphan_games))]:
        print(f"  sample games_without_room: {orphan_games[:5]}")

    # Oldest rooms (by created_at if present)
    with_dt = [r for r in parsed_rooms if r.get("created_at") is not None]
    without_dt = [r for r in parsed_rooms if r.get("created_at") is None]

    if with_dt:
        with_dt.sort(key=lambda r: r["created_at"])
        print(f"[oldest] top {min(limit, len(with_dt))} rooms by created_at:")
        for r in with_dt[:limit]:
            dt = r["created_at"].isoformat()
            print(
                f"  - {r['room_id']} key={r['key']} type={r['type']} started={r['game_started']} "
                f"players={r['players_count']} creator={bool(r['creator_client_id'])} created_at={dt}"
            )

    if without_dt:
        print(f"[unknown_created_at] rooms_without_created_at={len(without_dt)} (showing up to {min(limit, len(without_dt))})")
        for r in without_dt[:limit]:
            print(
                f"  - {r['room_id']} key={r['key']} type={r['type']} started={r['game_started']} "
                f"players={r['players_count']} creator={bool(r['creator_client_id'])}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

