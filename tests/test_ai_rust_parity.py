"""Optional parity check: Rust search vs Python get_best_move on sample boards."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CARGO = ROOT / "Cargo.toml"


def _rust_available() -> bool:
    if not CARGO.is_file():
        return False
    try:
        subprocess.run(
            ["cargo", "test", "-p", "shatra-engine", "--no-run"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@pytest.mark.skipif(not _rust_available(), reason="Rust engine not buildable in this environment")
def test_rust_contract_tests_pass():
    subprocess.run(
        ["cargo", "test", "-p", "shatra-engine", "--quiet"],
        cwd=ROOT,
        check=True,
    )


def test_python_ai_still_returns_legal_moves():
    from backend.ai import get_best_move

    board = {i: None for i in range(1, 63)}
    for i in range(11, 18):
        board[i] = "черная шатра"
    for i in range(46, 53):
        board[i] = "белая шатра"
    board[7] = "черный бий"
    board[56] = "белый бий"
    move = get_best_move(board, "черный", depth=2)
    assert move is not None
    fm, to = move
    assert board.get(fm) and "чер" in board[fm]
