"""Full PvP rematch flow under room lock (integration)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.session.v2.messages import _process_v2_client_message_locked
from backend.state import get_room_lock


@pytest.mark.asyncio
async def test_second_rematch_request_starts_game_for_both():
    room_id = "rematch-flow"
    finished = {
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
    fresh = {"board": {45: "белый бий"}, "mover": "белый", "ply": 0, "move_history": []}
    ws = AsyncMock()

    mgr = MagicMock()
    mgr.connections = {room_id: {"p1": ws, "p2": ws}}
    mgr.connection_proto = MagicMock(return_value=2)
    mgr.send_join_state = AsyncMock()
    mgr.send_to_player = AsyncMock()

    patches = [
        patch("backend.session.v2.messages.get_game", AsyncMock(return_value=finished)),
        patch("backend.session.v2.messages.get_room", AsyncMock(return_value=room)),
        patch("backend.ws_control_handlers.get_game", AsyncMock(return_value=finished)),
        patch("backend.ws_control_handlers.get_room", AsyncMock(return_value=room)),
        patch("backend.ws_control_handlers.set_room", new_callable=AsyncMock),
        patch("backend.ws_control_handlers.manager", mgr),
        patch("backend.session.v2.outbound.manager", mgr),
        patch("backend.session.rematch.manager", mgr),
        patch("backend.session.rematch._archive_finished_game_locked", new_callable=AsyncMock),
        patch("backend.session.rematch.init_game", new_callable=AsyncMock),
        patch("backend.session.rematch.get_game", AsyncMock(return_value=fresh)),
        patch("backend.session.rematch.set_room", new_callable=AsyncMock),
        patch("backend.session.rematch.stop_game_timer"),
        patch("backend.session.rematch.mark_game_started"),
    ]

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
        with patches[8], patches[9], patches[10], patches[11], patches[12]:
            lock = get_room_lock(room_id)
            async with lock:
                await _process_v2_client_message_locked(
                    room_id,
                    "p2",
                    {"v": 2, "t": "request_rematch"},
                    ws,
                    is_ai_room=False,
                )

    assert mgr.send_join_state.await_count == 2
