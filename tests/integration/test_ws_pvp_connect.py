"""PvP identity: real Redis + manager.connect + archive (без TestClient WS deadlock)."""

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

import tests.test_env  # noqa: F401

from backend.models import CreateRoomRequest
from backend.room_manager import create_room
from backend.ws_manager import handle_player2_join, manager
from main import app
from tests.db.conftest import db_fetchone, register
from tests.integration.helpers import (
    assert_finished_game_row,
    new_client_id,
    read_room_json,
)

pytestmark = pytest.mark.integration


def _register_pair() -> tuple[dict, dict]:
    with TestClient(app) as client:
        host = register(client, f"pvp_host_{uuid.uuid4().hex[:8]}")
        guest = register(client, f"pvp_guest_{uuid.uuid4().hex[:8]}")
    return (
        {
            "user_id": host["user"]["id"],
            "access_token": host["access_token"],
            "client_id": new_client_id(),
        },
        {
            "user_id": guest["user"]["id"],
            "access_token": guest["access_token"],
            "client_id": new_client_id(),
        },
    )


async def _connect_player(room_id: str, client_id: str, user: dict | None):
    from unittest.mock import AsyncMock

    from backend.db.models import User
    from backend.db.session import get_session_factory

    ws = AsyncMock()
    ws.accept = AsyncMock()
    db_user = None
    if user and user.get("user_id"):
        factory = get_session_factory()
        async with factory() as session:
            db_user = await session.get(User, uuid.UUID(user["user_id"]))
    ok = await manager.connect(room_id, ws, client_id, user=db_user)
    assert ok is True
    return ws


async def _run_pvp_scenario(
    *,
    room_type: str,
    host: dict,
    guest: dict | None,
    guest_client_id: str | None = None,
    resign_client_id: str | None = None,
):
    from backend.db.models import User
    from backend.db.session import get_session_factory
    from backend.game_archive import archive_finished_game
    from backend.state import close_redis, init_redis
    from backend.ws_control_handlers import handle_resign
    from unittest.mock import AsyncMock

    await init_redis()
    try:
        factory = get_session_factory()
        async with factory() as session:
            host_user = await session.get(User, uuid.UUID(host["user_id"]))

        result = await create_room(
            CreateRoomRequest(type=room_type, creator_client_id=host["client_id"]),
            user=host_user,
        )
        room_id = result["room_id"]

        await _connect_player(room_id, host["client_id"], host)
        guest_id = guest_client_id or (guest["client_id"] if guest else None)
        assert guest_id is not None
        await _connect_player(room_id, guest_id, guest)

        room_data = read_room_json(room_id)
        assert room_data["player_meta"][host["client_id"]]["user_id"] == host["user_id"]
        if guest:
            assert room_data["player_meta"][guest["client_id"]]["user_id"] == guest["user_id"]

        await handle_player2_join(room_id, room_data)
        resign_id = resign_client_id or host["client_id"]
        ws = AsyncMock()
        await handle_resign(room_id, resign_id, ws, is_ai_room=False)
        await archive_finished_game(room_id)
        manager.connections.pop(room_id, None)
        return room_id
    finally:
        await close_redis()


def test_public_both_authenticated():
    host, guest = _register_pair()

    room_id = asyncio.run(
        _run_pvp_scenario(room_type="public", host=host, guest=guest)
    )

    row = assert_finished_game_row(db_fetchone, room_id, room_type="public")
    user_ids = {str(row[1]) if row[1] else None, str(row[2]) if row[2] else None}
    assert user_ids == {host["user_id"], guest["user_id"]}


def test_public_host_auth_guest_anonymous():
    host, _guest = _register_pair()
    guest_id = "guest-anon-direct"

    room_id = asyncio.run(
        _run_pvp_scenario(
            room_type="public",
            host=host,
            guest=None,
            guest_client_id=guest_id,
            resign_client_id=guest_id,
        )
    )

    row = assert_finished_game_row(db_fetchone, room_id, room_type="public")
    assert host["user_id"] in {
        str(row[1]) if row[1] else None,
        str(row[2]) if row[2] else None,
    }
    assert True in {row[3], row[4]} and False in {row[3], row[4]}


def test_private_both_friends():
    host, guest = _register_pair()

    room_id = asyncio.run(
        _run_pvp_scenario(room_type="private", host=host, guest=guest)
    )

    row = assert_finished_game_row(db_fetchone, room_id, room_type="private")
    user_ids = {str(row[1]) if row[1] else None, str(row[2]) if row[2] else None}
    assert user_ids == {host["user_id"], guest["user_id"]}
