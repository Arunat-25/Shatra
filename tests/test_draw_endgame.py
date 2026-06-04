"""Draw detection: repetition and two-biy rule."""

from game_engine.board import Board
from game_engine.endgame import add_to_history, is_game_over
from game_engine.message_codes import DRAW_REPETITION, DRAW_TWO_BIYS
from game_engine.moves import process_move

from tests.helpers.engine_boards import empty_board


def test_repetition_draw_after_third_occurrence():
    board = empty_board()
    board[10] = "черный бий"
    board[53] = "белый бий"
    history: dict = {}
    for _ in range(3):
        add_to_history(history, board)

    over, winner, reason = is_game_over(Board(board), history)
    assert over is True
    assert winner is None
    assert reason == DRAW_REPETITION


def test_two_biys_draw_after_three_moves_counter():
    board = empty_board()
    board[10] = "черный бий"
    board[53] = "белый бий"

    over, winner, reason = is_game_over(Board(board), {}, moves_with_two_biys=3)
    assert over is True
    assert winner is None
    assert reason == DRAW_TWO_BIYS


def test_two_biys_not_draw_before_third_move():
    board = empty_board()
    board[10] = "черный бий"
    board[53] = "белый бий"

    over, _, reason = is_game_over(Board(board), {}, moves_with_two_biys=2)
    assert over is False
    assert reason is None


def test_three_quiet_moves_with_two_biys_triggers_draw():
    board = empty_board()
    board[10] = "черный бий"
    board[53] = "белый бий"
    history: dict = {}
    moves_with_two_biys = 0
    sequence = [
        ("черный", 10, 11),
        ("белый", 53, 54),
        ("черный", 11, 12),
    ]
    for color, from_pos, to_pos in sequence:
        result = process_move(
            board,
            color,
            from_pos,
            to_pos,
            position_history=history,
            moves_with_two_biys=moves_with_two_biys,
        )
        assert result.updated_positions is not None
        board = result.updated_positions
        moves_with_two_biys += 1

    over, winner, reason = is_game_over(Board(board), history, moves_with_two_biys)
    assert over is True
    assert winner is None
    assert reason == DRAW_TWO_BIYS
