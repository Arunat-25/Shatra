"""Тесты игровой логики для текущего состояния кода."""

from backend.board_utils import get_starting_board
from game_engine.board import Board
from game_engine.endgame import is_game_over
from game_engine.game_logic import logic
from game_engine.hints import get_hints
from game_engine.models import GameEvent
from game_engine.moves import has_mandatory_from_position
from game_engine.validation import get_all_mandatory_captures


def make_empty_board():
    return {i: None for i in range(1, 63)}


def test_handle_event_returns_error_for_invalid_move():
    board = make_empty_board()

    result = logic.handle_event(
        GameEvent(positions=board, mover_color="черный", from_pos=10, to_pos=18)
    )

    assert result.message == "Нет фигуры на выбранной позиции"
    assert result.updated_positions == board


def test_handle_event_returns_hints_for_current_piece():
    board = make_empty_board()
    board[11] = "черная шатра"

    result = logic.handle_event(GameEvent(positions=board, mover_color="черный", position=11))

    assert result.essential_positions
    assert 12 in result.essential_positions
    assert 18 in result.essential_positions


def test_handle_event_returns_empty_hints_for_wrong_color():
    board = make_empty_board()
    board[11] = "черная шатра"

    result = get_hints(board, "белый", 11)

    assert result.essential_positions == []


def test_handle_event_moves_piece_and_switches_turn():
    board = make_empty_board()
    board[11] = "черная шатра"

    result = logic.handle_event(
        GameEvent(positions=board, mover_color="черный", from_pos=11, to_pos=18)
    )

    assert result.updated_positions[11] is None
    assert result.updated_positions[18] == "черная шатра"
    assert result.movers_color == "белый"
    assert "Теперь ходит" in result.message


def test_handle_event_capture_removes_enemy_piece():
    board = make_empty_board()
    board[20] = "белая шатра"
    board[28] = "черная шатра"

    result = logic.handle_event(
        GameEvent(positions=board, mover_color="белый", from_pos=20, to_pos=36)
    )

    assert result.updated_positions[36] == "белая шатра"
    assert result.updated_positions[28] is None
    assert result.captured_positions == [28]
    assert result.movers_color == "черный"


def test_get_all_mandatory_captures_returns_current_capture_options():
    board = make_empty_board()
    board[20] = "белая шатра"
    board[28] = "черная шатра"

    captures = get_all_mandatory_captures(Board(board), "белый")

    assert captures == [(20, 36)]


def test_has_mandatory_from_position_reflects_capture_presence():
    board = make_empty_board()
    board[20] = "белая шатра"
    board[28] = "черная шатра"

    assert has_mandatory_from_position(board, "белый") is True

    empty_board = make_empty_board()
    assert has_mandatory_from_position(empty_board, "белый") is False


def test_is_game_over_detects_single_biy_remaining():
    board = make_empty_board()
    board[10] = "черный бий"

    is_over, winner = is_game_over(Board(board))

    assert is_over is True
    assert winner == "Черный бий победил!"


def test_is_game_over_returns_false_when_both_bies_exist():
    board = make_empty_board()
    board[10] = "черный бий"
    board[53] = "белый бий"

    is_over, winner = is_game_over(Board(board))

    assert is_over is False
    assert winner is None


def test_capture_chain_uses_the_correct_mandatory_piece():
    board = get_starting_board()
    pending = None

    sequence = [
        ("белый", 45, 37),
        ("черный", 23, 29),
        ("белый", 52, 45),
        ("черный", 22, 30),
    ]

    for mover, from_pos, to_pos in sequence:
        result = logic.handle_event(
            GameEvent(
                positions=board,
                mover_color=mover,
                from_pos=from_pos,
                to_pos=to_pos,
                position_for_mandatory_capture=pending,
            )
        )
        assert result.updated_positions is not None
        board = result.updated_positions
        pending = result.position_for_mandatory_capture

    assert pending == 37

    result = logic.handle_event(
        GameEvent(
            positions=board,
            mover_color="белый",
            from_pos=37,
            to_pos=23,
            position_for_mandatory_capture=pending,
        )
    )

    assert result.movers_color == "белый"
    assert result.position_for_mandatory_capture == 23
    assert result.captured_positions == [30]

    board = result.updated_positions
    result = logic.handle_event(
        GameEvent(
            positions=board,
            mover_color="белый",
            from_pos=23,
            to_pos=35,
            position_for_mandatory_capture=result.position_for_mandatory_capture,
        )
    )

    assert result.movers_color == "черный"
    assert result.position_for_mandatory_capture is None
    assert result.captured_positions == [29]
