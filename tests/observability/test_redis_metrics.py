"""Tests for Redis gauge refresh on /metrics scrape."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from backend.observability import metrics as m
from backend.observability.redis_metrics import refresh_redis_gauges


@pytest.mark.asyncio
async def test_refresh_counts_rooms_and_games_by_labels():
    rooms = {
        "room:a": json.dumps(
            {"type": "public", "game_started": False},
        ),
        "room:b": json.dumps(
            {"type": "public", "game_started": True},
        ),
        "room:c": json.dumps({"type": "ai", "game_started": True}),
    }
    games = {
        "game:b": json.dumps({"game_over": False}),
        "game:c": json.dumps({"game_over": True}),
    }

    async def fake_scan(pattern: str, count: int = 100):
        if pattern == "room:*":
            return list(rooms.keys())
        if pattern == "game:*":
            return list(games.keys())
        return []

    async def fake_get_raw(key: str):
        return rooms.get(key) or games.get(key)

    with (
        patch("backend.observability.redis_metrics.scan_keys", side_effect=fake_scan),
        patch("backend.observability.redis_metrics.get_raw", side_effect=fake_get_raw),
        patch("backend.observability.redis_metrics.state.redis_client", object()),
    ):
        await refresh_redis_gauges()

    assert m.REDIS_ROOMS_ACTIVE.labels(room_type="public")._value.get() == 2.0
    assert m.REDIS_ROOMS_ACTIVE.labels(room_type="ai")._value.get() == 1.0
    assert m.REDIS_ROOMS_WAITING.labels(room_type="public")._value.get() == 1.0
    assert m.REDIS_GAMES_ACTIVE.labels(game_over="false")._value.get() == 1.0
    assert m.REDIS_GAMES_ACTIVE.labels(game_over="true")._value.get() == 1.0


@pytest.mark.asyncio
async def test_refresh_zeros_gauges_when_redis_unavailable():
    with patch("backend.observability.redis_metrics.state.redis_client", None):
        await refresh_redis_gauges()

    assert m.REDIS_ROOMS_ACTIVE.labels(room_type="public")._value.get() == 0.0
    assert m.REDIS_GAMES_ACTIVE.labels(game_over="false")._value.get() == 0.0
    assert m.REDIS_ROOMS_WAITING.labels(room_type="public")._value.get() == 0.0


@pytest.mark.asyncio
async def test_refresh_treats_invalid_json_as_unknown_room():
    async def fake_scan(pattern: str, count: int = 100):
        return ["room:bad"] if pattern == "room:*" else []

    with (
        patch("backend.observability.redis_metrics.scan_keys", side_effect=fake_scan),
        patch("backend.observability.redis_metrics.get_raw", AsyncMock(return_value="not-json")),
        patch("backend.observability.redis_metrics.state.redis_client", object()),
    ):
        await refresh_redis_gauges()

    assert m.REDIS_ROOMS_ACTIVE.labels(room_type="unknown")._value.get() == 1.0
