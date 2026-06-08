"""Timer observability instrumentation tests."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.timers import disconnect_timer, handle_timeout


@pytest.mark.asyncio
class TestTimerMetrics:
    async def test_handle_timeout_records_clock_timeout(self):
        room_id = "timeout-room"
        game = {
            "board": {},
            "game_over": False,
            "move_history": [],
        }

        with (
            patch("backend.timers.get_game", new_callable=AsyncMock, return_value=game),
            patch("backend.timers.get_room", new_callable=AsyncMock, return_value=None),
            patch("backend.timers.set_game", new_callable=AsyncMock),
            patch("backend.timers.manager") as mgr,
            patch("backend.timers.stop_game_timer"),
            patch("backend.game_archive.on_game_finished", new_callable=AsyncMock),
            patch("backend.timers.record_timeout") as record_timeout,
        ):
            mgr.send_to_room = AsyncMock()
            await handle_timeout(room_id, "белый")

        record_timeout.assert_called_once_with("clock")

    async def test_disconnect_timer_records_disconnect_timeout(self):
        room_id = "dc-room"
        game = {"game_over": False, "board": {}}
        room_data = {"players": {"dc": "черный"}}
        ws = AsyncMock()
        ws.send_json = AsyncMock()

        with (
            patch("backend.timers.DISCONNECT_TIMEOUT", 1),
            patch("backend.timers.TICK_INTERVAL_SECONDS", 0),
            patch("backend.timers.get_game", new_callable=AsyncMock, return_value=game),
            patch("backend.timers.get_room", new_callable=AsyncMock, return_value=room_data),
            patch("backend.timers.set_game", new_callable=AsyncMock),
            patch("backend.timers.manager") as mgr,
            patch("backend.timers.stop_game_timer"),
            patch("backend.game_archive.on_game_finished", new_callable=AsyncMock),
            patch("backend.timers.disconnect_timers", {}),
            patch("backend.timers.record_timeout") as record_timeout,
        ):
            mgr.send_to_room = AsyncMock()
            await disconnect_timer(room_id, ws, "dc")

        record_timeout.assert_called_once_with("disconnect")
