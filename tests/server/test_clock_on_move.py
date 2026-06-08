"""Clock sync on move (Lichess-style)."""

import time
from unittest.mock import AsyncMock, patch

import pytest

from backend.game_helpers import (
    apply_move_result,
    compute_clock_times,
    finalize_clock_on_move,
)
from game_engine.models import GameEventResult


class TestComputeClockTimes:
    def test_active_side_elapsed_subtracted_from_display(self):
        room = {
            "time_control": 300,
            "timer_white": 100.0,
            "timer_black": 200.0,
            "last_tick": time.time() - 5.0,
        }
        game = {"mover": "белый", "move_history": [{"mover": "белый", "from_pos": 1, "to_pos": 2}]}
        times = compute_clock_times(room, game)
        assert times["белый"] == pytest.approx(95.0, abs=0.1)
        assert times["черный"] == 200.0

    def test_first_move_side_does_not_tick_down(self):
        room = {
            "time_control": 300,
            "timer_white": 100.0,
            "timer_black": 200.0,
            "last_tick": time.time() - 5.0,
        }
        game = {"mover": "белый", "move_history": []}
        times = compute_clock_times(room, game)
        assert times["белый"] == 100.0


@pytest.mark.asyncio
class TestFinalizeClockOnMove:
    async def test_turn_pass_deducts_elapsed_and_adds_increment(self, sample_room_data):
        sample_room_data["increment"] = 5
        sample_room_data["timer_white"] = 100.0
        sample_room_data["timer_black"] = 200.0
        sample_room_data["last_tick"] = time.time() - 3.0
        game = {"move_history": [{"mover": "белый", "from_pos": 1, "to_pos": 2}]}

        with patch("backend.game_helpers.get_room", new_callable=AsyncMock, return_value=sample_room_data):
            with patch("backend.game_helpers.set_room", new_callable=AsyncMock) as set_room:
                await finalize_clock_on_move("room1", game, "белый", turn_passed=True)

        assert sample_room_data["timer_white"] == pytest.approx(102.0, abs=0.1)
        assert sample_room_data["timer_black"] == 200.0
        assert sample_room_data["last_tick"] is not None
        set_room.assert_awaited_once()

    async def test_chain_move_does_not_finalize(self, sample_room_data):
        sample_room_data["timer_white"] = 100.0
        sample_room_data["last_tick"] = time.time() - 3.0

        with patch("backend.game_helpers.get_room", new_callable=AsyncMock) as get_room:
            with patch("backend.game_helpers.set_room", new_callable=AsyncMock) as set_room:
                await finalize_clock_on_move("room1", {"move_history": []}, "белый", turn_passed=False)

        get_room.assert_not_called()
        set_room.assert_not_called()


@pytest.mark.asyncio
class TestApplyMoveResultClockPayload:
    async def test_response_includes_time_after_turn_pass(self, starting_board, sample_room_data):
        game = {
            "board": dict(starting_board),
            "mover": "белый",
            "move_history": [{"mover": "белый", "from_pos": 53, "to_pos": 46}],
            "game_over": False,
        }
        result = GameEventResult(
            updated_positions=dict(starting_board),
            movers_color="черный",
            message_code="turn.now",
        )
        sample_room_data["increment"] = 5
        sample_room_data["timer_white"] = 90.0
        sample_room_data["timer_black"] = 300.0
        sample_room_data["last_tick"] = time.time()

        with patch("backend.game_helpers.set_game", new_callable=AsyncMock):
            with patch("backend.game_helpers.get_room", new_callable=AsyncMock, return_value=sample_room_data):
                with patch("backend.game_helpers.set_room", new_callable=AsyncMock):
                    with patch("backend.game_helpers.finalize_clock_on_move", new_callable=AsyncMock):
                        response = await apply_move_result(
                            sample_room_data["room_id"],
                            game,
                            result,
                            "белый",
                            53,
                            46,
                        )

        assert "time" in response
        assert response["time"]["белый"] == pytest.approx(90.0, abs=0.5)
        assert response["time"]["черный"] == 300.0
