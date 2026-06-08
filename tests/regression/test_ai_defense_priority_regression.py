from backend.board_utils import get_starting_board
from backend.ai import get_best_move
from game_engine.game_logic import logic
from game_engine.models import GameEvent


def _board_before_move_48() -> dict:
    moves = [
        ("белый", 44, 38),
        ("черный", 19, 25),
        ("белый", 40, 32),
        ("черный", 23, 31),
        ("белый", 47, 40),
        ("черный", 16, 23),
        ("белый", 48, 47),
        ("черный", 15, 16),
        ("белый", 49, 48),
        ("черный", 16, 15),
        ("белый", 43, 44),
        ("черный", 20, 19),
        ("белый", 41, 33),
        ("черный", 25, 41),
        ("черный", 41, 43),
        ("белый", 44, 42),
        ("черный", 14, 20),
        ("белый", 42, 43),
        ("черный", 18, 25),
        ("белый", 32, 18),
        ("черный", 11, 25),
        ("белый", 40, 33),
        ("черный", 25, 41),
        ("белый", 48, 34),
        ("черный", 12, 11),
        ("белый", 34, 33),
        ("черный", 19, 26),
        ("белый", 33, 19),
        ("черный", 11, 27),
        ("белый", 47, 40),
        ("черный", 27, 35),
        ("белый", 43, 27),
        ("черный", 21, 33),
        ("черный", 33, 47),
        ("белый", 46, 48),
        ("черный", 10, 21),
        ("белый", 48, 47),
        ("черный", 13, 12),
        ("белый", 47, 46),
        ("черный", 21, 13),
        ("белый", 50, 44),
        ("черный", 12, 11),
        ("белый", 54, 32),
        ("черный", 11, 18),
        ("белый", 55, 33),
        ("черный", 13, 14),
        ("белый", 33, 25),
    ]
    board = get_starting_board()
    for color, f, t in moves:
        board = logic.handle_event(
            GameEvent(positions=board, mover_color=color, from_pos=f, to_pos=t),
            position_history={},
        ).updated_positions
    return board


def test_ai_defends_hanging_piece_over_equal_trade_regression():
    """
    Regression from user game: before move 48 black has a hanging shatra on 18.
    AI should prioritize defense (9->11) over a hanging equal-trade move (22->30).
    """
    board = _board_before_move_48()
    assert get_best_move(board, "черный", depth=6) == (9, 11)
