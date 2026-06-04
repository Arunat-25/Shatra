"""Fortress/gate captures for shatra (49→55 white, 14→8 black)."""

from game_engine.board import Board
from game_engine.pieces.shatra import Shatra
from game_engine.validation import get_all_mandatory_captures, validate_move_with_code

from tests.helpers.engine_boards import empty_board


def test_white_49_to_55_forbidden_when_own_shatra_in_fortress():
    board = empty_board()
    board[49] = "белая шатра"
    board[53] = "черная шатра"
    board[55] = None
    board[54] = "белая шатра"

    s = Shatra("белый")
    assert not s.can_capture(board, 49, 55)
    valid, _, code = validate_move_with_code(board, 49, 55, "белый", [])
    assert not valid
    mandatory = get_all_mandatory_captures(Board(board), "белый", [])
    assert (49, 55) not in mandatory


def test_white_49_to_55_forbidden_when_fortress_empty():
    board = empty_board()
    board[49] = "белая шатра"
    board[53] = "черная шатра"
    board[55] = None

    s = Shatra("белый")
    assert not s.can_capture(board, 49, 55)
    valid, _, code = validate_move_with_code(board, 49, 55, "белый", [])
    assert not valid
    assert (49, 55) not in get_all_mandatory_captures(Board(board), "белый", [])


def test_white_49_to_55_forbidden_when_fortress_has_only_biy():
    board = empty_board()
    board[49] = "белая шатра"
    board[53] = "черная шатра"
    board[55] = None
    board[54] = "белый бий"

    s = Shatra("белый")
    assert not s.can_capture(board, 49, 55)
    valid, _, code = validate_move_with_code(board, 49, 55, "белый", [])
    assert not valid
    assert (49, 55) not in get_all_mandatory_captures(Board(board), "белый", [])


def test_black_14_to_8_forbidden_when_own_shatra_in_fortress():
    board = empty_board()
    board[14] = "черная шатра"
    board[10] = "белая шатра"
    board[8] = None
    board[1] = "черная шатра"

    s = Shatra("черный")
    assert not s.can_capture(board, 14, 8)
    valid, _, code = validate_move_with_code(board, 14, 8, "черный", [])
    assert not valid


def test_black_14_to_8_forbidden_when_fortress_empty():
    board = empty_board()
    board[14] = "черная шатра"
    board[10] = "белая шатра"
    board[8] = None

    s = Shatra("черный")
    assert not s.can_capture(board, 14, 8)
    valid, _, code = validate_move_with_code(board, 14, 8, "черный", [])
    assert not valid
    assert (14, 8) not in get_all_mandatory_captures(Board(board), "черный", [])
