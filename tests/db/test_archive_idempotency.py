"""Archive idempotency: room lock + unique (room_id, started_at)."""

import asyncio
from unittest.mock import patch

import pytest

from backend.board_utils import get_starting_board, keys_int_to_str
from backend.game_archive import archive_finished_game
from tests.db.conftest import db_scalar
from tests.db.test_persistence import _finished_game, _room


class ArchiveStub:
    def __init__(self, room_id: str, game: dict, room: dict):
        self.room_id = room_id
        self.game = game
        self.room = room

    async def get_game(self, room_id: str):
        return self.game if room_id == self.room_id else None

    async def get_room(self, room_id: str):
        return self.room if room_id == self.room_id else None

    async def set_game(self, room_id: str, game: dict):
        if room_id == self.room_id:
            self.game = game


@pytest.mark.asyncio
async def test_parallel_archive_creates_single_row():
    room_id = "paral001"
    stub = ArchiveStub(room_id, _finished_game(), _room(room_id))
    patches = (
        patch("backend.game_archive.get_game", side_effect=stub.get_game),
        patch("backend.game_archive.get_room", side_effect=stub.get_room),
        patch("backend.game_archive.set_game", side_effect=stub.set_game),
    )
    with patches[0], patches[1], patches[2]:
        results = await asyncio.gather(
            archive_finished_game(room_id),
            archive_finished_game(room_id),
        )
    assert sum(1 for r in results if r is not None) == 1
    assert db_scalar(
        "SELECT COUNT(*) FROM finished_games WHERE room_id = %s", (room_id,)
    ) == 1


@pytest.mark.asyncio
async def test_second_archive_after_archived_flag_is_noop():
    room_id = "noop0001"
    stub = ArchiveStub(room_id, _finished_game(), _room(room_id))
    with (
        patch("backend.game_archive.get_game", side_effect=stub.get_game),
        patch("backend.game_archive.get_room", side_effect=stub.get_room),
        patch("backend.game_archive.set_game", side_effect=stub.set_game),
    ):
        first = await archive_finished_game(room_id)
        second = await archive_finished_game(room_id)
    assert first is not None
    assert second is None
    assert db_scalar(
        "SELECT COUNT(*) FROM finished_games WHERE room_id = %s", (room_id,)
    ) == 1
