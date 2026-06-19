"""Timer must stop when the game ends."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.session.ai import _start_ai_game
from backend.timers import game_ticker
from game_engine.models import GameEventResult


@pytest.mark.asyncio
class TestGameTickerGameOver:
    async def test_stops_when_game_over(self):
        room_id = "over-room"
        room = {
            "time_control": 300,
            "timer_white": 100.0,
            "timer_black": 200.0,
        }
        game = {"mover": "белый", "game_over": True, "move_history": []}

        with patch("backend.timers.get_room", new_callable=AsyncMock, return_value=room):
            with patch("backend.timers.get_game", new_callable=AsyncMock, return_value=game):
                with patch("backend.timers.stop_game_timer") as stop:
                    with patch("backend.timers.manager") as mgr:
                        mgr.send_to_room = AsyncMock()
                        await game_ticker(room_id)

        stop.assert_called_once_with(room_id)
        mgr.send_to_room.assert_not_called()


@pytest.mark.asyncio
class TestApplyMoveResultStopsTimer:
    async def test_game_over_calls_stop_game_timer(self, starting_board):
        from backend.game_helpers import apply_move_result

        room_id = "move-over"
        game = {
            "board": dict(starting_board),
            "mover": "белый",
            "game_over": False,
            "move_history": [],
        }
        result = GameEventResult(
            updated_positions=dict(starting_board),
            game_over=True,
            winner_color="белый",
        )

        with patch("backend.game_helpers.set_game", new_callable=AsyncMock):
            with patch("backend.game_helpers.get_room", new_callable=AsyncMock, return_value={"type": "public"}):
                with patch("backend.game_helpers.set_room", new_callable=AsyncMock):
                    with patch("backend.game_helpers.build_move_response", return_value={"game_over": True}):
                        with patch("backend.timers.stop_game_timer") as stop:
                            with patch("backend.game_archive.on_game_finished", new_callable=AsyncMock):
                                await apply_move_result(room_id, game, result, "белый", 1, 2)

        stop.assert_called_once_with(room_id)


@pytest.mark.asyncio
class TestAiReconnectTimer:
    async def test_finished_game_does_not_restart_ticker(self):
        room_id = "ai-done"
        websocket = AsyncMock()
        room_data = {
            "type": "ai",
            "game_started": True,
            "time_control": 300,
            "players": {"c1": "белый"},
            "player_meta": {"c1": {"is_anonymous": True}},
        }
        game = {"mover": "белый", "game_over": True, "board": {}}

        with patch("backend.session.ai.get_game", new_callable=AsyncMock, return_value=game):
            with patch("backend.session.ai.build_game_started_response", return_value={"status": "game_started"}):
                with patch("backend.session.ai.manager") as mgr:
                    mgr.get_client_id.return_value = None
                    mgr.send_to_player = AsyncMock()
                    with patch("backend.session.ai.game_timers", {}):
                        with patch("backend.session.ai.asyncio.create_task") as create_task:
                            await _start_ai_game(room_id, websocket, room_data, "белый")

        create_task.assert_not_called()
