"""Contract fixtures stay in sync with game_engine."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from game_engine.game_logic import logic
from game_engine.models import GameEvent
from game_engine.moves import process_move
from tests.helpers.engine_boards import hint_at

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "tests/fixtures/rules/contract.json"
EXPORT = ROOT / "scripts/export_rules_contract.py"


def test_contract_file_exists():
    assert CONTRACT.is_file()


def test_export_script_runs():
    subprocess.run(
        [sys.executable, str(EXPORT)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_contract_cases_match_python_engine():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    for case in data["cases"]:
        action = case["action"]
        board = {int(k): v for k, v in action["board"].items()}
        expect = case["expect"]

        if action["type"] == "hints":
            result = hint_at(
                board,
                action["mover_color"],
                action["from_cell"],
                pending=action.get("chain_capture_cell"),
                batyr_caps=action.get("batyr_captured_this_turn") or [],
            )
            assert sorted(result.essential_positions or []) == expect["essential_positions"]
            assert (result.message_code or "") == (expect.get("message_code") or "")
            continue

        if action["type"] == "move":
            result = process_move(
                board,
                action["mover_color"],
                action["from_cell"],
                action["to_cell"],
                chain_capture_cell=action.get("chain_capture_cell"),
                batyr_captured_this_turn=action.get("batyr_captured_this_turn") or [],
            )
            assert (result.message_code or "") == (expect.get("message_code") or "")
            assert result.movers_color == expect.get("movers_color")
            assert result.position_for_mandatory_capture == expect.get(
                "position_for_mandatory_capture"
            )
            assert sorted(result.captured_positions or []) == expect.get(
                "captured_positions", []
            )
            assert list(result.captured_pieces or []) == expect.get("captured_pieces", [])
            assert bool(result.opportunity_pass_the_move) == expect.get(
                "opportunity_pass_the_move", False
            )
            if "desk" in expect:
                expected_desk = {int(k): v for k, v in expect["desk"].items()}
                assert result.updated_positions == expected_desk
            continue

        raise AssertionError(f"unknown contract action type: {action['type']}")
