"""Таймеры: таймаут, отключение, коррекция после паузы сервера."""

import time
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.models import Room
from backend.timers import handle_timeout, disconnect_timer, _opposite_color
from datetime import datetime


class TestRoomTimerCorrection:
    def test_only_active_side_loses_elapsed_on_restart(self):
        room = Room(
            room_id="r1",
            type="public",
            created_at=datetime.utcnow(),
            game_started=True,
            time_control=300,
            timer_white=100.0,
            timer_black=200.0,
            last_tick=time.time() - 10.0,
        )
        room.correct_timers_after_restart("белый")
        assert room.timer_white < 100.0
        assert room.timer_black == 200.0

    def test_black_on_move_only_black_clock_adjusted(self):
        room = Room(
            room_id="r1",
            type="public",
            created_at=datetime.utcnow(),
            game_started=True,
            time_control=300,
            timer_white=100.0,
            timer_black=50.0,
            last_tick=time.time() - 5.0,
        )
        room.correct_timers_after_restart("черный")
        assert room.timer_white == 100.0
        assert room.timer_black < 50.0

    def test_no_correction_without_mover_or_last_tick(self):
        room = Room(
            room_id="r1",
            type="public",
            created_at=datetime.utcnow(),
            game_started=True,
            time_control=300,
            timer_white=100.0,
            timer_black=200.0,
            last_tick=None,
        )
        room.correct_timers_after_restart("белый")
        assert room.timer_white == 100.0
        assert room.timer_black == 200.0

    def test_elapsed_cannot_go_negative(self):
        room = Room(
            room_id="r1",
            type="public",
            created_at=datetime.utcnow(),
            game_started=True,
            time_control=300,
            timer_white=2.0,
            timer_black=200.0,
            last_tick=time.time() - 999.0,
        )
        room.correct_timers_after_restart("белый")
        assert room.timer_white == 0.0


@pytest.mark.asyncio
class TestHandleTimeout:
    async def test_white_timeout_black_wins(self, starting_board):
        game = {"board": starting_board, "mover": "белый", "game_over": False}
        room_id = "timeout-room"

        with patch("backend.timers.get_game", new_callable=AsyncMock, return_value=game):
            with patch("backend.timers.set_game", new_callable=AsyncMock) as set_game:
                with patch("backend.timers.manager") as mgr:
                    mgr.send_to_room = AsyncMock()
                    with patch("backend.timers.stop_game_timer") as stop:
                        await handle_timeout(room_id, "белый")

        assert game["game_over"] is True
        set_game.assert_called_once()
        payload = mgr.send_to_room.call_args[0][1]
        assert payload["winner_color"] == "черный"
        assert payload["reason"] == "timeout"
        stop.assert_called_once()


@pytest.mark.asyncio
class TestDisconnectTimerWinner:
    async def test_disconnected_black_white_wins_fast(self, starting_board):
        """Сокращённый цикл: не ждём 30с, проверяем финальную логику через patch sleep."""
        room_id = "dc-room"
        game = {"board": starting_board, "game_over": False}
        room = {"players": {"dc": "черный", "stay": "белый"}}
        remaining_ws = AsyncMock()

        async def instant_sleep(_):
            return None

        with patch("backend.timers.asyncio.sleep", side_effect=instant_sleep):
            with patch("backend.timers.DISCONNECT_TIMEOUT", 1):
                with patch("backend.timers.get_game", new_callable=AsyncMock, return_value=game):
                    with patch("backend.timers.get_room", new_callable=AsyncMock, return_value=room):
                        with patch("backend.timers.set_game", new_callable=AsyncMock):
                            with patch("backend.timers.manager") as mgr:
                                mgr.send_to_room = AsyncMock()
                                with patch("backend.timers.stop_game_timer"):
                                    await disconnect_timer(room_id, remaining_ws, "dc")

        assert game["game_over"] is True
        assert game["winner"] == "белый"
        assert game["reason"] == "opponent_disconnected"

    async def test_no_game_over_if_already_finished(self, starting_board):
        game = {"board": starting_board, "game_over": True, "winner": "белый"}
        remaining_ws = AsyncMock()

        with patch("backend.timers.asyncio.sleep", side_effect=lambda _: None):
            with patch("backend.timers.DISCONNECT_TIMEOUT", 1):
                with patch("backend.timers.get_game", new_callable=AsyncMock, return_value=game):
                    with patch("backend.timers.set_game", new_callable=AsyncMock) as set_game:
                        with patch("backend.timers.manager") as mgr:
                            mgr.send_to_room = AsyncMock()
                            await disconnect_timer("r", remaining_ws, "x")

        set_game.assert_not_called()
        mgr.send_to_room.assert_not_called()


class TestOppositeColor:
    @pytest.mark.parametrize("c,expected", [
        ("белый", "черный"),
        ("черный", "белый"),
    ])
    def test_swap(self, c, expected):
        assert _opposite_color(c) == expected
