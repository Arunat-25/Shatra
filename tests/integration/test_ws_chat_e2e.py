"""E2E: PvP chat over WebSocket."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.models import CreateRoomRequest
from backend.room_manager import create_room
from backend.session.messages import process_client_message
from backend.ws_manager import handle_player2_join, manager
from main import app
from tests.db.conftest import register
from tests.integration.helpers import (
    flush_redis,
    new_client_id,
    read_room_json,
)

pytestmark = pytest.mark.integration


def _register_pair(client) -> tuple[dict, dict]:
    host = register(client, f"chat_host_{uuid.uuid4().hex[:6]}")
    guest = register(client, f"chat_guest_{uuid.uuid4().hex[:6]}")
    return (
        {
            "user_id": host["user"]["id"],
            "access_token": host["access_token"],
            "client_id": new_client_id(),
            "username": host["user"]["username"],
        },
        {
            "user_id": guest["user"]["id"],
            "access_token": guest["access_token"],
            "client_id": new_client_id(),
            "username": guest["user"]["username"],
        },
    )


async def _pvp_chat_setup(host: dict, guest: dict):
    from backend.db.models import User
    from backend.db.session import get_session_factory
    from backend.state import close_redis, init_redis

    await init_redis()
    factory = get_session_factory()
    async with factory() as session:
        host_user = await session.get(User, uuid.UUID(host["user_id"]))
        guest_user = await session.get(User, uuid.UUID(guest["user_id"]))

    result = await create_room(
        CreateRoomRequest(type="public", creator_client_id=host["client_id"]),
        user=host_user,
    )
    room_id = result["room_id"]

    host_ws = AsyncMock()
    guest_ws = AsyncMock()
    host_sent: list = []
    guest_sent: list = []

    async def host_send(payload):
        host_sent.append(payload)

    async def guest_send(payload):
        guest_sent.append(payload)

    host_ws.send_json = host_send
    guest_ws.send_json = guest_send

    assert await manager.connect(room_id, host_ws, host["client_id"], user=host_user)
    assert await manager.connect(room_id, guest_ws, guest["client_id"], user=guest_user)
    room_data = read_room_json(room_id)
    await handle_player2_join(room_id, room_data)
    return room_id, host_ws, guest_ws, host_sent, guest_sent, close_redis


class TestWsChatManagerE2E:
    def test_bidirectional_chat(self):
        with TestClient(app) as client:
            host, guest = _register_pair(client)

        async def run():
            room_id, host_ws, guest_ws, host_sent, guest_sent, close = await _pvp_chat_setup(
                host, guest
            )
            try:
                await process_client_message(
                    room_id, host["client_id"], {"type": "chat", "text": "hello guest"},
                    host_ws, is_ai_room=False,
                )
                await process_client_message(
                    room_id, guest["client_id"], {"type": "chat", "text": "hello host"},
                    guest_ws, is_ai_room=False,
                )
                return room_id, host_sent, guest_sent
            finally:
                manager.connections.clear()
                flush_redis()
                await close()

        room_id, host_sent, guest_sent = asyncio.run(run())
        assert any(m.get("text") == "hello guest" for m in guest_sent if m.get("type") == "chat")
        assert any(m.get("text") == "hello host" for m in host_sent if m.get("type") == "chat")

    def test_sanitize_stored_clean(self):
        with TestClient(app) as client:
            host, guest = _register_pair(client)

        async def run():
            room_id, host_ws, guest_ws, _, _, close = await _pvp_chat_setup(host, guest)
            try:
                await process_client_message(
                    room_id, host["client_id"], {"type": "chat", "text": "<b>clean</b>"},
                    host_ws, is_ai_room=False,
                )
                msgs = read_room_json(room_id).get("chat_messages") or []
                return msgs[-1]["text"]
            finally:
                manager.connections.clear()
                flush_redis()
                await close()

        assert asyncio.run(run()) == "clean"

    def test_duplicate_rejected(self):
        with TestClient(app) as client:
            host, guest = _register_pair(client)

        async def run():
            room_id, host_ws, guest_ws, host_sent, _, close = await _pvp_chat_setup(
                host, guest
            )
            try:
                await process_client_message(
                    room_id, host["client_id"], {"type": "chat", "text": "same"},
                    host_ws, is_ai_room=False,
                )
                await process_client_message(
                    room_id, host["client_id"], {"type": "chat", "text": "same"},
                    host_ws, is_ai_room=False,
                )
                return host_sent
            finally:
                manager.connections.clear()
                flush_redis()
                await close()

        host_sent = asyncio.run(run())
        assert any(m.get("message_code") == "chat.duplicate" for m in host_sent)

    def test_rate_limit_pvp(self):
        with TestClient(app) as client:
            host, guest = _register_pair(client)

        async def run():
            room_id, host_ws, guest_ws, host_sent, _, close = await _pvp_chat_setup(
                host, guest
            )
            try:
                with patch("backend.chat._too_soon", return_value=False):
                    with patch("backend.chat._check_rate_limit", new=AsyncMock(side_effect=[True] * 5 + [False])):
                        for i in range(5):
                            await process_client_message(
                                room_id, host["client_id"], {"type": "chat", "text": f"m{i}"},
                                host_ws, is_ai_room=False,
                            )
                        await process_client_message(
                            room_id, host["client_id"], {"type": "chat", "text": "overflow"},
                            host_ws, is_ai_room=False,
                        )
                return host_sent
            finally:
                manager.connections.clear()
                flush_redis()
                await close()

        host_sent = asyncio.run(run())
        assert any(m.get("message_code") == "chat.rate_limit" for m in host_sent)

    def test_empty_message_error(self):
        ws = AsyncMock()
        sent: list = []

        async def capture(payload):
            sent.append(payload)

        ws.send_json = capture

        async def run():
            from backend.state import close_redis, init_redis

            await init_redis()
            try:
                with patch("backend.chat.get_room", new=AsyncMock(return_value={"chat_messages": [], "player_meta": {}})):
                    await process_client_message(
                        "room1", "c1", {"type": "chat", "text": "   "}, ws, is_ai_room=False
                    )
            finally:
                await close_redis()
            return sent

        sent = asyncio.run(run())
        assert any(m.get("message_code") == "chat.empty" for m in sent)

    def test_ai_room_chat_unavailable(self):
        ws = AsyncMock()
        sent: list = []

        async def capture(payload):
            sent.append(payload)

        ws.send_json = capture

        async def run():
            from backend.state import close_redis, init_redis

            await init_redis()
            try:
                await process_client_message(
                    "room1", "c1", {"type": "chat", "text": "hi"}, ws, is_ai_room=True
                )
            finally:
                await close_redis()
            return sent

        sent = asyncio.run(run())
        assert any(m.get("message_code") == "chat.ai_unavailable" for m in sent)


@pytest.fixture(autouse=True)
def _flush():
    flush_redis()
    yield
    flush_redis()
    manager.connections.clear()

