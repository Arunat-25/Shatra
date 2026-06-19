"""Mandatory capture at turn start must not lock a single piece (chain mode)."""

from backend.board_utils import get_starting_board
from backend.game_helpers import persist_pending_mandatory_position
from backend.session.v2.protocol import build_move_event_from_game
from game_engine.game_logic import logic
from game_engine.models import GameEvent

USER_SEQUENCE_28 = [
    ("белый", 40, 32),
    ("черный", 20, 26),
    ("белый", 32, 20),
    ("черный", 12, 28),
    ("белый", 41, 34),
    ("черный", 28, 40),
    ("белый", 39, 41),
    ("черный", 19, 25),
    ("белый", 41, 33),
    ("черный", 25, 41),
    ("белый", 49, 33),
    ("черный", 9, 26),
    ("белый", 33, 19),
    ("черный", 11, 27),
    ("белый", 42, 34),
    ("черный", 27, 41),
    ("белый", 48, 34),
    ("черный", 10, 19),
    ("белый", 34, 26),
    ("черный", 18, 34),
    ("белый", 47, 40),
    ("черный", 21, 28),
    ("белый", 53, 42),
    ("черный", 34, 41),
    ("белый", 50, 49),
    ("черный", 41, 39),
    ("белый", 46, 32),
    ("черный", 28, 36),
]


def _board_after_sequence():
    board = get_starting_board()
    pending = None
    batyr = []
    history = {}
    last_result = None
    for color, f, t in USER_SEQUENCE_28:
        last_result = logic.handle_event(
            GameEvent(
                positions=board,
                mover_color=color,
                from_pos=f,
                to_pos=t,
                position_for_mandatory_capture=pending,
            ),
            batyr_captured_this_turn=batyr,
            position_history=history,
        )
        board = last_result.updated_positions
        pending = last_result.position_for_mandatory_capture
    return board, last_result


def test_after_black_28_36_white_mandatory_not_single_piece_chain():
    board, last = _board_after_sequence()
    assert last.movers_color == "белый"
    assert last.position_for_mandatory_capture == 42

    game = {"board": board, "mover": "белый", "pending_batyr_captures": [], "position_history": {}}
    persist_pending_mandatory_position(game, last, prev_mover="черный")
    assert game.get("pending_mandatory_position") is None

    event = build_move_event_from_game(game, 43, 29)
    assert event.position_for_mandatory_capture is None

    result = logic.handle_event(
        event,
        batyr_captured_this_turn=game.get("pending_batyr_captures"),
        position_history=game.get("position_history"),
    )
    assert result.message_code == "turn.now"
    assert 36 in (result.captured_positions or [])


def test_white_capture_black_shatra_on_36_via_42_30():
    board, _ = _board_after_sequence()
    result = logic.handle_event(
        GameEvent(
            positions=board,
            mover_color="белый",
            from_pos=42,
            to_pos=30,
            position_for_mandatory_capture=None,
        ),
        position_history={},
    )
    assert result.message_code == "turn.now"
    assert result.captured_positions == [36]


def test_same_player_chain_still_persists_pending():
    from tests.helpers.engine_boards import empty_board

    board = empty_board()
    board[20] = "белая шатра"
    board[28] = "черная шатра"
    board[36] = None
    board[44] = "черная шатра"
    board[45] = "белая шатра"
    first = logic.handle_event(
        GameEvent(positions=board, mover_color="белый", from_pos=20, to_pos=36)
    )
    assert first.movers_color == "белый"
    assert first.position_for_mandatory_capture == 36
    game = {"board": first.updated_positions, "mover": "белый"}
    persist_pending_mandatory_position(game, first, prev_mover="белый")
    assert game["pending_mandatory_position"] == 36
