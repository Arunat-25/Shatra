"""Shared fixtures and helpers for disconnect / Redis cleanup tests."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from backend.board_utils import get_starting_board


def pvp_room(*, room_id: str = "room1", room_type: str = "public", **extra) -> dict:
    room = {
        "room_id": room_id,
        "type": room_type,
        "game_started": True,
        "players": {"p-white": "белый", "p-black": "черный"},
        "time_control": None,
        "rematch_ready": [],
    }
    room.update(extra)
    return room


def ai_room(*, room_id: str = "ai-room", **extra) -> dict:
    room = {
        "room_id": room_id,
        "type": "ai",
        "game_started": True,
        "players": {"human-1": "белый"},
        "time_control": None,
        "rematch_ready": [],
    }
    room.update(extra)
    return room


def game_state(**extra) -> dict:
    state = {
        "board": get_starting_board(),
        "mover": "белый",
        "game_over": False,
        "move_history": [],
        "pending_batyr_captures": [],
        "position_history": {},
        "moves_with_two_biys": 0,
    }
    state.update(extra)
    return state


@asynccontextmanager
async def patch_disconnect_io(
    *,
    room_id: str,
    room: dict,
    game: dict | None,
    connections: dict | None = None,
    client_id: str = "p-white",
    opponent_ws=None,
):
    """Patch Redis I/O and manager for _handle_disconnect tests."""
    mgr = MagicMock()
    mgr.disconnect = AsyncMock()
    mgr.get_client_id = MagicMock(return_value=client_id)
    mgr.get_opponent_ws = MagicMock(return_value=opponent_ws)
    mgr.connections = connections if connections is not None else {}

    with (
        patch("backend.session.disconnect.manager", mgr),
        patch("backend.session.disconnect.get_game", new_callable=AsyncMock, return_value=game),
        patch("backend.session.disconnect.get_room", new_callable=AsyncMock, return_value=room),
        patch("backend.session.disconnect.set_room", new_callable=AsyncMock) as set_room,
        patch("backend.session.disconnect.delete_game", new_callable=AsyncMock) as delete_game,
        patch("backend.session.disconnect.delete_room", new_callable=AsyncMock) as delete_room,
    ):
        yield {
            "mgr": mgr,
            "set_room": set_room,
            "delete_game": delete_game,
            "delete_room": delete_room,
            "room_id": room_id,
        }
