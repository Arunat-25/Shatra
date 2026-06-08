"""game_ticker: computed display times and timeout detection."""

import time
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from backend.timers import game_ticker, stop_game_timer, game_timers


@pytest.mark.asyncio
class TestGameTicker:
    async def test_broadcasts_computed_time_without_mutating_stored(self):
        room_id = "tick-room"
        room = {
            "time_control": 300,
            "timer_white": 100.0,
            "timer_black": 200.0,
            "last_tick": time.time() - 5.0,
        }
        game = {"mover": "белый", "move_history": [{"mover": "белый", "from_pos": 1, "to_pos": 2}]}
        saved = []

        async def capture_set(rid, data):
            saved.append(dict(data))

        calls = 0

        async def get_room_tick(rid):
            nonlocal calls
            calls += 1
            if calls > 1:
                return None
            return room

        with patch("backend.timers.get_room", side_effect=get_room_tick):
            with patch("backend.timers.get_game", new_callable=AsyncMock, return_value=game):
                with patch("backend.timers.set_room", side_effect=capture_set):
                    with patch("backend.timers.manager") as mgr:
                        mgr.send_to_room = AsyncMock()
                        with patch(
                            "backend.timers.asyncio.sleep",
                            new_callable=AsyncMock,
                            return_value=None,
                        ):
                            await game_ticker(room_id)

        assert room["timer_white"] == 100.0
        assert not saved
        payload = mgr.send_to_room.call_args_list[0][0][1]
        assert payload["type"] == "timer_tick"
        assert payload["time"]["белый"] == pytest.approx(95.0, abs=0.2)
        assert payload["time"]["черный"] == 200.0

    async def test_timeout_sends_final_tick_with_zero(self):
        room_id = "tick-timeout"
        room = {
            "time_control": 300,
            "timer_white": 0.5,
            "timer_black": 200.0,
            "last_tick": time.time() - 1.0,
        }
        game = {"mover": "белый", "move_history": [{"mover": "белый", "from_pos": 1, "to_pos": 2}], "board": {}}

        with patch("backend.timers.get_room", new_callable=AsyncMock, return_value=room):
            with patch("backend.timers.get_game", new_callable=AsyncMock, return_value=game):
                with patch("backend.timers.set_room", new_callable=AsyncMock):
                    with patch("backend.timers.handle_timeout", new_callable=AsyncMock) as handle_timeout:
                        with patch("backend.timers.manager") as mgr:
                            mgr.send_to_room = AsyncMock()
                            with patch(
                                "backend.timers.asyncio.sleep",
                                new_callable=AsyncMock,
                                return_value=None,
                            ):
                                await game_ticker(room_id)

        handle_timeout.assert_awaited_once_with(room_id, "белый")
        first_payload = mgr.send_to_room.call_args_list[0][0][1]
        assert first_payload["type"] == "timer_tick"
        assert first_payload["time"]["белый"] == 0

    async def test_stops_when_no_time_control(self):
        room_id = "untimed"
        stop_game_timer(room_id)

        with patch("backend.timers.get_room", new_callable=AsyncMock, return_value={"time_control": None}):
            with patch("backend.timers.stop_game_timer") as stop:
                await game_ticker(room_id)
                stop.assert_called()
