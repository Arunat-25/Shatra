"""Matrix tests for Redis cleanup after game_over and related disconnect paths."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.state as state
from backend.session.disconnect import _handle_disconnect, _remove_room_from_redis
from backend.state import drop_room_lock, get_room_lock
from backend.ws_manager import ConnectionManager, _delete_room_after_grace, manager
from tests.server.disconnect_helpers import ai_room, game_state, patch_disconnect_io, pvp_room


@pytest.fixture
def ws():
    mock = AsyncMock()
    mock.send_json = AsyncMock()
    return mock


@pytest.mark.asyncio
class TestRemoveRoomFromRedis:
    async def test_remove_room_from_redis_calls_delete_and_clears_registries(self):
        room_id = "t-remove"
        state.game_timers[room_id] = asyncio.create_task(asyncio.sleep(9999))
        state.disconnect_timers[room_id] = asyncio.create_task(asyncio.sleep(9999))
        get_room_lock(room_id)
        manager.connections[room_id] = {"p1": AsyncMock()}

        with (
            patch("backend.session.disconnect.delete_game", new_callable=AsyncMock) as delete_game,
            patch("backend.session.disconnect.delete_room", new_callable=AsyncMock) as delete_room,
        ):
            await _remove_room_from_redis(room_id)

        await asyncio.sleep(0)
        delete_game.assert_called_once_with(room_id)
        delete_room.assert_called_once_with(room_id)
        assert room_id not in state.game_timers
        assert room_id not in state.disconnect_timers
        assert room_id not in state._room_locks
        assert room_id not in manager.connections


@pytest.mark.asyncio
class TestFinishedGameDisconnectUnit:
    async def test_pvp_game_over_opponent_still_connected(self, ws):
        room = pvp_room(rematch_ready=["p-white", "p-black"])
        opponent_ws = AsyncMock()
        async with patch_disconnect_io(
            room_id="room1",
            room=room,
            game=game_state(game_over=True),
            connections={"room1": {"p-black": opponent_ws}},
            opponent_ws=opponent_ws,
        ) as mocks:
            await _handle_disconnect("room1", ws, is_ai_room=False)

        assert room["rematch_ready"] == []
        mocks["set_room"].assert_called_once()
        opponent_ws.send_json.assert_called_once()
        assert opponent_ws.send_json.call_args[0][0]["status"] == "rematch_cancelled"
        mocks["delete_game"].assert_not_called()
        mocks["delete_room"].assert_not_called()

    async def test_pvp_game_over_last_player_leaves(self, ws):
        async with patch_disconnect_io(
            room_id="room1",
            room=pvp_room(),
            game=game_state(game_over=True),
            connections={},
        ) as mocks:
            await _handle_disconnect("room1", ws, is_ai_room=False)

        mocks["delete_game"].assert_called_once_with("room1")
        mocks["delete_room"].assert_called_once_with("room1")

    async def test_pvp_game_over_two_sequential_disconnects(self, ws):
        room = pvp_room(rematch_ready=["p-white", "p-black"])
        opponent_ws = AsyncMock()
        game = game_state(game_over=True)

        async with patch_disconnect_io(
            room_id="room1",
            room=room,
            game=game,
            connections={"room1": {"p-black": opponent_ws}},
            client_id="p-white",
            opponent_ws=opponent_ws,
        ) as first:
            await _handle_disconnect("room1", ws, is_ai_room=False)
            first["delete_game"].assert_not_called()
            first["delete_room"].assert_not_called()

        async with patch_disconnect_io(
            room_id="room1",
            room=room,
            game=game,
            connections={},
            client_id="p-black",
            opponent_ws=None,
        ) as second:
            await _handle_disconnect("room1", opponent_ws, is_ai_room=False)
            second["delete_game"].assert_called_once_with("room1")
            second["delete_room"].assert_called_once_with("room1")

    async def test_pvp_game_over_clears_rematch_ready(self, ws):
        room = pvp_room(rematch_ready=["p-white", "p-black"])
        async with patch_disconnect_io(
            room_id="room1",
            room=room,
            game=game_state(game_over=True),
            connections={},
        ) as mocks:
            await _handle_disconnect("room1", ws, is_ai_room=False)

        assert room["rematch_ready"] == []
        mocks["delete_game"].assert_called_once_with("room1")
        mocks["delete_room"].assert_called_once_with("room1")

    async def test_pvp_game_over_private_room_same_as_public(self, ws):
        async with patch_disconnect_io(
            room_id="priv1",
            room=pvp_room(room_id="priv1", room_type="private"),
            game=game_state(game_over=True),
            connections={},
        ) as mocks:
            await _handle_disconnect("priv1", ws, is_ai_room=False)

        mocks["delete_game"].assert_called_once_with("priv1")
        mocks["delete_room"].assert_called_once_with("priv1")

    async def test_ai_game_over_empty_room_deletes(self, ws):
        async with patch_disconnect_io(
            room_id="ai-room",
            room=ai_room(),
            game=game_state(game_over=True, winner_color="белый"),
            connections={},
        ) as mocks:
            await _handle_disconnect("ai-room", ws, is_ai_room=True)

        mocks["delete_game"].assert_called_once_with("ai-room")
        mocks["delete_room"].assert_called_once_with("ai-room")

    async def test_ai_game_over_mid_game_no_delete(self, ws):
        async with patch_disconnect_io(
            room_id="ai-room",
            room=ai_room(),
            game=game_state(game_over=False),
            connections={},
        ) as mocks:
            await _handle_disconnect("ai-room", ws, is_ai_room=True)

        mocks["delete_game"].assert_not_called()
        mocks["delete_room"].assert_not_called()

    async def test_active_game_opponent_connected_starts_timer(self, ws):
        opponent_ws = AsyncMock()
        room = pvp_room()
        game = game_state(game_over=False)

        with patch("backend.session.disconnect.manager") as mgr:
            mgr.disconnect = AsyncMock()
            mgr.get_client_id = MagicMock(return_value="p-white")
            mgr.get_opponent_ws = MagicMock(return_value=opponent_ws)
            mgr.connections = {"room1": {"p-black": opponent_ws}}
            with patch("backend.session.disconnect.get_game", new_callable=AsyncMock, return_value=game):
                with patch("backend.session.disconnect.get_room", new_callable=AsyncMock, return_value=room):
                    with patch("backend.session.disconnect.delete_game", new_callable=AsyncMock) as delete_game:
                        with patch("backend.session.disconnect.delete_room", new_callable=AsyncMock) as delete_room:
                            with patch("backend.session.disconnect.asyncio.create_task") as create_task:
                                timer_task = MagicMock()
                                create_task.return_value = timer_task
                                await _handle_disconnect("room1", ws, is_ai_room=False)

        delete_game.assert_not_called()
        delete_room.assert_not_called()
        create_task.assert_called_once()
        assert state.disconnect_timers.get("room1") is timer_task
        state.disconnect_timers.pop("room1", None)

    async def test_active_game_solo_disconnect_deletes(self, ws):
        async with patch_disconnect_io(
            room_id="room1",
            room=pvp_room(),
            game=game_state(game_over=False),
            connections={},
            opponent_ws=None,
        ) as mocks:
            await _handle_disconnect("room1", ws, is_ai_room=False)

        mocks["delete_game"].assert_called_once_with("room1")
        mocks["delete_room"].assert_called_once_with("room1")


@pytest.mark.asyncio
class TestFinishedGameCleanupWithRealDisconnect:
    async def test_manager_disconnect_then_finished_cleanup(self):
        room_id = "real-dc-finished"
        ws = AsyncMock()
        cm = ConnectionManager()
        cm.connections[room_id] = {"p-white": ws}
        room = pvp_room(room_id=room_id, game_started=True)
        game = game_state(game_over=True)

        with patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room):
            with patch("backend.ws_manager.end_session", new_callable=AsyncMock):
                with patch("backend.ws_manager.asyncio.create_task") as create_task:
                    create_task.return_value = MagicMock(done=MagicMock(return_value=False))
                    await cm.disconnect(room_id, ws)

        assert room_id not in cm.connections

        cm.disconnect = AsyncMock()
        cm.get_client_id = MagicMock(return_value="p-white")
        cm.get_opponent_ws = MagicMock(return_value=None)

        with (
            patch("backend.session.disconnect.manager", cm),
            patch("backend.session.disconnect.get_game", new_callable=AsyncMock, return_value=game),
            patch("backend.session.disconnect.get_room", new_callable=AsyncMock, return_value=room),
            patch("backend.session.disconnect.set_room", new_callable=AsyncMock),
            patch("backend.session.disconnect.delete_game", new_callable=AsyncMock) as delete_game,
            patch("backend.session.disconnect.delete_room", new_callable=AsyncMock) as delete_room,
        ):
            await _handle_disconnect(room_id, ws, is_ai_room=False)

        delete_game.assert_called_once_with(room_id)
        delete_room.assert_called_once_with(room_id)
        state.disconnect_timers.pop(room_id, None)

    async def test_grace_task_cancelled_when_immediate_remove(self):
        room_id = "grace-cancel"
        grace_task = asyncio.create_task(asyncio.sleep(9999))
        state.disconnect_timers[room_id] = grace_task

        with (
            patch("backend.session.disconnect.delete_game", new_callable=AsyncMock),
            patch("backend.session.disconnect.delete_room", new_callable=AsyncMock),
        ):
            await _remove_room_from_redis(room_id)

        await asyncio.sleep(0)
        assert grace_task.cancelled() or grace_task.done()
        assert room_id not in state.disconnect_timers

    async def test_finished_grace_fallback_deletes(self):
        room_id = "grace-finished"
        room = pvp_room(room_id=room_id, game_started=True)
        game = game_state(game_over=True)

        with patch("backend.ws_manager.asyncio.sleep", new_callable=AsyncMock):
            with patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room):
                with patch("backend.ws_manager.get_game", new_callable=AsyncMock, return_value=game):
                    with patch("backend.ws_manager.delete_game", new_callable=AsyncMock) as delete_game:
                        with patch("backend.ws_manager.delete_room", new_callable=AsyncMock) as delete_room:
                            manager.connections.pop(room_id, None)
                            await _delete_room_after_grace(room_id, 0.01)

        delete_game.assert_called_once_with(room_id)
        delete_room.assert_called_once_with(room_id)
