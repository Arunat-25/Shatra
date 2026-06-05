"""Mandatory capture fork: prefer longer own chain (20-34 over 21-33)."""
from backend.ai import (
    SearchState,
    _pick_best_mandatory_capture_fork,
    _simulate_capture_sequence,
)
from backend.ai_trained import get_best_move as strong_move
from backend.board_utils import get_starting_board
from game_engine.game_logic import logic
from game_engine.models import GameEvent


def _board_before_move_35():
    moves = [
        ("белый", 45, 37), ("черный", 22, 29), ("белый", 51, 45), ("черный", 29, 30),
        ("белый", 37, 38), ("черный", 30, 31), ("белый", 43, 37), ("черный", 31, 43),
        ("белый", 49, 37), ("черный", 16, 22), ("белый", 37, 31), ("черный", 18, 25),
        ("белый", 40, 32), ("черный", 12, 18), ("белый", 41, 40), ("черный", 9, 12),
        ("белый", 42, 41), ("черный", 8, 26), ("белый", 41, 33), ("черный", 25, 41),
        ("белый", 48, 34), ("черный", 26, 42), ("белый", 50, 34), ("черный", 19, 26),
        ("белый", 34, 33), ("черный", 7, 19), ("белый", 33, 25), ("черный", 19, 27),
        ("белый", 39, 33), ("черный", 27, 39), ("черный", 39, 41), ("белый", 47, 35),
        ("черный", 10, 19), ("белый", 25, 27),
    ]
    board = get_starting_board()
    for color, f, t in moves:
        board = logic.handle_event(
            GameEvent(positions=board, mover_color=color, from_pos=f, to_pos=t),
            position_history={},
        ).updated_positions
    return board


def test_simulate_20_34_chain_longer_than_21_33():
    board = _board_before_move_35()
    val20, chain20 = _simulate_capture_sequence(board, "черный", (20, 34), max_depth=16)
    val21, chain21 = _simulate_capture_sequence(board, "черный", (21, 33), max_depth=16)
    assert len(chain20) > len(chain21)
    assert val20 > val21


def test_fork_picker_prefers_20_34():
    board = _board_before_move_35()
    state = SearchState(board, "черный")
    assert _pick_best_mandatory_capture_fork(state, "черный") == (20, 34)


def test_strong_ai_plays_20_34_not_21_33():
    board = _board_before_move_35()
    assert strong_move(board, "черный", depth=5) == (20, 34)
