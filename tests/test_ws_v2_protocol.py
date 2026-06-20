"""WebSocket protocol v2."""

from game_engine.game_logic import logic
from game_engine.models import GameEvent
from backend.game_helpers import bump_ply
from backend.session.v2.protocol import (
    PROTO_VERSION,
    build_move_event_from_game,
    build_snapshot,
    build_move_delta,
    game_ply,
    next_ply,
    is_v2_message,
)
from tests.helpers.engine_boards import empty_board


def test_is_v2_message():
    assert is_v2_message({"v": 2, "t": "move"})
    assert not is_v2_message({"move_from": "position1"})


def test_ply_helpers():
    game = {"ply": 0}
    assert next_ply(game) == 1
    bump_ply(game)
    assert game_ply(game) == 1


def test_build_move_event_from_server_board():
    board = empty_board()
    board[45] = "белый бий"
    board[37] = None
    game = {
        "board": board,
        "mover": "белый",
        "pending_mandatory_position": None,
    }
    event = build_move_event_from_game(game, 45, 37)
    assert event.from_pos == 45
    assert event.to_pos == 37
    assert event.mover_color == "белый"
    assert event.positions[45] == "белый бий"


def test_build_snapshot_contains_ply():
    board = empty_board()
    board[45] = "белый бий"
    game = {
        "board": board,
        "mover": "белый",
        "ply": 0,
        "move_history": [],
        "pending_batyr_captures": [],
    }
    room = {"type": "ai", "time_control": None}
    snap = build_snapshot(game, room, "белый")
    assert snap["v"] == PROTO_VERSION
    assert snap["t"] == "snapshot"
    assert snap["ply"] == 0
    assert snap["yourColor"] == "белый"


def test_build_move_delta_clears_chain_cell_when_turn_switches_with_mandatory():
    from tests.helpers.server_game_sim import USER_SEQUENCE_28, simulate_server_replay, wire_move_delta

    game, last, prev = simulate_server_replay(USER_SEQUENCE_28)
    delta = wire_move_delta(game, last, prev, 28, 36)
    assert delta.get("chainCell") is None
    assert last.position_for_mandatory_capture == 42


def test_build_move_delta_after_engine_move():
    from backend.game_helpers import update_captures

    board = empty_board()
    board[45] = "белый бий"
    board[37] = None
    game = {"board": board, "mover": "белый", "ply": 0, "pending_batyr_captures": []}
    result = logic.handle_event(
        GameEvent(positions=board, mover_color="белый", from_pos=45, to_pos=37)
    )
    bump_ply(game)
    game["board"] = result.updated_positions
    update_captures(game, result)
    game["mover"] = result.movers_color
    delta = build_move_delta(game, result, "белый", 45, 37, {"time_control": None})
    assert delta["t"] == "move"
    assert delta["ply"] == 1
    assert delta["from"] == 45
    assert delta["to"] == 37
    assert delta["batyrCaptured"] == []


def test_build_move_delta_clears_batyr_captured_when_turn_switches():
    from backend.game_helpers import update_captures, persist_pending_mandatory_position

    board = empty_board()
    board.update({
        61: "черный батыр",
        55: "белая шатра",
        1: "белый бий",
        2: "белый бий",
    })
    game = {
        "board": board,
        "mover": "черный",
        "ply": 0,
        "pending_batyr_captures": [],
        "pending_mandatory_position": None,
    }
    prev = game["mover"]
    result = logic.handle_event(
        GameEvent(positions=board, mover_color="черный", from_pos=61, to_pos=53)
    )
    persist_pending_mandatory_position(game, result, prev)
    game["board"] = result.updated_positions
    update_captures(game, result)
    game["mover"] = result.movers_color
    bump_ply(game)

    assert game["pending_batyr_captures"] == []
    assert result.captured_pieces == [55]

    delta = build_move_delta(game, result, prev, 61, 53, {"time_control": None})
    assert delta["batyrCaptured"] == []
    assert delta["turn"] == "белый"


def test_build_move_delta_keeps_batyr_captured_during_same_player_chain():
    from backend.game_helpers import update_captures, persist_pending_mandatory_position

    board = empty_board()
    board.update({
        14: "черный батыр",
        10: "белая шатра",
        8: None,
        5: "белая шатра",
        2: None,
    })
    game = {
        "board": board,
        "mover": "черный",
        "ply": 0,
        "pending_batyr_captures": [],
        "pending_mandatory_position": None,
    }
    prev = game["mover"]
    result = logic.handle_event(
        GameEvent(positions=board, mover_color="черный", from_pos=14, to_pos=8)
    )
    persist_pending_mandatory_position(game, result, prev)
    game["board"] = result.updated_positions
    update_captures(game, result)
    game["mover"] = result.movers_color
    bump_ply(game)

    assert game["pending_batyr_captures"] == [10]
    delta = build_move_delta(game, result, prev, 14, 8, {"time_control": None})
    assert delta["batyrCaptured"] == [10]
    assert delta["turn"] == "черный"
