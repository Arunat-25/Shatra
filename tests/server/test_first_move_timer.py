"""Первый ход стороны не уменьшает таймер."""

import time

from backend.game_helpers import color_has_moved
from backend.models import Room
from datetime import datetime


class TestColorHasMoved:
    def test_no_moves(self):
        game = {"move_history": []}
        assert color_has_moved(game, "белый") is False
        assert color_has_moved(game, "черный") is False

    def test_white_only(self):
        game = {"move_history": [{"mover": "белый", "from_pos": 1, "to_pos": 2}]}
        assert color_has_moved(game, "белый") is True
        assert color_has_moved(game, "черный") is False


class TestRoomTimerCorrection:
    def test_first_move_no_elapsed_deduction_on_reconnect(self):
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
        game = {"move_history": [], "mover": "белый"}
        room.correct_timers_after_restart("белый", game)
        assert room.timer_white == 100.0

    def test_after_first_move_deducts_on_reconnect(self):
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
        game = {
            "move_history": [{"mover": "белый"}],
            "mover": "белый",
        }
        room.correct_timers_after_restart("белый", game)
        assert room.timer_white < 100.0
        assert room.timer_black == 200.0
