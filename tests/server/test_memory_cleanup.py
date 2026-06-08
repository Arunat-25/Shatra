"""
Регрессии утечек памяти: in-memory registries и asyncio-задачи.

Проверяем, что после disconnect / удаления комнаты / game over
не остаются «висящие» записи в game_timers, disconnect_timers,
_room_locks и manager.connections.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend import state
from backend.session import _handle_disconnect
from backend.session.rematch import _start_rematch
from backend.timers import stop_game_timer, disconnect_timer, handle_timeout
from backend.ws_manager import ConnectionManager, _delete_room_after_grace, manager
from backend.state import get_room_lock, drop_room_lock


def _cancel_task(task) -> None:
    if task is None or not hasattr(task, "cancel"):
        return
    if task.done():
        return
    try:
        task.cancel()
    except RuntimeError:
        pass


async def _cancel_and_clear_registries() -> None:
    for task in list(state.game_timers.values()):
        _cancel_task(task)
    for task in list(state.disconnect_timers.values()):
        _cancel_task(task)
    await asyncio.sleep(0)
    state.game_timers.clear()
    state.disconnect_timers.clear()
    state._room_locks.clear()
    manager.connections.clear()


def _clear_registries_only() -> None:
    state.game_timers.clear()
    state.disconnect_timers.clear()
    state._room_locks.clear()
    manager.connections.clear()


def assert_registries_empty(*, allow_locks: bool = False) -> None:
    assert state.game_timers == {}, f"game_timers leak: {state.game_timers}"
    assert state.disconnect_timers == {}, f"disconnect_timers leak: {state.disconnect_timers}"
    assert manager.connections == {}, f"connections leak: {manager.connections}"
    if not allow_locks:
        assert state._room_locks == {}, f"room_locks leak: {state._room_locks}"


@pytest.fixture(autouse=True)
async def isolated_registries():
    _clear_registries_only()
    yield
    await _cancel_and_clear_registries()


@pytest.mark.asyncio
class TestGameTimerCleanup:
    async def test_stop_game_timer_cancels_and_removes(self):
        room_id = "t-stop"

        async def sleeper():
            await asyncio.sleep(9999)

        task = asyncio.create_task(sleeper())
        state.game_timers[room_id] = task

        stop_game_timer(room_id)
        await asyncio.sleep(0)

        assert room_id not in state.game_timers
        assert task.cancelled() or task.done()

    async def test_handle_timeout_stops_ticker(self):
        room_id = "t-timeout"
        state.game_timers[room_id] = asyncio.create_task(asyncio.sleep(9999))

        with (
            patch("backend.timers.get_game", new_callable=AsyncMock, return_value={"board": {}}),
            patch("backend.timers.get_room", new_callable=AsyncMock, return_value=None),
            patch("backend.timers.set_game", new_callable=AsyncMock),
        ):
            with patch("backend.timers.manager") as mgr:
                mgr.send_to_room = AsyncMock()
                await handle_timeout(room_id, "белый")

        assert room_id not in state.game_timers

    async def test_player2_join_replaces_old_ticker_without_duplicate(self):
        from backend.ws_manager import handle_player2_join

        room_id = "t-join"
        old_task = asyncio.create_task(asyncio.sleep(9999))
        state.game_timers[room_id] = old_task

        room = {
            "room_id": room_id,
            "type": "public",
            "game_started": False,
            "players": {"a": "белый", "b": "черный"},
            "time_control": 60,
        }

        with patch("backend.ws_manager.init_game", new_callable=AsyncMock):
            with patch("backend.ws_manager.get_game", new_callable=AsyncMock, return_value={"board": {}, "mover": "белый"}):
                with patch("backend.ws_manager.set_room", new_callable=AsyncMock):
                    with patch("backend.ws_manager.manager") as mgr:
                        mgr.get_ws = MagicMock(return_value=None)
                        mgr.send_to_player = AsyncMock()
                        with patch("backend.ws_manager.asyncio.create_task") as create_task:
                            new_task = MagicMock(done=MagicMock(return_value=False))
                            create_task.return_value = new_task
                            await handle_player2_join(room_id, room)

        await asyncio.sleep(0)
        assert old_task.cancelled() or old_task.done()
        assert state.game_timers.get(room_id) is new_task
        stop_game_timer(room_id)


@pytest.mark.asyncio
class TestDisconnectTimerCleanup:
    async def test_disconnect_timer_removes_itself_after_finish(self):
        room_id = "t-dc-finish"
        ws = AsyncMock()

        with patch("backend.timers.asyncio.sleep", new_callable=AsyncMock):
            with patch("backend.timers.DISCONNECT_TIMEOUT", 1):
                with patch("backend.timers.get_game", new_callable=AsyncMock, return_value={"game_over": True}):
                    with patch("backend.timers.manager") as mgr:
                        mgr.send_to_room = AsyncMock()
                        task = asyncio.create_task(disconnect_timer(room_id, ws, "p1"))
                        state.disconnect_timers[room_id] = task
                        await task

        assert room_id not in state.disconnect_timers

    async def test_reconnect_cancels_grace_delete_task(self):
        cm = ConnectionManager()
        room_id = "t-grace-reconnect"
        room = {
            "room_id": room_id,
            "type": "public",
            "game_started": False,
            "players": {"creator": "белый"},
            "creator_client_id": "creator",
            "creator_color_preference": "белый",
        }
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.close = AsyncMock()

        grace_task = asyncio.create_task(asyncio.sleep(9999))
        state.disconnect_timers[room_id] = grace_task

        with patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room):
            with patch("backend.ws_manager.set_room", new_callable=AsyncMock):
                with patch.object(cm, "connections", {room_id: {}}):
                    ok = await cm.connect(room_id, ws2, "creator")

        await asyncio.sleep(0)
        assert ok is True
        assert room_id not in state.disconnect_timers
        assert grace_task.cancelled() or grace_task.done()

    async def test_double_in_game_disconnect_cancels_prior_timer(self):
        room_id = "t-double-dc"
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        game = {"board": {}, "game_over": False, "mover": "белый"}
        room = {"players": {"a": "белый", "b": "черный"}, "type": "public"}

        first = asyncio.create_task(asyncio.sleep(9999))
        state.disconnect_timers[room_id] = first

        opponent_ws = AsyncMock()
        with patch("backend.session.disconnect.manager") as mgr:
            mgr.get_client_id = MagicMock(return_value="a")
            mgr.disconnect = AsyncMock()
            mgr.get_opponent_ws = MagicMock(return_value=opponent_ws)
            with patch("backend.session.disconnect.get_game", new_callable=AsyncMock, return_value=game):
                with patch("backend.session.disconnect.get_room", new_callable=AsyncMock, return_value=room):
                    with patch("backend.session.disconnect.asyncio.create_task") as create_task:
                        second = MagicMock()
                        create_task.return_value = second
                        await _handle_disconnect(room_id, ws, is_ai_room=False)

        await asyncio.sleep(0)
        assert first.cancelled() or first.done()
        assert state.disconnect_timers.get(room_id) is second

        state.disconnect_timers.pop(room_id, None)


@pytest.mark.asyncio
class TestRoomLockCleanup:
    async def test_drop_room_lock_when_idle(self):
        room_id = "t-lock"
        get_room_lock(room_id)
        assert room_id in state._room_locks

        drop_room_lock(room_id)
        assert room_id not in state._room_locks

    async def test_drop_room_lock_skips_when_held(self):
        room_id = "t-lock-held"
        lock = get_room_lock(room_id)
        await lock.acquire()
        try:
            drop_room_lock(room_id)
            assert room_id in state._room_locks
        finally:
            lock.release()
            drop_room_lock(room_id)
        assert room_id not in state._room_locks

    async def test_grace_delete_drops_lock(self):
        room_id = "t-grace-lock"
        get_room_lock(room_id)
        room = {"room_id": room_id, "game_started": False, "type": "public"}

        with patch("backend.ws_manager.asyncio.sleep", new_callable=AsyncMock):
            with patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room):
                with patch("backend.ws_manager.get_game", new_callable=AsyncMock, return_value=None):
                    with patch("backend.ws_manager.delete_game", new_callable=AsyncMock):
                        with patch("backend.ws_manager.delete_room", new_callable=AsyncMock):
                            with patch.object(manager, "connections", {}):
                                await _delete_room_after_grace(room_id, 0.01)

        assert room_id not in state._room_locks


@pytest.mark.asyncio
class TestConnectionRegistryCleanup:
    async def test_destroy_room_clears_everything(self):
        cm = ConnectionManager()
        room_id = "t-destroy"
        ws = AsyncMock()

        cm.connections[room_id] = {"p1": ws}
        state.game_timers[room_id] = asyncio.create_task(asyncio.sleep(9999))
        state.disconnect_timers[room_id] = asyncio.create_task(asyncio.sleep(9999))
        get_room_lock(room_id)

        with patch("backend.ws_manager.delete_game", new_callable=AsyncMock):
            with patch("backend.ws_manager.delete_room", new_callable=AsyncMock):
                await cm._destroy_room(room_id)

        await asyncio.sleep(0)
        assert_registries_empty()

    async def test_disconnect_empty_waiting_room_schedules_then_cleans_on_grace(self):
        cm = ConnectionManager()
        room_id = "t-empty-wait"
        ws = AsyncMock()
        room = {"room_id": room_id, "type": "public", "game_started": False}

        cm.connections[room_id] = {"solo": ws}

        with patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room):
            with patch("backend.ws_manager.asyncio.create_task") as create_task:
                mock_task = MagicMock(done=MagicMock(return_value=False))
                create_task.return_value = mock_task
                await cm.disconnect(room_id, ws)

        assert room_id not in cm.connections
        assert state.disconnect_timers.get(room_id) is mock_task

        state.disconnect_timers.pop(room_id, None)

    async def test_handle_disconnect_delete_path_cleans_timers_and_lock(self):
        room_id = "t-del-path"
        ws = AsyncMock()
        state.game_timers[room_id] = asyncio.create_task(asyncio.sleep(9999))
        state.disconnect_timers[room_id] = asyncio.create_task(asyncio.sleep(9999))
        get_room_lock(room_id)
        game = {"board": {}, "game_over": False, "mover": "белый"}

        with patch("backend.session.disconnect.manager") as mgr:
            mgr.get_client_id = MagicMock(return_value="solo")
            mgr.disconnect = AsyncMock()
            mgr.get_opponent_ws = MagicMock(return_value=None)
            with patch("backend.session.disconnect.get_game", new_callable=AsyncMock, return_value=game):
                with patch("backend.session.disconnect.get_room", new_callable=AsyncMock, return_value={"players": {}}):
                    with patch("backend.session.disconnect.delete_game", new_callable=AsyncMock) as delete_game:
                        with patch("backend.session.disconnect.delete_room", new_callable=AsyncMock) as delete_room:
                            await _handle_disconnect(room_id, ws, is_ai_room=False)

        await asyncio.sleep(0)
        assert room_id not in state.game_timers
        assert room_id not in state.disconnect_timers
        assert room_id not in state._room_locks
        delete_game.assert_called_once()
        delete_room.assert_called_once()


@pytest.mark.asyncio
class TestRematchAndControlCleanup:
    async def test_start_rematch_stops_old_game_timer(self):
        room_id = "t-rematch"
        old = asyncio.create_task(asyncio.sleep(9999))
        state.game_timers[room_id] = old
        room = {
            "room_id": room_id,
            "players": {"a": "белый", "b": "черный"},
            "time_control": 60,
        }

        with patch("backend.session.rematch.init_game", new_callable=AsyncMock):
            with patch("backend.session.rematch.get_game", new_callable=AsyncMock, return_value={"board": {}, "mover": "белый"}):
                with patch("backend.session.rematch.set_room", new_callable=AsyncMock):
                    with patch("backend.session.rematch.manager") as mgr:
                        mgr.connections = {room_id: {}}
                        mgr.send_to_player = AsyncMock()
                        with patch("backend.session.rematch.asyncio.create_task") as create_task:
                            new_task = MagicMock()
                            create_task.return_value = new_task
                            await _start_rematch(room_id, room)

        await asyncio.sleep(0)
        assert old.cancelled() or old.done()
        stop_game_timer(room_id)

    async def test_resign_stops_game_timer(self):
        from backend.ws_control_handlers import handle_resign

        room_id = "t-resign"
        ws = AsyncMock()
        state.game_timers[room_id] = asyncio.create_task(asyncio.sleep(9999))
        game = {"board": {}, "game_over": False, "mover": "белый"}
        room = {"players": {"p-white": "белый", "p-black": "черный"}}

        with patch("backend.ws_control_handlers.get_game", new_callable=AsyncMock, return_value=game):
            with patch("backend.ws_control_handlers.get_room", new_callable=AsyncMock, return_value=room):
                with patch("backend.ws_control_handlers.set_game", new_callable=AsyncMock):
                    with patch("backend.ws_control_handlers.set_room", new_callable=AsyncMock):
                        with patch("backend.ws_control_handlers.manager") as mgr:
                            mgr.send_to_room = AsyncMock()
                            await handle_resign(room_id, "p-white", ws, is_ai_room=False)

        assert room_id not in state.game_timers


@pytest.mark.asyncio
class TestManyRoomsNoLeak:
    async def test_create_and_destroy_many_rooms_leaves_registries_empty(self):
        cm = ConnectionManager()

        with patch("backend.ws_manager.delete_game", new_callable=AsyncMock):
            with patch("backend.ws_manager.delete_room", new_callable=AsyncMock):
                for i in range(12):
                    room_id = f"bulk-{i}"
                    ws = AsyncMock()
                    cm.connections[room_id] = {f"p{i}": ws}
                    state.game_timers[room_id] = asyncio.create_task(asyncio.sleep(9999))
                    get_room_lock(room_id)
                    await cm._destroy_room(room_id)

        await asyncio.sleep(0)
        assert_registries_empty()

    async def test_process_move_acquires_lock_then_releases(self):
        """Лок комнаты не должен оставаться захваченным после хода."""
        from backend.session import process_client_message
        from backend.board_utils import keys_int_to_str, get_starting_board

        room_id = "t-lock-move"
        board = get_starting_board()
        game = {
            "board": board,
            "mover": "белый",
            "game_over": False,
            "move_history": [],
            "pending_batyr_captures": [],
            "position_history": {},
            "moves_with_two_biys": 0,
        }
        room = {
            "room_id": room_id,
            "type": "public",
            "game_started": True,
            "players": {"p-white": "белый", "p-black": "черный"},
        }
        ws = AsyncMock()

        async def get_game(_):
            return dict(game)

        async def get_room(_):
            return dict(room)

        async def set_game(_, g):
            game.clear()
            game.update(g)

        manager.connections[room_id] = {"p-white": ws, "p-black": AsyncMock()}

        with patch("backend.session.messages.get_game", side_effect=get_game):
            with patch("backend.session.messages.get_room", side_effect=get_room):
                with patch("backend.game_helpers.set_game", side_effect=set_game):
                    with patch("backend.session.messages.manager.send_to_room", new_callable=AsyncMock):
                            await process_client_message(
                                room_id,
                                "p-black",
                                {
                                    "board": keys_int_to_str(board),
                                    "movers_color": "черный",
                                    "move_from": "position12",
                                    "move_to": "position20",
                                },
                                ws,
                                is_ai_room=False,
                            )

        lock = state._room_locks.get(room_id)
        if lock is not None:
            assert not lock.locked(), "room lock still held after message processing"

        manager.connections.pop(room_id, None)
        state._room_locks.pop(room_id, None)


@pytest.mark.asyncio
class TestOrphanedStateCleanup:
    async def test_disconnect_without_game_stops_orphaned_timers(self):
        room_id = "t-no-game"
        ws = AsyncMock()
        state.game_timers[room_id] = asyncio.create_task(asyncio.sleep(9999))
        state.disconnect_timers[room_id] = asyncio.create_task(asyncio.sleep(9999))
        get_room_lock(room_id)

        with patch("backend.session.disconnect.manager") as mgr:
            mgr.get_client_id = MagicMock(return_value="solo")
            mgr.disconnect = AsyncMock()
            mgr.connections = {}
            with patch("backend.session.disconnect.get_game", new_callable=AsyncMock, return_value=None):
                with patch("backend.session.disconnect.get_room", new_callable=AsyncMock, return_value=None):
                    await _handle_disconnect(room_id, ws, is_ai_room=False)

        await asyncio.sleep(0)
        assert room_id not in state.game_timers
        assert room_id not in state.disconnect_timers
        assert room_id not in state._room_locks
