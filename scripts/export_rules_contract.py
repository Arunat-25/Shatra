#!/usr/bin/env python3
"""Export game_engine dictionaries and contract fixtures for client rules (Variant F).

Usage:
    python scripts/export_rules_contract.py

Writes:
    frontend/packages/shatra-rules/src/dictionaries.json
    tests/fixtures/rules/contract.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game_engine.moves import process_move  # noqa: E402
from game_engine import dictionaries as dict_mod  # noqa: E402
from tests.helpers.engine_boards import empty_board, play_sequence, hint_at  # noqa: E402


DICT_OUT = ROOT / "frontend/packages/shatra-rules/src/dictionaries.json"
CONTRACT_OUT = ROOT / "tests/fixtures/rules/contract.json"


def _json_board(board: dict) -> dict:
    return {str(k): v for k, v in board.items()}


def _export_dictionaries() -> None:
    payload = {
        "black_shatra_possible_moves": dict_mod.black_shatra_possible_moves,
        "white_shatra_possible_moves": dict_mod.white_shatra_possible_moves,
        "black_biy_possible_moves": dict_mod.black_biy_possible_moves,
        "white_biy_possible_moves": dict_mod.white_biy_possible_moves,
        "shatra_and_biy_possible_captures": dict_mod.shatra_and_biy_possible_captures,
        "batyr_moves_and_captures": dict_mod.batyr_moves_and_captures,
    }
    # JSON keys must be strings; nested capture maps too
    def norm(obj):
        if isinstance(obj, dict):
            return {str(k): norm(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [norm(x) for x in obj]
        return obj

    DICT_OUT.parent.mkdir(parents=True, exist_ok=True)
    DICT_OUT.write_text(
        json.dumps(norm(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _hint_case(case_id: str, board: dict, color: str, from_cell: int, **kwargs) -> dict:
    pending = kwargs.get("pending")
    batyr_caps = kwargs.get("batyr_caps") or []
    result = hint_at(
        board,
        color,
        from_cell,
        pending=pending,
        batyr_caps=batyr_caps,
    )
    expect: dict = {
        "essential_positions": sorted(result.essential_positions or []),
        "message_code": result.message_code or "",
    }
    if result.captured_pieces is not None:
        expect["captured_pieces"] = list(result.captured_pieces)
    return {
        "id": case_id,
        "action": {
            "type": "hints",
            "board": _json_board(board),
            "mover_color": color,
            "from_cell": from_cell,
            "chain_capture_cell": pending,
            "batyr_captured_this_turn": batyr_caps,
        },
        "expect": expect,
    }


def _move_case(case_id: str, board: dict, color: str, from_cell: int, to_cell: int, **kwargs) -> dict:
    pending = kwargs.get("pending")
    batyr_caps = kwargs.get("batyr_caps") or []
    result = process_move(
        board,
        color,
        from_cell,
        to_cell,
        chain_capture_cell=pending,
        batyr_captured_this_turn=batyr_caps,
    )
    expect: dict = {
        "message_code": result.message_code or "",
        "movers_color": result.movers_color,
        "position_for_mandatory_capture": result.position_for_mandatory_capture,
        "captured_positions": sorted(result.captured_positions or []),
        "captured_pieces": list(result.captured_pieces or []),
        "opportunity_pass_the_move": bool(result.opportunity_pass_the_move),
    }
    if result.updated_positions is not None:
        expect["desk"] = _json_board(result.updated_positions)
    return {
        "id": case_id,
        "action": {
            "type": "move",
            "board": _json_board(board),
            "mover_color": color,
            "from_cell": from_cell,
            "to_cell": to_cell,
            "chain_capture_cell": pending,
            "batyr_captured_this_turn": batyr_caps,
        },
        "expect": expect,
    }


def _build_contract_cases() -> list[dict]:
    cases: list[dict] = []

    # --- basic hints (test_game_logic) ---
    b = empty_board()
    b[11] = "черная шатра"
    cases.append(_hint_case("black_shatra_from_11", b, "черный", 11))

    b = empty_board()
    b[11] = "черная шатра"
    cases.append(_hint_case("wrong_color_empty_hints", b, "белый", 11))

    # --- mandatory / chain (test_hints_mandatory) ---
    b = empty_board()
    b[11] = "черная шатра"
    b[18] = "белая шатра"
    b[25] = None
    b[32] = "белая шатра"
    b[20] = "черная шатра"
    state = play_sequence([("черный", 11, 25)], board=b)
    cases.append(
        _hint_case(
            "chain_from_25",
            state["board"],
            "черный",
            25,
            pending=state["pending"],
            batyr_caps=state["batyr_caps"],
        )
    )
    cases.append(
        _hint_case(
            "chain_other_piece_empty",
            state["board"],
            "черный",
            20,
            pending=state["pending"],
            batyr_caps=state["batyr_caps"],
        )
    )

    b = empty_board()
    b[20] = "белая шатра"
    b[28] = "черная шатра"
    b[36] = None
    b[48] = "белый бий"
    b[47] = "черная шатра"
    b[52] = "белая шатра"
    cases.append(_hint_case("mandatory_shatra_blocked", b, "белый", 52))
    cases.append(_hint_case("mandatory_biy_must_move", b, "белый", 48))

    b = empty_board()
    b[14] = "черная шатра"
    b[10] = "белая шатра"
    b[8] = None
    cases.append(_hint_case("chain_no_fortress_capture", b, "черный", 14, pending=14))

    # --- capture fork ---
    b = empty_board()
    b[20] = "белая шатра"
    b[28] = "черная шатра"
    cases.append(_hint_case("white_capture_hints_20", b, "белый", 20))

    # --- moves (process_move) ---
    b = empty_board()
    b[20] = "белая шатра"
    b[28] = "черная шатра"
    b[36] = None
    cases.append(_move_case("white_shatra_capture_20_36", b, "белый", 20, 36))

    b = empty_board()
    b[11] = "черная шатра"
    b[18] = "белая шатра"
    b[25] = None
    b[32] = "белая шатра"
    state = play_sequence([("черный", 11, 25)], board=b)
    cases.append(
        _move_case(
            "black_chain_second_capture",
            state["board"],
            "черный",
            25,
            39,
            pending=state["pending"],
            batyr_caps=state["batyr_caps"],
        )
    )

    b = empty_board()
    b[53] = "белая шатра"
    b[45] = None
    cases.append(_move_case("white_shatra_quiet_move", b, "белый", 53, 45))

    return cases


def main() -> None:
    _export_dictionaries()
    cases = _build_contract_cases()
    CONTRACT_OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "generated_by": "scripts/export_rules_contract.py",
        "cases": cases,
    }
    CONTRACT_OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {DICT_OUT.relative_to(ROOT)}")
    print(f"Wrote {CONTRACT_OUT.relative_to(ROOT)} ({len(cases)} cases)")


if __name__ == "__main__":
    main()
