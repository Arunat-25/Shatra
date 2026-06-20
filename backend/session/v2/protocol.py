"""WebSocket protocol v2 — message builders and parsers."""

from __future__ import annotations

import time
from typing import Any

from game_engine.models import GameEvent
from backend.board_utils import keys_int_to_str


def _norm_board_keys(board: dict) -> dict:
    out = {}
    for k, v in (board or {}).items():
        try:
            out[int(k)] = v
        except (TypeError, ValueError):
            out[k] = v
    return out

PROTO_VERSION = 2


def game_ply(game: dict) -> int:
    return int(game.get("ply", 0))


def next_ply(game: dict) -> int:
    return game_ply(game) + 1


def bump_ply(game: dict) -> None:
    game["ply"] = game_ply(game) + 1


def is_v2_message(data: dict) -> bool:
    return isinstance(data, dict) and data.get("v") == PROTO_VERSION and isinstance(data.get("t"), str)


def build_move_event_from_game(game: dict, from_cell: int, to_cell: int) -> GameEvent:
    pending = game.get("pending_mandatory_position")
    return GameEvent(
        positions=_norm_board_keys(game.get("board", {})),
        mover_color=game["mover"],
        from_pos=from_cell,
        to_pos=to_cell,
        position_for_mandatory_capture=pending,
    )


def _clocks_payload(room_data: dict | None, game: dict | None, compute_clock_times) -> dict[str, float] | None:
    if not room_data or not room_data.get("time_control"):
        return None
    return compute_clock_times(room_data, game) or {
        "белый": float(room_data.get("timer_white") or 0),
        "черный": float(room_data.get("timer_black") or 0),
    }


def build_snapshot(
    game: dict,
    room_data: dict,
    my_color: str | None,
    *,
    players_info: list | None = None,
) -> dict:
    from backend.game_helpers import compute_clock_times

    clocks = _clocks_payload(room_data, game, compute_clock_times)
    history = []
    for entry in game.get("move_history") or []:
        if not entry.get("from_pos") or not entry.get("to_pos"):
            continue
        history.append({
            "ply": entry.get("move_number"),
            "from": entry.get("from_pos"),
            "to": entry.get("to_pos"),
            "mover": entry.get("mover"),
        })

    payload: dict[str, Any] = {
        "v": PROTO_VERSION,
        "t": "snapshot",
        "ply": game_ply(game),
        "turn": game.get("mover"),
        "board": keys_int_to_str(game.get("board", {})),
        "chainCell": game.get("pending_mandatory_position"),
        "batyrCaptured": list(game.get("pending_batyr_captures") or []),
        "moveHistory": history,
        "yourColor": my_color,
        "gameOver": None,
        "drawOfferFrom": game.get("draw_offer_from"),
    }
    if players_info is not None:
        payload["playersInfo"] = players_info
    if clocks is not None:
        payload["clocks"] = clocks
        payload["timeControl"] = room_data.get("time_control")
        payload["increment"] = room_data.get("increment")
    if game.get("game_over"):
        payload["gameOver"] = {
            "reason": game.get("reason") or "",
            "winner": game.get("winner_color") or game.get("winner") or "",
            "ply": game_ply(game),
        }
    return payload


def build_waiting(
    room_id: str,
    room_data: dict,
    *,
    client_id: str,
    players_info: list,
) -> dict:
    room_type = room_data.get("type")
    return {
        "v": PROTO_VERSION,
        "t": "waiting",
        "link": room_id,
        "roomType": room_type,
        "showInviteLink": (
            room_type == "private"
            and client_id == room_data.get("creator_client_id")
        ),
        "playersInfo": players_info,
    }


def build_move_delta(
    game: dict,
    result,
    prev_mover: str,
    from_cell: int | None,
    to_cell: int | None,
    room_data: dict | None = None,
    *,
    board_before: dict | None = None,
) -> dict:
    from backend.game_helpers import compute_clock_times, _resolve_game_end_reason, shatra_was_promoted

    promoted = shatra_was_promoted(board_before or {}, result, from_cell, to_cell)

    payload: dict[str, Any] = {
        "v": PROTO_VERSION,
        "t": "move",
        "ply": game_ply(game),
        "mover": prev_mover,
        "from": from_cell,
        "to": to_cell,
        "turn": result.movers_color or game.get("mover"),
        "captured": list(result.captured_positions or []),
        "promoted": promoted,
        "chainCell": game.get("pending_mandatory_position"),
        "batyrCaptured": list(game.get("pending_batyr_captures") or []),
        "canPass": bool(result.opportunity_pass_the_move),
        "messageCode": result.message_code or "",
        "gameOver": bool(result.game_over),
    }
    if result.message_params:
        payload["messageParams"] = result.message_params
    if result.game_over:
        end_reason = _resolve_game_end_reason(result)
        if end_reason:
            payload["reason"] = end_reason
        if result.winner_color:
            payload["winner"] = result.winner_color
    if room_data:
        clocks = _clocks_payload(room_data, game, compute_clock_times)
        if clocks is not None:
            payload["clocks"] = clocks
    return {k: v for k, v in payload.items() if v is not None}


def build_reject(
    code: str,
    *,
    ply: int | None = None,
    snapshot: dict | None = None,
    message_params: dict | None = None,
) -> dict:
    payload: dict[str, Any] = {
        "v": PROTO_VERSION,
        "t": "reject",
        "code": code,
    }
    if ply is not None:
        payload["ply"] = ply
    if snapshot is not None:
        payload["snapshot"] = snapshot
    if message_params:
        payload["messageParams"] = message_params
    return payload


def build_error(code: str, **params) -> dict:
    payload: dict[str, Any] = {
        "v": PROTO_VERSION,
        "t": "error",
        "code": code,
    }
    if params:
        payload["messageParams"] = params
    return payload


def build_game_over(game: dict, result) -> dict:
    from backend.game_helpers import _resolve_game_end_reason

    end_reason = _resolve_game_end_reason(result) or game.get("reason") or ""
    return {
        "v": PROTO_VERSION,
        "t": "gameOver",
        "reason": end_reason,
        "winner": result.winner_color or game.get("winner_color") or "",
        "ply": game_ply(game),
    }


def build_clock_tick(room_data: dict, game: dict | None) -> dict:
    from backend.game_helpers import compute_clock_times

    clocks = _clocks_payload(room_data, game, compute_clock_times)
    return {
        "v": PROTO_VERSION,
        "t": "clock",
        "clocks": clocks or {},
        "turn": game.get("mover") if game else None,
        "serverTime": int(time.time() * 1000),
    }


def wrap_control_v1(v1_payload: dict) -> dict:
    """Attach v2 envelope to legacy control payloads where needed."""
    msg_type = v1_payload.get("type") or v1_payload.get("status")
    if not msg_type:
        return v1_payload
    out: dict = {"v": PROTO_VERSION, "t": msg_type}
    for key, value in v1_payload.items():
        if key in ("type", "status", "v", "t"):
            continue
        out[key] = value
    return out
