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
        finish = AsyncMock(return_value=True)

        with (
            patch("backend.timers.get_game", new_callable=AsyncMock, return_value=game),
            patch("backend.timers.get_room", new_callable=AsyncMock, return_value=None),
            patch("backend.timers._finish_game_locked", finish),
        ):
            await handle_timeout(room_id, "белый")

        finish.assert_awaited_once()
        assert finish.await_args.kwargs["record_timeout_kind"] == "clock"

    async def test_disconnect_timer_records_disconnect_timeout(self):
        room_id = "dc-room"
        game = {"game_over": False, "board": {}}
        room_data = {"players": {"dc": "черный"}}
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        finish = AsyncMock(return_value=True)

        with (
            patch("backend.timers.DISCONNECT_TIMEOUT", 1),
            patch("backend.timers.TICK_INTERVAL_SECONDS", 0),
            patch("backend.timers.get_game", new_callable=AsyncMock, return_value=game),
            patch("backend.timers.get_room", new_callable=AsyncMock, return_value=room_data),
            patch("backend.timers.finish_game", finish),
            patch("backend.timers.disconnect_timers", {}),
        ):
            await disconnect_timer(room_id, ws, "dc")

        finish.assert_awaited_once()
        assert finish.await_args.kwargs["record_timeout_kind"] == "disconnect"
