"""Audit: wire payloads must match persisted game state (not raw engine result)."""

from __future__ import annotations

import pytest

from backend.game_helpers import (
    build_move_delta_response,
    build_move_response,
    persist_pending_mandatory_position,
    update_captures,
    bump_ply,
    shatra_was_promoted,
)
from backend.session.v2.protocol import build_move_delta, build_snapshot
from game_engine.game_logic import logic
from game_engine.message_codes import MOVE_PASSED
from game_engine.models import GameEvent
from tests.helpers.engine_boards import empty_board
from tests.helpers.server_game_sim import (
    _load_sync_scenarios,
    _moves_from_fixture,
    new_server_game,
)


def _apply_server_side(game: dict, result, prev_mover: str) -> None:
    if result.updated_positions:
        game["board"] = result.updated_positions
    persist_pending_mandatory_position(game, result, prev_mover)
    update_captures(game, result)
    if result.movers_color:
        game["mover"] = result.movers_color


def _apply_move_delta_py(board: dict, from_cell: int, to_cell: int, *, captured=None, promoted=False) -> dict:
    """Mirror frontend/ws/v2/applyDelta.js."""
    nxt = dict(board)
    piece = nxt.get(from_cell)
    if not piece:
        return nxt
    for pos in captured or []:
        nxt[int(pos)] = None
    nxt[to_cell] = piece
    nxt[from_cell] = None
    if promoted and piece and "шатра" in piece:
        nxt[to_cell] = "белый батыр" if "бел" in piece else "черный батыр"
    return nxt


def _assert_wire_matches_game(
    game: dict, result, prev_mover: str, from_cell: int, to_cell: int, *, board_before: dict,
) -> None:
    delta = build_move_delta(
        game, result, prev_mover, from_cell, to_cell,
        room_data={"time_control": None}, board_before=board_before,
    )
    v1_delta = build_move_delta_response(
        game, result, prev_mover, from_cell, to_cell, board_before=board_before,
    )
    v1_full = build_move_response(game, result, prev_mover, from_cell, to_cell)

    expected_batyr = list(game.get("pending_batyr_captures") or [])
    expected_chain = game.get("pending_mandatory_position")

    assert delta.get("batyrCaptured") == expected_batyr
    assert v1_delta.get("captured_pieces") == expected_batyr
    assert v1_full.get("captured_pieces", []) == expected_batyr or v1_full.get("captured_pieces") is None

    assert delta.get("chainCell") == expected_chain
    assert v1_delta.get("position_for_mandatory_capture") == expected_chain
    assert v1_full.get("position_for_mandatory_capture") == expected_chain

    snap = build_snapshot(game, {"type": "ai", "time_control": None}, "белый")
    assert snap.get("batyrCaptured") == expected_batyr
    assert snap.get("chainCell") == expected_chain

    # canPass is per-move (not persisted); must match engine for this ply
    assert delta.get("canPass") is bool(result.opportunity_pass_the_move)
    if prev_mover != game.get("mover"):
        assert delta.get("canPass") is False


@pytest.mark.parametrize("scenario", _load_sync_scenarios(), ids=lambda s: s["id"])
def test_sync_scenarios_wire_matches_persisted_game(scenario):
    if "board" in scenario:
        game = new_server_game(
            board={int(k): v for k, v in scenario["board"].items()},
            mover=scenario.get("mover", scenario["expect_mover"]),
        )
    else:
        game = new_server_game(mover=_moves_from_fixture(scenario["moves"])[0][0])

    moves = _moves_from_fixture(scenario["moves"])
    for color, from_cell, to_cell in moves:
        prev = game["mover"]
        board_before = dict(game["board"])
        event = GameEvent(
            positions=game["board"],
            mover_color=color,
            from_pos=from_cell,
            to_pos=to_cell,
            position_for_mandatory_capture=game.get("pending_mandatory_position"),
        )
        result = logic.handle_event(
            event,
            batyr_captured_this_turn=game.get("pending_batyr_captures"),
        )
        assert result.updated_positions is not None
        _apply_server_side(game, result, prev)
        bump_ply(game)
        _assert_wire_matches_game(game, result, prev, from_cell, to_cell, board_before=board_before)


def test_batyr_turn_switch_delta_must_not_leak_captured_ghosts():
    board = empty_board()
    board.update({61: "черный батыр", 55: "белая шатра", 1: "белый бий", 2: "белый бий"})
    game = new_server_game(board=board, mover="черный")
    prev = game["mover"]
    result = logic.handle_event(
        GameEvent(positions=board, mover_color="черный", from_pos=61, to_pos=53)
    )
    _apply_server_side(game, result, prev)
    assert game["pending_batyr_captures"] == []
    assert list(result.captured_pieces or []) == [55]
    _assert_wire_matches_game(game, result, prev, 61, 53, board_before=board)


def test_batyr_chain_delta_keeps_ghosts_for_same_player():
    board = empty_board()
    board.update({14: "черный батыр", 10: "белая шатра", 8: None, 5: "белая шатра", 2: None})
    game = new_server_game(board=board, mover="черный")
    prev = game["mover"]
    result = logic.handle_event(
        GameEvent(positions=board, mover_color="черный", from_pos=14, to_pos=8)
    )
    _apply_server_side(game, result, prev)
    assert game["pending_batyr_captures"] == [10]
    assert game["pending_mandatory_position"] == 8
    _assert_wire_matches_game(game, result, prev, 14, 8, board_before=board)


def test_biy_pass_turn_clears_chain_and_batyr_on_wire():
    board = empty_board()
    board.update({
        10: "белый бий", 13: "черная шатра", 19: None,
        26: "черная шатра", 33: None, 53: "черный бий",
    })
    game = new_server_game(board=board, mover="белый")
    prev = game["mover"]
    board_before = dict(board)
    first = logic.handle_event(
        GameEvent(positions=board, mover_color="белый", from_pos=10, to_pos=19)
    )
    _apply_server_side(game, first, prev)
    assert game["pending_mandatory_position"] == 19
    assert first.opportunity_pass_the_move is True

    prev = game["mover"]
    board_before_pass = dict(game["board"])
    passed = logic.handle_event(
        GameEvent(
            positions=game["board"],
            mover_color="белый",
            from_pos=0,
            to_pos=0,
            position_for_mandatory_capture=0,
        ),
        batyr_captured_this_turn=game.get("pending_batyr_captures"),
    )
    _apply_server_side(game, passed, prev)
    assert passed.message_code == MOVE_PASSED
    assert game.get("pending_mandatory_position") is None
    assert game.get("pending_batyr_captures") == []
    _assert_wire_matches_game(game, passed, prev, 0, 0, board_before=board_before_pass)


@pytest.mark.parametrize("scenario", _load_sync_scenarios(), ids=lambda s: s["id"])
def test_apply_move_delta_matches_engine_board(scenario):
    """H12: client applyMoveDelta must reconstruct the same board as the engine."""
    if "board" in scenario:
        game = new_server_game(
            board={int(k): v for k, v in scenario["board"].items()},
            mover=scenario.get("mover", scenario["expect_mover"]),
        )
    else:
        game = new_server_game(mover=_moves_from_fixture(scenario["moves"])[0][0])

    for color, from_cell, to_cell in _moves_from_fixture(scenario["moves"]):
        prev_board = dict(game["board"])
        prev_mover = game["mover"]
        event = GameEvent(
            positions=game["board"],
            mover_color=color,
            from_pos=from_cell,
            to_pos=to_cell,
            position_for_mandatory_capture=game.get("pending_mandatory_position"),
        )
        result = logic.handle_event(
            event,
            batyr_captured_this_turn=game.get("pending_batyr_captures"),
        )
        assert result.updated_positions is not None
        promoted = shatra_was_promoted(prev_board, result, from_cell, to_cell)
        delta_board = _apply_move_delta_py(
            prev_board,
            from_cell,
            to_cell,
            captured=result.captured_positions,
            promoted=promoted,
        )
        assert delta_board == result.updated_positions, (
            f"{scenario['id']}: {from_cell}->{to_cell}"
        )
        _apply_server_side(game, result, prev_mover)
        bump_ply(game)


def test_capture_promotion_sets_promoted_flag_even_with_turn_now_message():
    """H17: capture promotion uses turn.now but delta must still set promoted=true."""
    board = empty_board()
    board.update({56: "черная шатра", 58: "белая шатра", 60: None})
    game = new_server_game(board=board, mover="черный")
    prev = game["mover"]
    result = logic.handle_event(GameEvent(positions=board, mover_color="черный", from_pos=56, to_pos=60))
    _apply_server_side(game, result, prev)
    assert result.message_code == "turn.now"
    assert game["board"][60] == "черный батыр"
    delta = build_move_delta(
        game, result, prev, 56, 60, room_data={"time_control": None}, board_before=board,
    )
    assert delta.get("promoted") is True
    desk_from_delta = _apply_move_delta_py(board, 56, 60, captured=result.captured_positions, promoted=True)
    assert desk_from_delta == game["board"]


def test_quiet_promotion_sets_promoted_flag():
    board = empty_board()
    board.update({57: "черная шатра", 10: "черный бий", 53: "белый бий"})
    game = new_server_game(board=board, mover="черный")
    prev = game["mover"]
    result = logic.handle_event(GameEvent(positions=board, mover_color="черный", from_pos=57, to_pos=60))
    _apply_server_side(game, result, prev)
    assert result.message_code == "piece.promoted"
    delta = build_move_delta(
        game, result, prev, 57, 60, room_data={"time_control": None}, board_before=board,
    )
    assert delta.get("promoted") is True


def test_snapshot_mid_batyr_chain_matches_persisted_game():
    board = empty_board()
    board.update({14: "черный батыр", 10: "белая шатра", 8: None, 5: "белая шатра", 2: None})
    game = new_server_game(board=board, mover="черный")
    prev = game["mover"]
    result = logic.handle_event(GameEvent(positions=board, mover_color="черный", from_pos=14, to_pos=8))
    _apply_server_side(game, result, prev)
    snap = build_snapshot(game, {"type": "ai", "time_control": None}, "белый")
    assert snap.get("chainCell") == 8
    assert snap.get("batyrCaptured") == [10]
    assert snap.get("turn") == "черный"
    assert snap.get("board", {}).get("8") == "черный батыр" or snap.get("board", {}).get(8) == "черный батыр"


def test_reject_snapshot_preserves_mid_chain_state():
    """H22: v2 reject with snapshot must carry persisted chain/batyr for resync."""
    board = empty_board()
    board.update({14: "черный батыр", 10: "белая шатра", 8: None, 5: "белая шатра", 2: None})
    game = new_server_game(board=board, mover="черный")
    prev = game["mover"]
    result = logic.handle_event(GameEvent(positions=board, mover_color="черный", from_pos=14, to_pos=8))
    _apply_server_side(game, result, prev)
    snap = build_snapshot(game, {"type": "ai", "time_control": None}, "белый")
    from backend.session.v2.protocol import build_reject

    reject = build_reject("move.impossible", snapshot=snap)
    assert reject["snapshot"]["chainCell"] == 8
    assert reject["snapshot"]["batyrCaptured"] == [10]
    assert reject["snapshot"]["turn"] == "черный"


def test_wire_never_sends_stale_mandatory_on_turn_switch():
    """H33: persisted game clears mandatory; wire chainCell must be absent/null."""
    board = empty_board()
    board.update({61: "черный батыр", 55: "белая шатра", 1: "белый бий", 2: "белый бий"})
    game = new_server_game(board=board, mover="черный")
    prev = game["mover"]
    board_before = dict(board)
    result = logic.handle_event(GameEvent(positions=board, mover_color="черный", from_pos=61, to_pos=53))
    _apply_server_side(game, result, prev)
    delta = build_move_delta(
        game, result, prev, 61, 53, room_data={"time_control": None}, board_before=board_before,
    )
    assert game.get("pending_mandatory_position") is None
    assert delta.get("chainCell") is None
    v1 = build_move_delta_response(
        game, result, prev, 61, 53, board_before=board_before,
    )
    assert v1.get("position_for_mandatory_capture") is None


def test_pass_move_wire_can_pass_false_after_turn_switch():
    """H24: pass ends chain; wire must not offer pass on next turn."""
    board = empty_board()
    board.update({
        10: "белый бий", 13: "черная шатра", 19: None,
        26: "черная шатра", 33: None, 53: "черный бий",
    })
    game = new_server_game(board=board, mover="белый")
    prev = game["mover"]
    first = logic.handle_event(GameEvent(positions=board, mover_color="белый", from_pos=10, to_pos=19))
    _apply_server_side(game, first, prev)
    prev = game["mover"]
    board_before = dict(board)
    passed = logic.handle_event(
        GameEvent(
            positions=game["board"],
            mover_color="белый",
            from_pos=0,
            to_pos=0,
            position_for_mandatory_capture=0,
        ),
        batyr_captured_this_turn=game.get("pending_batyr_captures"),
    )
    _apply_server_side(game, passed, prev)
    delta = build_move_delta(
        game, passed, prev, 0, 0, room_data={"time_control": None}, board_before=board_before,
    )
    assert delta.get("canPass") is False
    assert delta.get("chainCell") is None
    assert delta.get("batyrCaptured") == []
