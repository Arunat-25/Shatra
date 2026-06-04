"""Tests for WebSocket presence hooks."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from backend.db.session import get_session_factory
from backend.db.models import PresenceSession
from backend.ws_manager import manager
from sqlalchemy import select


@pytest.mark.asyncio
class TestPresenceHooks:
    async def test_connect_starts_presence_session(self):
        room_id = "pres01"
        client_id = "client-presence-1"
        ws = AsyncMock()
        room_data = {
            "room_id": room_id,
            "type": "public",
            "players": {},
            "player_meta": {},
        }

        async def get_room(rid):
            return room_data if rid == room_id else None

        async def set_room(rid, data):
            room_data.update(data)

        with (
            patch("backend.ws_manager.get_room", side_effect=get_room),
            patch("backend.ws_manager.set_room", side_effect=set_room),
        ):
            ok = await manager.connect(room_id, ws, client_id, user=None)

        assert ok is True
        factory = get_session_factory()
        async with factory() as session:
            rows = list((await session.scalars(select(PresenceSession))).all())
        assert len(rows) == 1
        assert rows[0].client_id == client_id
        assert rows[0].is_anonymous is True
        manager.connections.pop(room_id, None)

    async def test_connect_without_token_preserves_user_id_from_player_meta(self, client):
        """Presence user_id берётся из merged meta, не только из JWT на WS."""
        from tests.db.conftest import register

        reg = register(client, "presence_meta_user")
        user_id = reg["user"]["id"]
        room_id = "pres03"
        client_id = "client-presence-auth"
        ws = AsyncMock()
        room_data = {
            "room_id": room_id,
            "type": "ai",
            "creator_client_id": client_id,
            "creator_color_preference": "random",
            "players": {},
            "player_meta": {
                client_id: {
                    "user_id": user_id,
                    "username": "presence_meta_user",
                    "is_anonymous": False,
                },
            },
        }

        async def get_room(rid):
            return room_data if rid == room_id else None

        async def set_room(rid, data):
            room_data.update(data)

        with (
            patch("backend.ws_manager.get_room", side_effect=get_room),
            patch("backend.ws_manager.set_room", side_effect=set_room),
        ):
            ok = await manager.connect(room_id, ws, client_id, user=None)

        assert ok is True
        factory = get_session_factory()
        async with factory() as session:
            rows = list((await session.scalars(select(PresenceSession))).all())
        assert len(rows) == 1
        assert rows[0].user_id == uuid.UUID(user_id)
        assert rows[0].is_anonymous is False
        manager.connections.pop(room_id, None)

    async def test_disconnect_ends_presence_session(self):
        room_id = "pres02"
        client_id = "client-presence-2"
        ws = AsyncMock()
        room_data = {
            "room_id": room_id,
            "type": "public",
            "players": {client_id: "белый"},
            "player_meta": {client_id: {"is_anonymous": True}},
        }
        manager.connections[room_id] = {client_id: ws}

        async def get_room(rid):
            return room_data if rid == room_id else None

        with (
            patch("backend.ws_manager.get_room", side_effect=get_room),
            patch("backend.ws_manager.set_room", AsyncMock()),
            patch("backend.ws_manager.start_session", new_callable=AsyncMock) as start_mock,
            patch("backend.ws_manager.end_session", new_callable=AsyncMock) as end_mock,
        ):
            await manager.disconnect(room_id, ws)

        end_mock.assert_called_once_with(client_id)
        manager.connections.pop(room_id, None)
