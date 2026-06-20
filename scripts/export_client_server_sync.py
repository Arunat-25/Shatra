#!/usr/bin/env python3
"""Export client/server sync fixtures from live engine + server sim.

Usage:
    python scripts/export_client_server_sync.py

Writes:
    tests/fixtures/sync/client_server_sync.json
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game_engine.message_codes import (  # noqa: E402
    CAPTURE_CONTINUE,
    CAPTURE_CONTINUE_SAME,
    CAPTURE_MANDATORY_OTHER,
    CAPTURE_MUST_CONTINUE,
    CAPTURE_ONLY_BIY,
    MOVE_TARGET_OCCUPIED,
    TURN_NOW,
)
from tests.helpers.engine_boards import empty_board  # noqa: E402
from tests.helpers.server_game_sim import (  # noqa: E402
    client_chain_cell,
    new_server_game,
    simulate_server_replay,
    try_server_move,
)


OUT = ROOT / "tests/fixtures/sync/client_server_sync.json"


def _json_board(board: dict) -> dict:
    return {str(k): v for k, v in board.items()}


def _replay(moves: list[tuple[str, int, int]], board: dict | None = None, mover: str | None = None):
    if board is not None:
        game, last, prev = simulate_server_replay(
            moves,
            game=new_server_game(board=dict(board), mover=mover or moves[0][0]),
        )
    else:
        game, last, prev = simulate_server_replay(moves)
    return game, last, prev


def _legal(game: dict, from_cell: int, to_cell: int, *, code: str, captures: list[int] | None = None) -> dict:
    probe = deepcopy(game)
    before = dict(probe["board"])
    result = try_server_move(probe, from_cell, to_cell)
    assert result.message_code == code, f"{from_cell}->{to_cell}: {result.message_code}"
    assert probe["board"] != before, f"{from_cell}->{to_cell} did not apply"
    entry = {"from": from_cell, "to": to_cell, "code": code}
    if captures is not None:
        entry["captures"] = captures
    return entry


def _illegal_stale(game: dict, from_cell: int, to_cell: int, stale_chain: int, code: str) -> dict:
    probe = deepcopy(game)
    before = dict(probe["board"])
    result = try_server_move(probe, from_cell, to_cell, override_chain=stale_chain)
    assert result.message_code == code, f"stale {from_cell}->{to_cell}: {result.message_code}"
    assert probe["board"] == before, f"stale {from_cell}->{to_cell} mutated board"
    return {"from": from_cell, "to": to_cell, "stale_chain": stale_chain, "code": code}


def _illegal(game: dict, from_cell: int, to_cell: int, code: str) -> dict:
    probe = deepcopy(game)
    before = dict(probe["board"])
    result = try_server_move(probe, from_cell, to_cell)
    assert probe["board"] == before, f"illegal {from_cell}->{to_cell} mutated board"
    if code:
        assert result.message_code == code, f"illegal {from_cell}->{to_cell}: {result.message_code}"
    return {"from": from_cell, "to": to_cell, "code": code}


def _scenario(
    scenario_id: str,
    description: str,
    moves: list[tuple[str, int, int]],
    *,
    board: dict | None = None,
    mover: str | None = None,
    expect_mover: str,
    expect_server_pending: int | None,
    expect_delta_chain_cell: int | None = None,
    legal_moves: list[dict] | None = None,
    illegal_with_stale_chain: list[dict] | None = None,
    illegal_moves: list[dict] | None = None,
) -> dict:
    game, last, prev = _replay(moves, board, mover)
    assert game["mover"] == expect_mover
    pending = game.get("pending_mandatory_position")
    if expect_server_pending is None:
        assert pending is None
    else:
        assert pending == expect_server_pending

    if expect_delta_chain_cell is not None and moves:
        from backend.session.v2.protocol import build_move_delta  # noqa: E402

        color, f, t = moves[-1]
        delta = build_move_delta(game, last, prev, f, t, room_data={"time_control": None})
        got = delta.get("chainCell")
        assert got == expect_delta_chain_cell, f"delta chainCell {got}"

    assert client_chain_cell(game) == (expect_server_pending if expect_server_pending is not None else None)

    payload = {
        "id": scenario_id,
        "description": description,
        "moves": [[color, f, t] for color, f, t in moves],
        "mover": mover or (moves[0][0] if moves else expect_mover),
        "expect_mover": expect_mover,
        "expect_server_pending": expect_server_pending,
    }
    if board is not None:
        payload["board"] = _json_board(board)
    if expect_delta_chain_cell is not None:
        payload["expect_delta_chain_cell"] = expect_delta_chain_cell
    if legal_moves:
        payload["legal_moves"] = legal_moves
    if illegal_with_stale_chain:
        payload["illegal_with_stale_chain"] = illegal_with_stale_chain
    if illegal_moves:
        payload["illegal_moves"] = illegal_moves
    return payload


def _build_scenarios() -> list[dict]:
    scenarios: list[dict] = []

    # --- existing: long line mandatory fork (user report) ---
    moves_28 = [
        ("белый", 40, 32), ("черный", 20, 26), ("белый", 32, 20), ("черный", 12, 28),
        ("белый", 41, 34), ("черный", 28, 40), ("белый", 39, 41), ("черный", 19, 25),
        ("белый", 41, 33), ("черный", 25, 41), ("белый", 49, 33), ("черный", 9, 26),
        ("белый", 33, 19), ("черный", 11, 27), ("белый", 42, 34), ("черный", 27, 41),
        ("белый", 48, 34), ("черный", 10, 19), ("белый", 34, 26), ("черный", 18, 34),
        ("белый", 47, 40), ("черный", 21, 28), ("белый", 53, 42), ("черный", 34, 41),
        ("белый", 50, 49), ("черный", 41, 39), ("белый", 46, 32), ("черный", 28, 36),
    ]
    game, _, _ = _replay(moves_28)
    scenarios.append(_scenario(
        "user_sequence_28_white_mandatory",
        "After Black 28-36 White must capture; no single-piece chain lock at turn start",
        moves_28,
        expect_mover="белый",
        expect_server_pending=None,
        expect_delta_chain_cell=None,
        legal_moves=[
            _legal(game, 42, 30, code=TURN_NOW, captures=[36]),
            _legal(game, 43, 29, code=TURN_NOW, captures=[36]),
            _legal(game, 44, 28, code=TURN_NOW, captures=[36]),
        ],
        illegal_with_stale_chain=[
            _illegal_stale(game, 32, 36, 42, CAPTURE_CONTINUE_SAME),
            _illegal_stale(game, 43, 29, 42, CAPTURE_CONTINUE_SAME),
        ],
        illegal_moves=[
            _illegal(game, 42, 36, MOVE_TARGET_OCCUPIED),
        ],
    ))

    # --- shatra chain mid-turn ---
    board_chain = empty_board()
    board_chain.update({
        20: "белая шатра", 28: "черная шатра", 36: None, 44: "черная шатра", 45: "белая шатра",
    })
    game, _, _ = _replay([("белый", 20, 36)], board_chain, "белый")
    scenarios.append(_scenario(
        "white_shatra_double_capture_chain",
        "Mid-turn chain: pending persists while same player continues",
        [("белый", 20, 36)],
        board=board_chain,
        mover="белый",
        expect_mover="белый",
        expect_server_pending=36,
        expect_delta_chain_cell=36,
        legal_moves=[_legal(game, 36, 52, code=TURN_NOW, captures=[44])],
        illegal_with_stale_chain=[_illegal_stale(game, 45, 37, 36, CAPTURE_CONTINUE_SAME)],
    ))

    # --- single mandatory capture then turn ---
    moves_b32 = [
        ("белый", 40, 32), ("черный", 19, 25), ("белый", 41, 33), ("черный", 25, 41),
        ("белый", 42, 40), ("черный", 18, 25),
    ]
    game, _, _ = _replay(moves_b32)
    scenarios.append(_scenario(
        "black_forces_white_capture_from_32",
        "Regression: single mandatory capture then turn passes",
        moves_b32,
        expect_mover="белый",
        expect_server_pending=None,
        legal_moves=[_legal(game, 32, 18, code=TURN_NOW, captures=[25])],
    ))

    # --- black batyr chain: ghost cell blocks wrong ray ---
    board_batyr = empty_board()
    board_batyr.update({
        14: "черный батыр", 10: "белая шатра", 8: None, 5: "белая шатра", 2: None,
        21: "белая шатра", 28: None,
    })
    game, _, _ = _replay([("черный", 14, 8)], board_batyr, "черный")
    scenarios.append(_scenario(
        "black_batyr_chain_ghost_blocks_ray",
        "Batyr chain: captured cell blocks further targets on same ray",
        [("черный", 14, 8)],
        board=board_batyr,
        mover="черный",
        expect_mover="черный",
        expect_server_pending=8,
        expect_delta_chain_cell=8,
        legal_moves=[_legal(game, 8, 2, code=TURN_NOW, captures=[5])],
        illegal_with_stale_chain=[_illegal_stale(game, 21, 28, 8, CAPTURE_CONTINUE_SAME)],
        illegal_moves=[_illegal(game, 8, 28, CAPTURE_MUST_CONTINUE)],
    ))

    # --- batyr chain completes and passes turn ---
    game, _, _ = _replay([("черный", 14, 8), ("черный", 8, 2)], board_batyr, "черный")
    scenarios.append(_scenario(
        "black_batyr_chain_completes_turn",
        "Batyr finishes capture chain; pending and batyr caps cleared on turn switch",
        [("черный", 14, 8), ("черный", 8, 2)],
        board=board_batyr,
        mover="черный",
        expect_mover="белый",
        expect_server_pending=None,
        expect_delta_chain_cell=None,
    ))

    # --- batyr jump capture (61 over 55) ---
    board_61 = empty_board()
    board_61.update({61: "черный батыр", 55: "белая шатра"})
    game = new_server_game(board=board_61, mover="черный")
    scenarios.append(_scenario(
        "black_batyr_capture_61_over_55",
        "Batyr captures by jumping over enemy (land on 53, not 55)",
        [],
        board=board_61,
        mover="черный",
        expect_mover="черный",
        expect_server_pending=None,
        legal_moves=[_legal(game, 61, 53, code=TURN_NOW, captures=[55])],
        illegal_moves=[_illegal(game, 61, 55, MOVE_TARGET_OCCUPIED)],
    ))

    # --- black shatra two-hop chain ---
    board_sh = empty_board()
    board_sh.update({
        11: "черная шатра", 18: "белая шатра", 25: None, 32: "белая шатра", 20: "черная шатра",
    })
    game, _, _ = _replay([("черный", 11, 25)], board_sh, "черный")
    scenarios.append(_scenario(
        "black_shatra_capture_chain",
        "Black shatra chain: second capture from chain cell",
        [("черный", 11, 25)],
        board=board_sh,
        mover="черный",
        expect_mover="черный",
        expect_server_pending=25,
        expect_delta_chain_cell=25,
        legal_moves=[_legal(game, 25, 39, code=TURN_NOW, captures=[32])],
        illegal_with_stale_chain=[_illegal_stale(game, 20, 32, 25, CAPTURE_CONTINUE_SAME)],
    ))

    # --- only biy may move when only biy can capture ---
    board_biy = empty_board()
    board_biy.update({
        48: "белый бий", 47: "черная шатра", 46: None,
        1: "черный бий", 2: "черный бий",
    })
    game = new_server_game(board=board_biy, mover="белый")
    scenarios.append(_scenario(
        "white_biy_only_mandatory_flexible",
        "When only biy can capture, biy may take or make a quiet move",
        [],
        board=board_biy,
        mover="белый",
        expect_mover="белый",
        expect_server_pending=None,
        legal_moves=[
            _legal(game, 48, 46, code=TURN_NOW, captures=[47]),
            _legal(game, 48, 40, code=TURN_NOW, captures=[]),
        ],
    ))

    # --- batyr + biy mandatory: wrong piece blocked ---
    board_multi = empty_board()
    board_multi.update({
        35: "белый батыр", 49: "черная шатра", 53: None,
        19: "белый бий", 13: "черная шатра", 52: "белая шатра",
        1: "черный бий", 2: "черный бий",
    })
    game = new_server_game(board=board_multi, mover="белый")
    scenarios.append(_scenario(
        "white_batyr_and_biy_mandatory_fork",
        "Multiple mandatory attackers at turn start; wrong piece rejected",
        [],
        board=board_multi,
        mover="белый",
        expect_mover="белый",
        expect_server_pending=None,
        legal_moves=[
            _legal(game, 35, 53, code=TURN_NOW, captures=[49]),
            _legal(game, 19, 10, code=TURN_NOW, captures=[13]),
        ],
        illegal_moves=[_illegal(game, 52, 45, CAPTURE_MANDATORY_OTHER)],
    ))

    # --- shatra promotion on quiet move ---
    board_promo = empty_board()
    board_promo.update({53: "белая шатра", 45: None})
    game, _, _ = _replay([("белый", 53, 45)], board_promo, "белый")
    scenarios.append(_scenario(
        "white_shatra_promotion_to_batyr",
        "Shatra promotes to batyr when entering promotion row without capture",
        [("белый", 53, 45)],
        board=board_promo,
        mover="белый",
        expect_mover="черный",
        expect_server_pending=None,
        legal_moves=[],
    ))

    return scenarios


def main() -> None:
    scenarios = _build_scenarios()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "generated_by": "scripts/export_client_server_sync.py",
        "scenarios": scenarios,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(scenarios)} scenarios)")


if __name__ == "__main__":
    main()
