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
    user.rating = 1625
    meta = meta_from_user(user)
    assert meta["username"] == "Player1"
    assert meta["is_anonymous"] is False
    assert meta["rating"] == 1625


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
            "c1": {"username": "alice", "is_anonymous": False, "rating": 1542},
            "c2": {"username": None, "is_anonymous": True},
        },
    }
    info = build_players_info(room)
    assert len(info) == 2
    assert info[0]["display_name"] == "alice"
    assert info[0]["rating"] == 1542
    assert info[1]["display_name"] == "Аноним"
    assert "rating" not in info[1]


@pytest.mark.asyncio
async def test_refresh_player_ratings_in_room():
    from unittest.mock import AsyncMock, MagicMock

    from backend.player_identity import refresh_player_ratings_in_room

    uid = uuid.uuid4()
    room = {
        "player_meta": {
            "c1": {
                "user_id": str(uid),
                "username": "alice",
                "is_anonymous": False,
                "rating": 1500,
            },
        },
    }
    user = MagicMock()
    user.id = uid
    user.username = "alice"
    user.rating = 1633

    db = AsyncMock()
    db.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[user])))

    await refresh_player_ratings_in_room(room, db)
    assert room["player_meta"]["c1"]["rating"] == 1633


@pytest.mark.asyncio
async def test_refresh_pvp_ratings_skips_ai_room():
    from backend.player_identity import refresh_pvp_ratings_for_room

    room = {
        "type": "ai",
        "player_meta": {
            "c1": {
                "user_id": str(uuid.uuid4()),
                "username": "solo",
                "is_anonymous": False,
                "rating": 1500,
            },
        },
    }
    snapshot = {k: dict(v) for k, v in room["player_meta"].items()}
    await refresh_pvp_ratings_for_room(room)
    assert room["player_meta"] == snapshot


@pytest.mark.asyncio
async def test_refresh_pvp_ratings_for_room_loads_db():
    from backend.db.models import User
    from backend.db.session import get_session_factory
    from backend.player_identity import refresh_pvp_ratings_for_room

    uid = uuid.uuid4()
    factory = get_session_factory()
    async with factory() as session:
        session.add(
            User(
                id=uid,
                username=f"refresh_{uid.hex[:8]}",
                username_normalized=f"refresh_{uid.hex[:8]}",
                password_hash="hash",
                rating=1711,
            )
        )
        await session.commit()

    room = {
        "type": "public",
        "player_meta": {
            "c1": {
                "user_id": str(uid),
                "username": "alice",
                "is_anonymous": False,
                "rating": 1200,
            },
        },
    }
    await refresh_pvp_ratings_for_room(room)
    assert room["player_meta"]["c1"]["rating"] == 1711


@pytest.mark.asyncio
async def test_create_room_with_user_sets_creator():
    user = MagicMock()
    user.id = "11111111-1111-1111-1111-111111111111"
    user.username = "creator"
    stored = {}

    async def fake_set(room_id, data):
        stored[room_id] = data

    req = CreateRoomRequest(type="public", creator_client_id="client-abc")
    with (
        patch("backend.room_manager.set_room", side_effect=fake_set),
        patch("backend.room_manager.add_waiting_public_room", AsyncMock()),
    ):
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
    with (
        patch("backend.room_manager.set_room", side_effect=fake_set),
        patch("backend.room_manager.add_waiting_public_room", AsyncMock()),
    ):
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
