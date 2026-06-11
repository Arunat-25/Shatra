"""Tests for shared game-over helper."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.game_finish import _finish_game_locked, finish_game


@pytest.mark.asyncio
async def test_finish_game_idempotent_when_already_over():
    game = {"board": {}, "game_over": True, "reason": "resign"}
    with (
        patch("backend.game_finish.get_game", AsyncMock(return_value=game)),
        patch("backend.game_finish.set_game", AsyncMock()) as set_game,
        patch("backend.game_archive.on_game_finished", AsyncMock()),
    ):
        result = await finish_game(
            "room1",
            reason="resign",
            winner_color="черный",
            broadcast={"game_over": True},
        )
    assert result is False
    set_game.assert_not_called()


@pytest.mark.asyncio
async def test_finish_game_locked_ends_active_game():
    game = {"board": {}, "game_over": False}
    with (
        patch("backend.game_finish.get_game", AsyncMock(return_value=game)),
        patch("backend.game_finish.get_room", AsyncMock(return_value={"type": "public"})),
        patch("backend.game_finish.set_game", AsyncMock()) as set_game,
        patch("backend.game_finish.set_room", AsyncMock()),
        patch("backend.timers.stop_game_timer"),
        patch("backend.game_finish.manager") as mgr,
        patch("backend.game_archive._archive_finished_game_locked", AsyncMock()) as archive,
    ):
        mgr.send_to_room = AsyncMock()
        result = await _finish_game_locked(
            "room1",
            reason="resign",
            winner_color="черный",
            broadcast={"game_over": True, "reason": "resign"},
        )
    assert result is True
    assert game["game_over"] is True
    assert game["reason"] == "resign"
    set_game.assert_awaited()
    archive.assert_awaited_once()
