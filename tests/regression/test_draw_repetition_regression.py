from backend.board_utils import get_starting_board
from game_engine.game_logic import logic
from game_engine.models import GameEvent


def test_position_history_is_mutated_by_game_logic():
    board = get_starting_board()
    history: dict[str, int] = {}
    res = logic.handle_event(
        GameEvent(positions=board, mover_color="белый", from_pos=44, to_pos=38),
        position_history=history,
    )
    assert res.updated_positions is not None
    # Must be the same dict object and must be populated.
    assert history, "GameLogic must record positions into caller-provided history dict"


def test_draw_by_threefold_repetition_regression_user_line():
    moves = [
        ("белый", 44, 38),
        ("черный", 23, 31),
        ("белый", 40, 32),
        ("черный", 15, 23),
        ("белый", 41, 33),
        ("черный", 19, 25),
        ("белый", 47, 40),
        ("черный", 25, 41),
        ("белый", 49, 33),
        ("черный", 16, 15),
        ("белый", 33, 25),
        ("черный", 20, 19),
        ("белый", 48, 47),
        ("черный", 14, 20),
        ("белый", 43, 44),
        ("черный", 15, 14),
        ("белый", 42, 43),
        ("черный", 23, 30),
        ("белый", 54, 48),
        ("черный", 14, 15),
        ("белый", 55, 41),
        ("черный", 15, 14),
        ("белый", 56, 49),
        ("черный", 14, 15),
        ("белый", 49, 42),
        ("черный", 15, 14),
        ("белый", 57, 49),
        ("черный", 14, 15),
        ("белый", 41, 33),
        ("черный", 15, 14),
        ("белый", 42, 41),
        ("черный", 14, 15),
        ("белый", 41, 42),
        ("черный", 15, 14),
        ("белый", 42, 41),
        ("черный", 14, 15),
        ("белый", 41, 42),
        ("черный", 15, 14),
        ("белый", 42, 41),
        ("черный", 14, 15),
        ("белый", 41, 42),
        ("черный", 15, 14),
        ("белый", 42, 41),
        ("черный", 14, 15),
        ("белый", 41, 42),
        ("черный", 15, 14),
    ]

    board = get_starting_board()
    history: dict[str, int] = {}
    last = None
    for color, f, t in moves:
        last = logic.handle_event(
            GameEvent(positions=board, mover_color=color, from_pos=f, to_pos=t),
            position_history=history,
        )
        board = last.updated_positions
        if last.game_over:
            break

    assert last is not None
    assert last.game_over
    assert last.draw_reason == "draw_repetition"
