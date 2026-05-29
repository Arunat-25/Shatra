"""game_ticker: тикает только часы стороны на ходе."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from backend.timers import game_ticker, stop_game_timer, game_timers


@pytest.mark.asyncio
class TestGameTicker:
    async def test_decrements_only_white_when_white_to_move(self):
        room_id = "tick-room"
        room = {
            "time_control": 300,
            "timer_white": 100.0,
            "timer_black": 200.0,
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

        assert saved
        assert saved[-1]["timer_white"] == 99.0
        assert saved[-1]["timer_black"] == 200.0

    async def test_stops_when_no_time_control(self):
        room_id = "untimed"
        stop_game_timer(room_id)

        with patch("backend.timers.get_room", new_callable=AsyncMock, return_value={"time_control": None}):
            with patch("backend.timers.stop_game_timer") as stop:
                await game_ticker(room_id)
                stop.assert_called()
