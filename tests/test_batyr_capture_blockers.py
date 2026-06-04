"""Батыр: взятые в текущей серии клетки блокируют дальнейший путь."""

from game_engine.board import Board
from game_engine.game_logic import logic
from game_engine.hints import get_hints
from game_engine.message_codes import CAPTURE_CONTINUE, CAPTURE_MUST_CONTINUE
from game_engine.models import GameEvent
from game_engine.pieces.batyr import Batyr
from game_engine.validation import get_all_mandatory_captures, validate_move

from tests.helpers.engine_boards import empty_board, hint_at


def _black_batyr_chain_after_first_capture():
    """14→8 берёт 10; с 8 можно продолжить на 2 (через 5), но не на 28 (через 10)."""
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
    return first


def test_batyr_can_capture_on_ray_not_blocked_by_ghost_on_other_ray():
    first = _black_batyr_chain_after_first_capture()
    batyr = Batyr("черный")
    caps = first.captured_pieces

    assert batyr.can_capture(first.updated_positions, 8, 2, caps)
    assert validate_move(first.updated_positions, 8, 2, "черный", caps)[0]


def test_batyr_cannot_capture_beyond_ghost_on_same_ray():
    first = _black_batyr_chain_after_first_capture()
    batyr = Batyr("черный")
    caps = first.captured_pieces
    cells = first.updated_positions

    for blocked_target in (28, 35, 42):
        assert not batyr.can_capture(cells, 8, blocked_target, caps), (
            f"8→{blocked_target} must be blocked by ghost on 10"
        )
        valid, _ = validate_move(cells, 8, blocked_target, "черный", caps)
        assert not valid


def test_batyr_mandatory_captures_exclude_targets_beyond_ghost():
    first = _black_batyr_chain_after_first_capture()
    board = Board(first.updated_positions)
    mandatory = get_all_mandatory_captures(board, "черный", first.captured_pieces)

    assert (8, 2) in mandatory
    assert all(to_cell != 28 for _, to_cell in mandatory)
    assert all(to_cell != 35 for _, to_cell in mandatory)


def test_batyr_chain_hints_exclude_targets_beyond_ghost():
    first = _black_batyr_chain_after_first_capture()
    caps = first.captured_pieces
    cells = first.updated_positions

    hints = get_hints(
        cells, "черный", 8,
        batyr_captured_this_turn=caps,
        chain_capture_cell=8,
    )
    assert 2 in hints.essential_positions
    assert 28 not in hints.essential_positions
    assert 35 not in hints.essential_positions

    via_logic = hint_at(cells, "черный", 8, pending=8, batyr_caps=caps)
    assert 2 in via_logic.essential_positions
    assert 28 not in via_logic.essential_positions


def test_batyr_chain_move_beyond_ghost_is_rejected():
    first = _black_batyr_chain_after_first_capture()

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


def test_batyr_second_capture_in_chain_still_allowed_before_ghost():
    first = _black_batyr_chain_after_first_capture()

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
    assert second.updated_positions[2] == "черный батыр"
    assert second.updated_positions[5] is None
    assert 10 in second.captured_pieces
    assert 5 in second.captured_pieces


def test_batyr_cannot_capture_enemy_on_already_captured_cell():
    """Нельзя снова «бить» через клетку, уже взятую в этой серии."""
    first = _black_batyr_chain_after_first_capture()
    batyr = Batyr("черный")

    assert not batyr.can_capture(first.updated_positions, 8, 10, first.captured_pieces)


def test_batyr_cannot_land_on_captured_cell_even_after_enemy():
    """Прозрачная клетка не может быть полем приземления."""
    cells = empty_board()
    cells[2] = "черный батыр"
    cells[5] = "белая шатра"
    cells[10] = None
    captured = [10]

    batyr = Batyr("черный")
    assert not batyr.can_capture(cells, 2, 10, captured)

    valid, _ = validate_move(
        cells, 2, 10, "черный", captured, chain_capture_cell=2,
    )
    assert not valid


def test_batyr_chain_hints_exclude_captured_landing_cell():
    cells = empty_board()
    cells[2] = "черный батыр"
    cells[5] = "белая шатра"
    cells[10] = None
    cells[14] = None
    captured = [10]

    hints = get_hints(
        cells, "черный", 2,
        batyr_captured_this_turn=captured,
        chain_capture_cell=2,
    )
    assert 10 not in hints.essential_positions
    assert 8 in hints.essential_positions
    assert 14 not in hints.essential_positions


def test_batyr_chain_move_to_captured_cell_is_rejected():
    cells = empty_board()
    cells[2] = "черный батыр"
    cells[5] = "белая шатра"
    cells[10] = None
    captured = [10]

    result = logic.handle_event(
        GameEvent(
            positions=cells,
            mover_color="черный",
            from_pos=2,
            to_pos=10,
            position_for_mandatory_capture=2,
        ),
        batyr_captured_this_turn=captured,
    )
    assert result.message_code == CAPTURE_MUST_CONTINUE
    assert result.updated_positions[2] == "черный батыр"
    assert result.updated_positions[5] == "белая шатра"
    assert result.updated_positions[10] is None


def test_batyr_two_ghosts_block_path_after_second_capture():
    """После двух взятий обе прозрачные клетки блокируют луч дальше."""
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
    assert set(second.captured_pieces) == {10, 5}
    assert second.updated_positions[2] == "черный батыр"

    batyr = Batyr("черный")
    cells = second.updated_positions
    caps = second.captured_pieces

    # С 2 враг на 21, приземление 28 — луч пересекает ghost на 5 и/или 10
    assert not batyr.can_capture(cells, 2, 28, caps)
    hints = get_hints(
        cells, "черный", 2,
        batyr_captured_this_turn=caps,
        chain_capture_cell=2,
    )
    assert 28 not in hints.essential_positions
