"""Shared board helpers for game_engine tests."""

from __future__ import annotations

from game_engine.game_logic import logic
from game_engine.models import GameEvent


def empty_board() -> dict:
    return {i: None for i in range(1, 63)}


def play_sequence(
    moves: list[tuple[str, int, int]],
    board: dict | None = None,
    *,
    pending: int | None = None,
    batyr_caps: list[int] | None = None,
    position_history: dict | None = None,
    moves_with_two_biys: int = 0,
    initial_mover: str = "белый",
):
    """Play (mover_color, from, to) moves; return final state dict."""
    state = {
        "board": dict(board or empty_board()),
        "mover": initial_mover,
        "pending": pending,
        "batyr_caps": list(batyr_caps or []),
        "history": dict(position_history or {}),
        "two_biys": moves_with_two_biys,
    }
    last = None
    for color, from_pos, to_pos in moves:
        state["mover"] = color
        last = logic.handle_event(
            GameEvent(
                positions=state["board"],
                mover_color=color,
                from_pos=from_pos,
                to_pos=to_pos,
                position_for_mandatory_capture=state["pending"],
            ),
            batyr_captured_this_turn=state["batyr_caps"],
            position_history=state["history"],
            moves_with_two_biys=state["two_biys"],
        )
        assert last.updated_positions is not None, (
            f"move {color} {from_pos}->{to_pos} failed: {last.message_code}"
        )
        state["board"] = last.updated_positions
        state["batyr_caps"] = list(last.captured_pieces or [])
        state["pending"] = last.position_for_mandatory_capture
        if last.movers_color:
            state["mover"] = last.movers_color
    return {
        "board": state["board"],
        "pending": state["pending"],
        "batyr_caps": state["batyr_caps"],
        "mover": state["mover"],
        "last": last,
        "history": state["history"],
    }


def hint_at(
    board: dict,
    color: str,
    from_cell: int,
    *,
    pending: int | None = None,
    batyr_caps: list[int] | None = None,
):
    return logic.handle_event(
        GameEvent(
            positions=board,
            mover_color=color,
            position=from_cell,
            position_for_mandatory_capture=pending,
        ),
        batyr_captured_this_turn=batyr_caps or [],
    )
