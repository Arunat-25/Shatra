"""Refresh Redis state gauges on each /metrics scrape."""

from __future__ import annotations

import json
import time
from collections import Counter

from backend import state
from backend.observability.metrics import (
    REDIS_GAMES_ACTIVE,
    REDIS_ROOMS_ACTIVE,
    REDIS_ROOMS_WAITING,
)
from backend.state import get_raw, scan_keys

ROOM_TYPES = ("public", "private", "ai", "unknown")
GAME_OVER_LABELS = ("true", "false")
_GAUGE_CACHE_TTL_SECONDS = 10.0
_gauge_cache_expires_at = 0.0


def _zero_gauges() -> None:
    for room_type in ROOM_TYPES:
        REDIS_ROOMS_ACTIVE.labels(room_type=room_type).set(0)
    REDIS_ROOMS_WAITING.labels(room_type="public").set(0)
    for game_over in GAME_OVER_LABELS:
        REDIS_GAMES_ACTIVE.labels(game_over=game_over).set(0)


async def _scan_and_update_gauges() -> None:
    if state.redis_client is None:
        _zero_gauges()
        return

    _zero_gauges()

    rooms_by_type: Counter[str] = Counter()
    waiting_public = 0

    for key in await scan_keys("room:*"):
        raw = await get_raw(key)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            rooms_by_type["unknown"] += 1
            continue

        room_type = data.get("type") or "unknown"
        if room_type not in ROOM_TYPES:
            room_type = "unknown"
        rooms_by_type[room_type] += 1
        if room_type == "public" and not data.get("game_started"):
            waiting_public += 1

    games_by_over: Counter[str] = Counter()
    for key in await scan_keys("game:*"):
        raw = await get_raw(key)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            games_by_over["false"] += 1
            continue
        game_over = "true" if data.get("game_over") else "false"
        games_by_over[game_over] += 1

    for room_type, count in rooms_by_type.items():
        REDIS_ROOMS_ACTIVE.labels(room_type=room_type).set(count)
    REDIS_ROOMS_WAITING.labels(room_type="public").set(waiting_public)
    for game_over, count in games_by_over.items():
        REDIS_GAMES_ACTIVE.labels(game_over=game_over).set(count)


def invalidate_redis_gauges_cache() -> None:
    """Drop TTL cache so the next refresh scans Redis."""
    global _gauge_cache_expires_at
    _gauge_cache_expires_at = 0.0


async def refresh_redis_gauges(*, force: bool = False) -> None:
    """Scan room:* and game:* keys and update Prometheus gauges."""
    global _gauge_cache_expires_at
    if state.redis_client is None:
        _gauge_cache_expires_at = 0.0
        await _scan_and_update_gauges()
        return
    now = time.monotonic()
    if not force and now < _gauge_cache_expires_at:
        return
    await _scan_and_update_gauges()
    _gauge_cache_expires_at = now + _GAUGE_CACHE_TTL_SECONDS
