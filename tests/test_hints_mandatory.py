"""Hints during mandatory capture and chains."""

from game_engine.message_codes import CAPTURE_CONTINUE_SAME, CAPTURE_MUST
from game_engine.models import GameEvent
from game_engine.game_logic import logic
from game_engine.validation import validate_move

from tests.helpers.engine_boards import empty_board, hint_at, play_sequence


def test_hints_only_legal_targets():
    board = empty_board()
    board[11] = "черная шатра"
    hints = hint_at(board, "черный", 11)
    for target in hints.essential_positions:
        ok, _ = validate_move(board, 11, target, "черный", [], check_mandatory=True)
        assert ok, f"hint {target} must be valid"


def test_chain_hints_only_on_mandatory_piece():
    board = empty_board()
    board[11] = "черная шатра"
    board[18] = "белая шатра"
    board[25] = None
    board[32] = "белая шатра"
    board[20] = "черная шатра"

    state = play_sequence([("черный", 11, 25)], board=board)
    pending = state["pending"]
    assert pending == 25, "expected capture chain from 11→25 with continue via 32"

    chain_hints = hint_at(
        state["board"], "черный", 25, pending=pending, batyr_caps=state["batyr_caps"]
    )
    assert chain_hints.essential_positions

    other = hint_at(
        state["board"], "черный", 20, pending=pending, batyr_caps=state["batyr_caps"]
    )
    assert other.essential_positions == []
    assert other.message_code == CAPTURE_CONTINUE_SAME


def test_mandatory_phase_empty_hints_for_non_attacking_pieces():
    board = empty_board()
    board[20] = "белая шатра"
    board[28] = "черная шатра"
    board[36] = None
    board[48] = "белый бий"
    board[47] = "черная шатра"
    board[52] = "белая шатра"

    hints_shatra = hint_at(board, "белый", 52)
    assert hints_shatra.essential_positions == []

    hints_biy = hint_at(board, "белый", 48)
    assert 46 in hints_biy.essential_positions


def test_chain_hints_exclude_shatra_fortress_capture():
    board = empty_board()
    board[14] = "черная шатра"
    board[10] = "белая шатра"
    board[8] = None

    chain_hints = hint_at(board, "черный", 14, pending=14)
    assert 8 not in chain_hints.essential_positions

    result = logic.handle_event(
        GameEvent(
            positions=board,
            mover_color="черный",
            from_pos=14,
            to_pos=8,
            position_for_mandatory_capture=14,
        )
    )
    assert result.message_code == CAPTURE_MUST
    assert result.updated_positions[8] is None
