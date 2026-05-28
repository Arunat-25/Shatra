"""Модель комнаты: таймеры после рестарта сервера."""

import time
from datetime import datetime, timezone

import pytest

from backend.models import Room


def _room(**kwargs) -> Room:
    defaults = dict(
        room_id="test-room",
        type="public",
        created_at=datetime.now(timezone.utc),
        game_started=True,
        time_control=300,
        timer_white=120.0,
        timer_black=90.0,
        last_tick=time.time() - 10,
    )
    defaults.update(kwargs)
    return Room(**defaults)


class TestCorrectTimersAfterRestart:
    def test_only_white_mover_loses_elapsed_time(self):
        room = _room()
        room.correct_timers_after_restart("белый")
        assert room.timer_white == pytest.approx(110.0, abs=0.1)
        assert room.timer_black == 90.0

    def test_only_black_mover_loses_elapsed_time(self):
        room = _room(last_tick=time.time() - 5)
        room.correct_timers_after_restart("черный")
        assert room.timer_white == 120.0
        assert room.timer_black == pytest.approx(85.0, abs=0.1)

    def test_without_mover_nothing_changes(self):
        room = _room()
        room.correct_timers_after_restart(None)
        assert room.timer_white == 120.0
        assert room.timer_black == 90.0

    def test_not_started_game_skips_correction(self):
        room = _room(game_started=False, last_tick=time.time() - 60)
        room.correct_timers_after_restart("белый")
        assert room.timer_white == 120.0
