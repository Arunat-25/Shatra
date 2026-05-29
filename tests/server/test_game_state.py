"""Тесты Pydantic-модели GameState."""

import pytest

from backend.game_state import GameState
from backend.board_utils import get_starting_board


def test_new_game_has_starting_board():
    gs = GameState.new(get_starting_board())
    assert gs.mover == "белый"
    assert gs.board[10] == "черный бий"
    assert gs.game_over is False


def test_from_storage_normalizes_string_keys():
    gs = GameState.from_storage({
        "board": {"10": "черный бий", "53": "белый бий"},
        "mover": "белый",
    })
    assert gs.board[10] == "черный бий"
    assert gs.board[53] == "белый бий"


def test_roundtrip_storage():
    gs = GameState.new(get_starting_board())
    restored = GameState.from_storage(gs.to_storage())
    assert restored.board[10] == gs.board[10]
    assert restored.mover == gs.mover


def test_extra_fields_preserved():
    gs = GameState.from_storage({
        "board": {"10": "черный бий"},
        "mover": "белый",
        "custom_flag": True,
    })
    dumped = gs.to_storage()
    assert dumped.get("custom_flag") is True
