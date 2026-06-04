"""Multi-step captures, pending reset, biy pass turn."""

from game_engine.message_codes import (
    CAPTURE_CONTINUE,
    CAPTURE_CONTINUE_SAME,
    CAPTURE_MUST_CONTINUE,
    MOVE_PASSED,
    PIECE_PROMOTED,
    TURN_NOW,
)
from game_engine.models import GameEvent
from game_engine.game_logic import logic
from game_engine.pieces.batyr import Batyr

from tests.helpers.engine_boards import empty_board, hint_at, play_sequence


def test_shatra_chain_pending_and_other_piece_rejected():
    board = empty_board()
    board[20] = "белая шатра"
    board[28] = "черная шатра"
    board[36] = None
    board[44] = "черная шатра"
    board[45] = "белая шатра"
    board[52] = None

    first = logic.handle_event(
        GameEvent(positions=board, mover_color="белый", from_pos=20, to_pos=36)
    )
    assert first.message_code == CAPTURE_CONTINUE
    assert first.position_for_mandatory_capture == 36
    assert first.movers_color == "белый"

    wrong_piece = logic.handle_event(
        GameEvent(
            positions=first.updated_positions,
            mover_color="белый",
            from_pos=45,
            to_pos=37,
            position_for_mandatory_capture=first.position_for_mandatory_capture,
        )
    )
    assert wrong_piece.message_code == CAPTURE_CONTINUE_SAME

    second = logic.handle_event(
        GameEvent(
            positions=first.updated_positions,
            mover_color="белый",
            from_pos=36,
            to_pos=52,
            position_for_mandatory_capture=36,
        )
    )
    assert second.message_code == TURN_NOW
    assert second.position_for_mandatory_capture is None
    assert second.movers_color == "черный"
    assert second.updated_positions[28] is None
    assert second.updated_positions[44] is None


def test_black_shatra_chain_two_captures():
    board = empty_board()
    board[11] = "черная шатра"
    board[18] = "белая шатра"
    board[25] = None
    board[32] = "белая шатра"

    state = play_sequence([("черный", 11, 25), ("черный", 25, 39)], board=board)
    assert state["last"].message_code == TURN_NOW
    assert state["pending"] is None
    assert state["board"][18] is None
    assert state["board"][32] is None


def test_batyr_chain_accumulates_captured_cells():
    board = empty_board()
    board[14] = "черный батыр"
    board[10] = "белая шатра"
    board[8] = None
    board[5] = "белая шатра"
    board[2] = None

    first = logic.handle_event(
        GameEvent(positions=board, mover_color="черный", from_pos=14, to_pos=8)
    )
    assert first.message_code == CAPTURE_CONTINUE
    assert first.position_for_mandatory_capture == 8
    assert 10 in first.captured_pieces

    second = logic.handle_event(
        GameEvent(
            positions=first.updated_positions,
            mover_color="черный",
            from_pos=8,
            to_pos=2,
            position_for_mandatory_capture=8,
        ),
        batyr_captured_this_turn=first.captured_pieces,
    )
    assert second.message_code == TURN_NOW
    assert second.position_for_mandatory_capture is None
    assert 5 in second.captured_positions
    assert 10 in second.captured_pieces
    assert 5 in second.captured_pieces


def test_batyr_cannot_rejump_captured_cell_in_same_turn():
    """Нельзя снова использовать клетку, уже взятую в этой серии."""
    board = empty_board()
    board[14] = "черный батыр"
    board[10] = "белая шатра"
    board[8] = None

    first = logic.handle_event(
        GameEvent(positions=board, mover_color="черный", from_pos=14, to_pos=8)
    )
    caps = list(first.captured_pieces)
    assert 10 in caps

    batyr = Batyr("черный")
    assert not batyr.can_capture(first.updated_positions, 8, 10, caps)


def test_batyr_chain_cannot_jump_beyond_captured_cell():
    board = empty_board()
    board[14] = "черный батыр"
    board[10] = "белая шатра"
    board[8] = None
    board[5] = "белая шатра"
    board[2] = None
    board[21] = "белая шатра"
    board[28] = None

    first = logic.handle_event(
        GameEvent(positions=board, mover_color="черный", from_pos=14, to_pos=8)
    )
    assert first.message_code == CAPTURE_CONTINUE
    assert first.position_for_mandatory_capture == 8
    assert first.captured_pieces == [10]

    hints = hint_at(
        first.updated_positions,
        "черный",
        8,
        pending=8,
        batyr_caps=first.captured_pieces,
    )
    assert 2 in hints.essential_positions
    assert 28 not in hints.essential_positions

    blocked = logic.handle_event(
        GameEvent(
            positions=first.updated_positions,
            mover_color="черный",
            from_pos=8,
            to_pos=28,
            position_for_mandatory_capture=8,
        ),
        batyr_captured_this_turn=first.captured_pieces,
    )
    assert blocked.message_code == CAPTURE_MUST_CONTINUE
    assert blocked.updated_positions[8] == "черный батыр"
    assert blocked.updated_positions[21] == "белая шатра"
    assert blocked.updated_positions[28] is None


def test_shatra_capture_promote_continues_as_batyr():
    """Взятие на клетку превращения: шатра → батыр, цепочка продолжается взятиями батыра."""
    board = empty_board()
    board[56] = "черная шатра"
    board[58] = "белая шатра"
    board[60] = None
    board[61] = "белая шатра"

    first = logic.handle_event(
        GameEvent(positions=board, mover_color="черный", from_pos=56, to_pos=60)
    )
    assert first.message_code == CAPTURE_CONTINUE
    assert first.position_for_mandatory_capture == 60
    assert first.movers_color == "черный"
    assert first.updated_positions[60] == "черный батыр"
    assert first.updated_positions[58] is None

    second = logic.handle_event(
        GameEvent(
            positions=first.updated_positions,
            mover_color="черный",
            from_pos=60,
            to_pos=62,
            position_for_mandatory_capture=60,
        )
    )
    assert second.message_code == TURN_NOW
    assert second.position_for_mandatory_capture is None
    assert second.movers_color == "белый"
    assert second.updated_positions[61] is None


def test_shatra_capture_promote_without_followup_ends_turn():
    board = empty_board()
    board[56] = "черная шатра"
    board[58] = "белая шатра"
    board[60] = None

    result = logic.handle_event(
        GameEvent(positions=board, mover_color="черный", from_pos=56, to_pos=60)
    )
    assert result.message_code == TURN_NOW
    assert result.position_for_mandatory_capture is None
    assert result.movers_color == "белый"
    assert result.updated_positions[60] == "черный батыр"
    assert result.updated_positions[58] is None


def test_shatra_quiet_promotion_ends_turn_with_promoted_message():
    board = empty_board()
    board[57] = "черная шатра"
    board[10] = "черный бий"
    board[53] = "белый бий"

    result = logic.handle_event(
        GameEvent(positions=board, mover_color="черный", from_pos=57, to_pos=60)
    )
    assert result.message_code == PIECE_PROMOTED
    assert result.updated_positions[60] == "черный батыр"
    assert result.position_for_mandatory_capture is None


def test_biy_capture_without_chain_offers_pass_then_turn_switches():
    board = empty_board()
    board[48] = "белый бий"
    board[47] = "черная шатра"
    board[46] = None
    board[53] = "черный бий"

    cap = logic.handle_event(
        GameEvent(positions=board, mover_color="белый", from_pos=48, to_pos=46)
    )
    assert cap.opportunity_pass_the_move is True
    assert cap.position_for_mandatory_capture is None
    assert cap.movers_color == "черный"

    passed = logic.handle_event(
        GameEvent(
            positions=cap.updated_positions,
            mover_color="белый",
            from_pos=0,
            to_pos=0,
            position_for_mandatory_capture=0,
        )
    )
    assert passed.message_code == MOVE_PASSED
    assert passed.movers_color == "черный"


def test_biy_capture_with_optional_chain_can_pass_without_continuing():
    board = empty_board()
    board[10] = "белый бий"
    board[13] = "черная шатра"
    board[19] = None
    board[26] = "черная шатра"
    board[33] = None
    board[53] = "черный бий"

    first = logic.handle_event(
        GameEvent(positions=board, mover_color="белый", from_pos=10, to_pos=19)
    )
    assert first.position_for_mandatory_capture == 19
    assert first.opportunity_pass_the_move is True

    passed = logic.handle_event(
        GameEvent(
            positions=first.updated_positions,
            mover_color="белый",
            from_pos=0,
            to_pos=0,
            position_for_mandatory_capture=0,
        )
    )
    assert passed.message_code == MOVE_PASSED
    assert passed.movers_color == "черный"
    assert first.updated_positions[13] is None
