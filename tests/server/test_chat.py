"""Тесты чата в комнате."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.chat import CHAT_MAX_LENGTH, handle_chat_message, sanitize_chat_text


class TestSanitizeChat:
    def test_strips_html(self):
        assert sanitize_chat_text('<b>hi</b>') == 'hi'

    def test_rejects_empty(self):
        assert sanitize_chat_text('   ') is None

    def test_truncates_length(self):
        long = 'a' * (CHAT_MAX_LENGTH + 50)
        assert len(sanitize_chat_text(long)) == CHAT_MAX_LENGTH


@pytest.mark.asyncio
async def test_chat_message_stored():
    room_id = "room1"
    room = {
        "room_id": room_id,
        "type": "public",
        "players": {"c1": "белый", "c2": "черный"},
        "player_meta": {"c1": {"username": "alice", "is_anonymous": False}},
        "chat_messages": [],
    }
    stored = {room_id: room.copy()}

    async def fake_get(rid):
        return stored.get(rid)

    async def fake_set(rid, data):
        stored[rid] = data

    ws = MagicMock()
    ws.send_json = AsyncMock()

    with (
        patch("backend.chat.get_room", side_effect=fake_get),
        patch("backend.chat.set_room", side_effect=fake_set),
        patch("backend.chat._check_rate_limit", new_callable=AsyncMock, return_value=True),
        patch("backend.chat.manager") as mgr,
    ):
        mgr.send_to_room = AsyncMock()
        ok = await handle_chat_message(
            room_id, "c1", ws, {"text": "Привет"}, is_ai_room=False
        )
    assert ok is True
    assert stored[room_id]["chat_messages"][0]["text"] == "Привет"


@pytest.mark.asyncio
async def test_chat_disabled_in_ai_room():
    ws = MagicMock()
    ws.send_json = AsyncMock()
    ok = await handle_chat_message("r1", "c1", ws, {"text": "hi"}, is_ai_room=True)
    assert ok is True
    ws.send_json.assert_called_once()
