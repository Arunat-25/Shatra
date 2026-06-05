from backend.ai import get_best_move as easy_move
from backend.ai_trained import get_best_move as strong_move, reload_weights
from backend.ai_weights import load_weights
from backend.board_utils import get_starting_board
from game_engine.hints import get_hints
from tests.test_ai import _is_legal_move


def test_strong_move_legal_from_start():
    board = get_starting_board()
    move = strong_move(board, "белый", depth=3)
    assert move is not None
    assert _is_legal_move(board, "белый", move)


def test_load_trained_weights_file():
    w = load_weights()
    assert w.piece_biy >= 10_000
    assert w.chain_capture_bonus >= 8_000


def test_reload_weights_after_change():
    reload_weights()
    board = get_starting_board()
    m1 = strong_move(board, "белый", depth=2)
    assert m1 is not None


def test_easy_and_strong_both_return_hints_legal_moves():
    board = get_starting_board()
    for fn in (easy_move, strong_move):
        move = fn(board, "черный", depth=2)
        assert move is not None
        from_cell, to_cell = move
        hints = get_hints(board, "черный", from_cell)
        assert to_cell in hints.essential_positions
