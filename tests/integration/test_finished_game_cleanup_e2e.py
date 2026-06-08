"""Integration: Redis keys and gauges after game_over disconnect cleanup."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

import tests.test_env  # noqa: F401

from backend.observability.redis_metrics import refresh_redis_gauges
from backend.session.disconnect import _handle_disconnect
from backend.state import close_redis, init_redis, set_game, set_room
from backend.ws_manager import manager
from tests.integration.helpers import flush_redis, redis_client
from tests.observability.prometheus_helpers import parse_gauge
from tests.server.disconnect_helpers import game_state, pvp_room

pytestmark = pytest.mark.integration


async def _seed_finished_room(room_id: str = "cleanup-e2e") -> None:
    await set_room(room_id, pvp_room(room_id=room_id))
    await set_game(room_id, game_state(game_over=True, winner_color="белый", reason="resign"))


@pytest.mark.asyncio
async def test_redis_keys_removed_after_last_disconnect_post_game_over():
    await init_redis()
    try:
        flush_redis()
        room_id = "cleanup-e2e"
        await _seed_finished_room(room_id)
        assert redis_client().exists(f"room:{room_id}") == 1
        assert redis_client().exists(f"game:{room_id}") == 1

        ws = AsyncMock()
        with patch("backend.session.disconnect.manager") as mgr:
            mgr.disconnect = AsyncMock()
            mgr.get_client_id = lambda _rid, _ws: "p-white"
            mgr.get_opponent_ws = lambda _rid, _cid: None
            mgr.connections = {}
            await _handle_disconnect(room_id, ws, is_ai_room=False)

        assert redis_client().exists(f"room:{room_id}") == 0
        assert redis_client().exists(f"game:{room_id}") == 0
    finally:
        manager.connections.clear()
        await close_redis()


@pytest.mark.asyncio
async def test_redis_keys_remain_while_opponent_connected():
    await init_redis()
    try:
        flush_redis()
        room_id = "cleanup-keep"
        await _seed_finished_room(room_id)
        opponent_ws = AsyncMock()

        ws = AsyncMock()
        with patch("backend.session.disconnect.manager") as mgr:
            mgr.disconnect = AsyncMock()
            mgr.get_client_id = lambda _rid, _ws: "p-white"
            mgr.get_opponent_ws = lambda _rid, _cid: opponent_ws
            mgr.connections = {room_id: {"p-black": opponent_ws}}
            await _handle_disconnect(room_id, ws, is_ai_room=False)

        assert redis_client().exists(f"room:{room_id}") == 1
        assert redis_client().exists(f"game:{room_id}") == 1
    finally:
        manager.connections.clear()
        await close_redis()


@pytest.mark.asyncio
async def test_metrics_gauge_drops_after_cleanup():
    await init_redis()
    try:
        flush_redis()
        room_id = "cleanup-gauge"
        await _seed_finished_room(room_id)

        await refresh_redis_gauges()
        body_before = (await _metrics_text()).decode()
        assert parse_gauge(body_before, "shatra_redis_games_active", {"game_over": "true"}) >= 1.0

        ws = AsyncMock()
        with patch("backend.session.disconnect.manager") as mgr:
            mgr.disconnect = AsyncMock()
            mgr.get_client_id = lambda _rid, _ws: "p-white"
            mgr.get_opponent_ws = lambda _rid, _cid: None
            mgr.connections = {}
            await _handle_disconnect(room_id, ws, is_ai_room=False)

        await refresh_redis_gauges()
        body_after = (await _metrics_text()).decode()
        assert parse_gauge(body_after, "shatra_redis_games_active", {"game_over": "true"}) == 0.0
        assert parse_gauge(body_after, "shatra_redis_games_active", {"game_over": "false"}) == 0.0
    finally:
        manager.connections.clear()
        await close_redis()


async def _metrics_text() -> bytes:
    from backend.observability.metrics import metrics_payload

    payload, _ = metrics_payload()
    return payload
