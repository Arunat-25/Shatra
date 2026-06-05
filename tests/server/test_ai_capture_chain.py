"""AI must finish long mandatory capture chains (not stop at 5 jumps)."""
import pytest
from unittest.mock import AsyncMock, patch

from backend.board_utils import get_starting_board
from game_engine.game_logic import logic
from game_engine.models import GameEvent


def _board_before_white_capture_chain():
    moves = [
        ("белый", 39, 32), ("черный", 19, 25), ("белый", 40, 39), ("черный", 11, 19),
        ("белый", 44, 38), ("черный", 23, 31), ("белый", 41, 34), ("черный", 22, 23),
        ("белый", 47, 41), ("черный", 21, 22), ("белый", 32, 33), ("черный", 12, 11),
        ("белый", 33, 32), ("черный", 19, 27), ("белый", 32, 33), ("черный", 13, 19),
        ("белый", 33, 21), ("черный", 15, 27), ("белый", 34, 33), ("черный", 14, 21),
        ("белый", 33, 32), ("черный", 27, 26), ("белый", 41, 34), ("черный", 25, 33),
    ]
    board = get_starting_board()
    for color, f, t in moves:
        board = logic.handle_event(
            GameEvent(positions=board, mover_color=color, from_pos=f, to_pos=t),
            position_history={},
        ).updated_positions
    return board


@pytest.mark.asyncio
async def test_handle_ai_move_completes_six_jump_chain():
    from backend.session.ai import handle_ai_move

    chain = [(39, 27), (27, 13), (13, 25), (25, 27), (27, 15), (15, 29)]
    calls = []

    def scripted_move(
        board,
        color,
        depth,
        batyr_caps=None,
        pending=None,
        position_history=None,
    ):
        move = chain[len(calls)]
        calls.append(move)
        return move

    game = {
        "board": _board_before_white_capture_chain(),
        "mover": "белый",
        "move_history": [],
        "position_history": {},
    }
    room = {"type": "ai"}

    with (
        patch("backend.session.ai.asyncio.sleep", new_callable=AsyncMock),
        patch("backend.session.ai.get_ai_move", scripted_move),
        patch("backend.session.ai.set_game", new_callable=AsyncMock),
        patch("backend.session.ai.manager.send_to_room", new_callable=AsyncMock),
        patch("backend.session.ai.apply_move_result", new_callable=AsyncMock) as apply_mock,
    ):
        async def _apply(room_id, g, result, prev_mover, from_cell, to_cell):
            if result.updated_positions:
                g["board"] = result.updated_positions
            if result.movers_color:
                g["mover"] = result.movers_color
            if result.position_for_mandatory_capture:
                g["pending_mandatory_position"] = result.position_for_mandatory_capture
            else:
                g.pop("pending_mandatory_position", None)
            return {}

        apply_mock.side_effect = _apply
        await handle_ai_move("room-chain", game, room_data=room)

    assert calls == chain
    assert game["mover"] == "черный"
    assert "pending_mandatory_position" not in game
