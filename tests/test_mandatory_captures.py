"""Mandatory capture rules: biy vs shatra/batyr attackers."""

from game_engine.board import Board
from game_engine.hints import get_hints
from game_engine.validation import get_all_mandatory_captures, validate_move_with_code

from tests.helpers.engine_boards import empty_board, hint_at


def test_only_biy_can_capture_biy_may_move_or_capture():
    board = empty_board()
    board[48] = "белый бий"
    board[47] = "черная шатра"
    board[46] = None
    board[41] = None

    mandatory = get_all_mandatory_captures(Board(board), "белый", [])
    assert mandatory == [(48, 46)]

    ok_move, _, _ = validate_move_with_code(board, 48, 41, "белый", [])
    assert ok_move
    ok_cap, _, _ = validate_move_with_code(board, 48, 46, "белый", [])
    assert ok_cap

    hints = hint_at(board, "белый", 48)
    assert 46 in hints.essential_positions
    assert 41 in hints.essential_positions


def test_only_biy_capture_shatra_cannot_move():
    board = empty_board()
    board[48] = "белый бий"
    board[47] = "черная шатра"
    board[46] = None
    board[52] = "белая шатра"

    valid, _, code = validate_move_with_code(board, 52, 45, "белый", [])
    assert not valid
    assert code == "ONLY_BIY_CAN_CAPTURE"

    hints = hint_at(board, "белый", 52)
    assert hints.essential_positions == []


def test_biy_and_shatra_capture_biy_cannot_quiet_move():
    board = empty_board()
    board[20] = "белая шатра"
    board[28] = "черная шатра"
    board[36] = None
    board[48] = "белый бий"
    board[47] = "черная шатра"
    board[46] = None

    mandatory = get_all_mandatory_captures(Board(board), "белый", [])
    starts = {f for f, _ in mandatory}
    assert 20 in starts and 48 in starts

    valid, _, code = validate_move_with_code(board, 48, 41, "белый", [])
    assert not valid
    assert code in ("MANDATORY_CAPTURE_OTHER_PIECE", "MANDATORY_CAPTURE_THIS_PIECE")

    valid_cap, _, _ = validate_move_with_code(board, 48, 46, "белый", [])
    assert valid_cap


def test_biy_and_batyr_capture_other_piece_blocked():
    board = empty_board()
    board[35] = "белый батыр"
    board[49] = "черная шатра"
    board[53] = None
    board[19] = "белый бий"
    board[13] = "черная шатра"
    board[52] = "белая шатра"

    mandatory = get_all_mandatory_captures(Board(board), "белый", [])
    assert len(mandatory) >= 2

    valid, _, code = validate_move_with_code(board, 52, 45, "белый", [])
    assert not valid
    assert code == "MANDATORY_CAPTURE_OTHER_PIECE"


def test_biy_only_capture_no_pending_after_opponent_move():
    """После хода соперника бий не обязан брать — pending не ставится, ИИ может отступить."""
    from backend.board_utils import get_starting_board
    from game_engine.game_logic import logic
    from game_engine.models import GameEvent
    from backend.ai_trained import get_best_move as strong_move

    moves = [
        ("белый", 39, 32), ("черный", 24, 31), ("белый", 44, 38), ("черный", 23, 24),
        ("белый", 40, 39), ("черный", 18, 26), ("белый", 32, 25), ("черный", 12, 18),
        ("белый", 25, 27), ("черный", 21, 33), ("белый", 39, 27), ("черный", 20, 34),
        ("белый", 42, 26), ("белый", 26, 12), ("черный", 13, 20), ("белый", 12, 28),
        ("черный", 22, 34), ("белый", 41, 27), ("черный", 14, 21), ("белый", 53, 33),
        ("черный", 9, 14), ("белый", 46, 39), ("черный", 18, 25), ("белый", 47, 41),
        ("черный", 11, 18), ("белый", 38, 37), ("черный", 8, 12), ("белый", 37, 36),
        ("черный", 18, 26),
    ]
    board = get_starting_board()
    pending = None
    for color, f, t in moves:
        result = logic.handle_event(
            GameEvent(
                positions=board,
                mover_color=color,
                from_pos=f,
                to_pos=t,
                position_for_mandatory_capture=pending,
            ),
            position_history={},
        )
        board = result.updated_positions
        pending = result.position_for_mandatory_capture

    assert result.position_for_mandatory_capture is None
    assert strong_move(board, "белый", depth=5) == (33, 32)


def test_three_attackers_biy_must_capture_not_walk():
    board = empty_board()
    board[35] = "белый батыр"
    board[44] = "белая шатра"
    board[48] = "белый бий"
    board[49] = "черная шатра"
    board[50] = "черная шатра"
    board[47] = "черная шатра"

    valid, msg, code = validate_move_with_code(board, 48, 41, "белый", [])
    assert not valid
    assert "бить" in msg.lower() or code.startswith("MANDATORY")

    valid_cap, _, _ = validate_move_with_code(board, 48, 46, "белый", [])
    assert valid_cap
