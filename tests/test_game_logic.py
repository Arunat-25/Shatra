"""Тесты игровой логики для текущего состояния кода."""

from backend.board_utils import get_starting_board
from game_engine.board import Board
from game_engine.endgame import is_game_over
from game_engine.message_codes import MOVE_NO_PIECE, TURN_NOW
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

    assert result.message_code == MOVE_NO_PIECE
    assert result.updated_positions is None


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
    assert result.message_code == TURN_NOW


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

    is_over, winner_color, draw_reason = is_game_over(Board(board))

    assert is_over is True
    assert winner_color == "черный"
    assert draw_reason is None


def test_is_game_over_returns_false_when_both_bies_exist():
    board = make_empty_board()
    board[10] = "черный бий"
    board[53] = "белый бий"

    is_over, winner_color, draw_reason = is_game_over(Board(board))

    assert is_over is False
    assert winner_color is None
    assert draw_reason is None


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


def _replay_moves(moves, board=None, pending=None, batyr_caps=None):
    """Проигрывает ходы, возвращает (board, pending, batyr_caps, last_result)."""
    state = {
        "board": dict(board or get_starting_board()),
        "mover": "белый",
        "pending": pending,
        "batyr_caps": list(batyr_caps or []),
    }
    last = None
    for color, from_pos, to_pos in moves:
        last = logic.handle_event(
            GameEvent(
                positions=state["board"],
                mover_color=state["mover"],
                from_pos=from_pos,
                to_pos=to_pos,
                position_for_mandatory_capture=state["pending"],
            ),
            batyr_captured_this_turn=state["batyr_caps"],
        )
        state["board"] = last.updated_positions
        state["batyr_caps"] = last.captured_pieces or []
        state["pending"] = last.position_for_mandatory_capture
        if last.movers_color:
            state["mover"] = last.movers_color
    return state["board"], state["pending"], state["batyr_caps"], last


def test_batyr_chain_ends_and_clears_pending_when_landing_blocked():
    """После 36→50 цепочка не продолжается, если следующая клетка приземления занята."""
    # Минимальная позиция:
    # - чёрный батыр 36 бьёт белую фигуру на 43 и приземляется на 50
    # - затем у батыра есть потенциальное продолжение 50→38 (через 44),
    #   но 38 занята — цепочка должна завершиться.
    board = make_empty_board()
    board[36] = "черный батыр"
    board[43] = "белая шатра"
    board[44] = "белая шатра"
    board[38] = "белая шатра"  # блокируем клетку приземления для 50→38

    result = logic.handle_event(
        GameEvent(
            positions=board,
            mover_color="черный",
            from_pos=36,
            to_pos=50,
            position_for_mandatory_capture=36,
        ),
        batyr_captured_this_turn=[],
    )

    assert result.movers_color == "белый"
    assert result.position_for_mandatory_capture is None
    assert result.captured_positions == [43]

    piece = Board(result.updated_positions).get_piece_object(50)
    assert not piece.can_capture(result.updated_positions, 50, 38, result.captured_pieces)


def test_game_ends_immediately_when_biy_captured_in_shatra_chain():
    """
    Регрессия: если бий взят в середине/конце цепочки шатры, игра должна завершиться сразу,
    без передачи хода и без предложения продолжать цепочку.
    """
    # Используем словарь захватов шатры/бия:
    # 7 -> 15 берёт 10 (shatra_and_biy_possible_captures[7][15] == 10)
    # 15 -> 31 берёт 23 (shatra_and_biy_possible_captures[15][31] == 23)
    board = make_empty_board()
    board[7] = "белая шатра"
    board[10] = "черная шатра"
    board[23] = "черный бий"
    board[53] = "белый бий"

    first = logic.handle_event(
        GameEvent(
            positions=board,
            mover_color="белый",
            from_pos=7,
            to_pos=15,
            position_for_mandatory_capture=None,
        )
    )
    assert first.game_over is False
    assert first.movers_color == "белый"
    assert first.position_for_mandatory_capture == 15

    second = logic.handle_event(
        GameEvent(
            positions=first.updated_positions,
            mover_color="белый",
            from_pos=15,
            to_pos=31,
            position_for_mandatory_capture=first.position_for_mandatory_capture,
        )
    )
    assert second.game_over is True
    assert second.movers_color is None
    assert second.winner_color == "белый"
