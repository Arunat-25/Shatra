"""Общие фикстуры для тестов Shatra."""

import pytest

from backend.board_utils import get_starting_board


@pytest.fixture
def starting_board():
    return get_starting_board()


@pytest.fixture
def sample_room_data():
    return {
        "room_id": "abcd1234",
        "type": "public",
        "game_started": False,
        "creator_client_id": "creator-1",
        "creator_color_preference": "белый",
        "time_control": 300,
        "increment": 5,
        "timer_white": 300.0,
        "timer_black": 300.0,
        "players": {},
    }


@pytest.fixture
def game_in_progress(starting_board):
    return {
        "board": starting_board,
        "mover": "белый",
        "game_over": False,
        "move_history": [],
        "pending_batyr_captures": [],
        "position_history": {},
        "moves_with_two_biys": 0,
    }
