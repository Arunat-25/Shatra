"""Тесты идентификации игроков в комнатах."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.game_archive import _side_for_color
from backend.models import CreateRoomRequest
from backend.player_identity import build_players_info, merge_player_meta, meta_from_user
from backend.room_manager import create_room
from backend.ws_manager import manager


def test_meta_from_user_anonymous():
    assert meta_from_user(None)["is_anonymous"] is True


def test_meta_from_user_authenticated():
    user = MagicMock()
    user.id = "uuid-1"
    user.username = "Player1"
    meta = meta_from_user(user)
    assert meta["username"] == "Player1"
    assert meta["is_anonymous"] is False


def test_merge_player_meta_preserves_auth_when_ws_has_no_user():
    existing = meta_from_user(MagicMock(id=uuid.uuid4(), username="solo"))
    merged = merge_player_meta(existing, None)
    assert merged["username"] == "solo"
    assert merged["is_anonymous"] is False


def test_merge_player_meta_token_overrides_anonymous():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "logged_in"
    merged = merge_player_meta(meta_from_user(None), user)
    assert merged["username"] == "logged_in"
    assert merged["is_anonymous"] is False


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


@pytest.mark.asyncio
async def test_ws_connect_without_token_preserves_creator_meta_for_ai_archive():
    """Регрессия: REST create с JWT + WS без access_token → finished_games с user_id."""
    user_id = uuid.uuid4()
    client_id = "host-client"
    room_id = str(uuid.uuid4())
    room_data = {
        "room_id": room_id,
        "type": "ai",
        "creator_client_id": client_id,
        "players": {},
        "player_meta": {
            client_id: {
                "user_id": str(user_id),
                "username": "solo",
                "is_anonymous": False,
            }
        },
        "color_preference": "random",
    }
    stored: dict[str, dict] = {}

    async def fake_get_room(rid):
        return dict(room_data) if rid == room_id else None

    async def fake_set_room(rid, data):
        stored[rid] = data

    ws = AsyncMock()

    with (
        patch("backend.ws_manager.get_room", side_effect=fake_get_room),
        patch("backend.ws_manager.set_room", side_effect=fake_set_room),
        patch("backend.ws_manager.start_session", new_callable=AsyncMock),
    ):
        ok = await manager.connect(room_id, ws, client_id, user=None)

    assert ok is True
    saved = stored[room_id]
    side = _side_for_color(saved, saved["players"][client_id])
    assert side["user_id"] == user_id
    assert side["username"] == "solo"
    assert side["is_anonymous"] is False
