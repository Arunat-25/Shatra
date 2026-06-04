"""Contract tests for shared test DB helpers."""

import pytest

from tests.helpers.finished_games import insert_finished_game


def test_insert_finished_game_requires_keyword_args():
    with pytest.raises(TypeError, match="positional"):
        insert_finished_game("room-id")
