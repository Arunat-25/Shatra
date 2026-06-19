"""Simulate server game state updates (WS v2 handlers) for sync tests."""

from __future__ import annotations

import json
from pathlib import Path

from backend.board_utils import get_starting_board
from backend.game_helpers import bump_ply, persist_pending_mandatory_position
from backend.session.v2.protocol import build_move_event_from_game, build_move_delta, build_snapshot
from game_engine.game_logic import logic
from game_engine.models import GameEvent


def new_server_game(*, board: dict | None = None, mover: str = "белый") -> dict:
    return {
        "board": dict(board or get_starting_board()),
        "mover": mover,
        "pending_mandatory_position": None,
        "pending_batyr_captures": [],
        "position_history": {},
        "ply": 0,
        "move_history": [],
    }


def simulate_server_replay(
    moves: list[tuple[str, int, int]],
    *,
    game: dict | None = None,
) -> tuple[dict, object, str]:
    """
    Replay moves through build_move_event_from_game + persist_pending_mandatory_position.
    Returns (game, last_result, last_prev_mover).
    """
    state = game or new_server_game(mover=moves[0][0])
    last_result = None
    last_prev_mover = state["mover"]

    for color, from_pos, to_pos in moves:
        assert state["mover"] == color, (
            f"expected mover {state['mover']}, got {color} for {from_pos}->{to_pos}"
        )
        prev_mover = state["mover"]
        event = build_move_event_from_game(state, from_pos, to_pos)
        result = logic.handle_event(
            event,
            batyr_captured_this_turn=state.get("pending_batyr_captures"),
            position_history=state.get("position_history"),
            moves_with_two_biys=state.get("moves_with_two_biys", 0),
        )
        assert result.updated_positions is not None, (
            f"move rejected: {color} {from_pos}->{to_pos} code={result.message_code}"
        )

        persist_pending_mandatory_position(state, result, prev_mover)
        state["board"] = result.updated_positions
        if result.movers_color:
            state["mover"] = result.movers_color
        bump_ply(state)

        last_result = result
        last_prev_mover = prev_mover

    return state, last_result, last_prev_mover


def client_chain_cell(game: dict) -> int | None:
    """Chain cell the browser uses (mirrors snapshot / move delta adapter)."""
    pending = game.get("pending_mandatory_position")
    return int(pending) if pending is not None else None


def wire_move_delta(game: dict, result, prev_mover: str, from_cell: int, to_cell: int) -> dict:
    return build_move_delta(
        game,
        result,
        prev_mover,
        from_cell,
        to_cell,
        room_data={"time_control": None},
    )


def try_server_move(
    game: dict,
    from_cell: int,
    to_cell: int,
    *,
    override_chain: int | None = ...,  # type: ignore[assignment]
) -> object:
    """
    Apply one move against current server game (updates game in place).
    override_chain: force chain_capture_cell on the event (simulate stale server bug).
    """
    prev_mover = game["mover"]
    event = build_move_event_from_game(game, from_cell, to_cell)
    if override_chain is not ...:
        event.position_for_mandatory_capture = override_chain

    result = logic.handle_event(
        event,
        batyr_captured_this_turn=game.get("pending_batyr_captures"),
        position_history=game.get("position_history"),
        moves_with_two_biys=game.get("moves_with_two_biys", 0),
    )
    if result.updated_positions and result.updated_positions != game["board"]:
        persist_pending_mandatory_position(game, result, prev_mover)
        game["board"] = result.updated_positions
        if result.movers_color:
            game["mover"] = result.movers_color
        bump_ply(game)
    return result


def snapshot_chain_cell(game: dict, *, my_color: str | None = None) -> int | None:
    snap = build_snapshot(game, {"type": "ai", "time_control": None}, my_color)
    cell = snap.get("chainCell")
    return int(cell) if cell is not None else None


_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "sync" / "client_server_sync.json"


def _load_sync_scenarios() -> list[dict]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))["scenarios"]


def _moves_from_fixture(raw_moves: list) -> list[tuple[str, int, int]]:
    return [(color, int(f), int(t)) for color, f, t in raw_moves]


def moves_for_scenario(scenario_id: str) -> list[tuple[str, int, int]]:
    for scenario in _load_sync_scenarios():
        if scenario["id"] == scenario_id:
            return _moves_from_fixture(scenario["moves"])
    raise KeyError(scenario_id)


USER_SEQUENCE_28 = moves_for_scenario("user_sequence_28_white_mandatory")
