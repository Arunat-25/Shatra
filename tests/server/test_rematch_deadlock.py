"""Rematch must not deadlock when invoked under the room lock."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.session.v2.messages import _process_v2_client_message_locked
from backend.state import get_room_lock


@pytest.mark.asyncio
async def test_start_rematch_completes_under_room_lock():
    """Regression: archive_finished_game nested lock hung rematch forever."""
    room_id = "rematch-deadlock"
    game = {
        "board": {45: "белый бий"},
        "mover": "белый",
        "game_over": True,
        "winner_color": "белый",
        "reason": "resign",
        "archived": True,
        "move_history": [],
    }
    room = {
        "type": "public",
        "players": {"p1": "белый", "p2": "черный"},
        "rematch_ready": ["p1"],
        "player_meta": {},
    }
    ws = AsyncMock()

    fresh_game = {"board": {45: "белый бий"}, "mover": "белый", "ply": 0, "move_history": []}

    mgr = MagicMock()
    mgr.connections = {room_id: {"p1": ws, "p2": ws}}
    mgr.connection_proto = MagicMock(return_value=2)
    mgr.send_join_state = AsyncMock()
    mgr.send_to_player = AsyncMock()

    patches = [
        patch("backend.session.v2.messages.get_game", AsyncMock(return_value=game)),
        patch("backend.session.v2.messages.get_room", AsyncMock(return_value=room)),
        patch("backend.ws_control_handlers.get_game", AsyncMock(return_value=game)),
        patch("backend.ws_control_handlers.get_room", AsyncMock(return_value=room)),
        patch("backend.ws_control_handlers.set_room", AsyncMock()),
        patch("backend.ws_control_handlers.manager", mgr),
        patch("backend.session.v2.outbound.manager", mgr),
        patch("backend.session.rematch.manager", mgr),
        patch("backend.session.rematch._archive_finished_game_locked", new_callable=AsyncMock),
        patch("backend.session.rematch.init_game", new_callable=AsyncMock),
        patch("backend.session.rematch.get_game", AsyncMock(return_value=fresh_game)),
        patch("backend.session.rematch.set_room", new_callable=AsyncMock),
        patch("backend.session.rematch.stop_game_timer"),
        patch("backend.session.rematch.mark_game_started"),
    ]

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
        with patches[8] as archive_locked, patches[9], patches[10], patches[11], patches[12], patches[13]:
            lock = get_room_lock(room_id)
            async with lock:
                await asyncio.wait_for(
                    _process_v2_client_message_locked(
                        room_id,
                        "p2",
                        {"v": 2, "t": "request_rematch"},
                        ws,
                        is_ai_room=False,
                    ),
                    timeout=2.0,
                )

    archive_locked.assert_awaited_once()
    assert mgr.send_join_state.await_count == 2


@pytest.mark.asyncio
async def test_archive_finished_game_deadlocks_if_reacquired():
    """Document nested lock behaviour — same lock cannot be taken twice."""
    lock = asyncio.Lock()

    async def inner():
        async with lock:
            return "ok"

    async with lock:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(inner(), timeout=0.05)
