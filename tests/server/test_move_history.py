"""История ходов: запись только при реальном изменении доски."""

import pytest
from unittest.mock import AsyncMock, patch

from backend.game_helpers import apply_move_result, save_move_to_history
from backend.board_utils import keys_int_to_str
from game_engine.message_codes import MOVE_WRONG_COLOR, TURN_NOW
from game_engine.models import GameEventResult


class TestSaveMoveToHistory:
    def test_appends_entry_with_desk_snapshot(self, starting_board):
        game = {"board": starting_board, "move_history": []}
        save_move_to_history(game, "белый", 45, 37)
        assert len(game["move_history"]) == 1
        entry = game["move_history"][0]
        assert entry["mover"] == "белый"
        assert entry["from_pos"] == 45
        assert entry["to_pos"] == 37
        assert "desk" in entry


@pytest.mark.asyncio
class TestApplyMoveResult:
    async def test_no_history_when_board_unchanged(self, starting_board):
        game = {
            "board": dict(starting_board),
            "mover": "белый",
            "move_history": [],
            "moves_made": 0,
        }
        result = GameEventResult(
            message_code=MOVE_WRONG_COLOR,
            movers_color="белый",
            updated_positions=dict(starting_board),
        )
        with patch("backend.game_helpers.set_game", new_callable=AsyncMock):
            with patch("backend.game_helpers.get_room", new_callable=AsyncMock, return_value=None):
                response = await apply_move_result(
                    "room1", game, result, "белый", 45, 37
                )
        assert len(game["move_history"]) == 0
        assert response["message_code"] == MOVE_WRONG_COLOR

    async def test_history_when_board_changes(self, starting_board):
        board = dict(starting_board)
        board[45] = None
        board[37] = "белая шатра"
        game = {
            "board": dict(starting_board),
            "mover": "белый",
            "move_history": [],
            "moves_made": 0,
        }
        result = GameEventResult(
            message_code=TURN_NOW,
            movers_color="черный",
            updated_positions=board,
        )
        with patch("backend.game_helpers.set_game", new_callable=AsyncMock):
            with patch("backend.game_helpers.get_room", new_callable=AsyncMock, return_value=None):
                await apply_move_result("room1", game, result, "белый", 45, 37)
        assert len(game["move_history"]) == 1
        assert game["mover"] == "черный"
