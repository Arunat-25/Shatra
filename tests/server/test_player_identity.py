"""Тесты идентификации игроков в комнатах."""

import pytest

from backend.models import CreateRoomRequest
from backend.player_identity import build_players_info, meta_from_user
from backend.room_manager import create_room
from unittest.mock import MagicMock, patch


def test_meta_from_user_anonymous():
    assert meta_from_user(None)["is_anonymous"] is True


def test_meta_from_user_authenticated():
    user = MagicMock()
    user.id = "uuid-1"
    user.username = "Player1"
    meta = meta_from_user(user)
    assert meta["username"] == "Player1"
    assert meta["is_anonymous"] is False


def test_build_players_info():
    room = {
        "players": {"c1": "белый", "c2": "черный"},
        "player_meta": {
            "c1": {"username": "alice", "is_anonymous": False},
            "c2": {"username": None, "is_anonymous": True},
        },
    }
    info = build_players_info(room)
    assert len(info) == 2
    assert info[0]["display_name"] == "alice"
    assert info[1]["display_name"] == "Аноним"


@pytest.mark.asyncio
async def test_create_room_with_user_sets_creator():
    user = MagicMock()
    user.id = "11111111-1111-1111-1111-111111111111"
    user.username = "creator"
    stored = {}

    async def fake_set(room_id, data):
        stored[room_id] = data

    req = CreateRoomRequest(type="public", creator_client_id="client-abc")
    with patch("backend.room_manager.set_room", side_effect=fake_set):
        result = await create_room(req, user=user)
    room = stored[result["room_id"]]
    assert room["creator_username"] == "creator"
    assert room["player_meta"]["client-abc"]["username"] == "creator"


@pytest.mark.asyncio
async def test_create_room_without_user_anonymous_creator():
    stored = {}

    async def fake_set(room_id, data):
        stored[room_id] = data

    req = CreateRoomRequest(type="public", creator_client_id="guest-1")
    with patch("backend.room_manager.set_room", side_effect=fake_set):
        result = await create_room(req, user=None)
    room = stored[result["room_id"]]
    assert room.get("creator_username") is None
    assert room["player_meta"]["guest-1"]["is_anonymous"] is True
