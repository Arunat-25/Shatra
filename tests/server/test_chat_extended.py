"""Расширенные тесты чата: rate limit, история, XSS, интеграция."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.chat import (
    CHAT_MAX_MESSAGES,
    CHAT_RATE_LIMIT,
    _append_message,
    handle_chat_message,
    sanitize_chat_text,
    send_chat_history,
)


class TestSanitizeChatExtended:
    def test_script_tags_removed(self):
        assert sanitize_chat_text('<script></script>hello') == 'hello'
        assert sanitize_chat_text('<script>alert(1)</script> hello') == 'alert(1) hello'

    def test_html_entities_unescaped_then_stripped(self):
        assert sanitize_chat_text('&lt;b&gt;x&lt;/b&gt;') == 'x'

    def test_only_whitespace_and_tags_rejected(self):
        assert sanitize_chat_text('<br><br>') is None

    def test_collapses_internal_whitespace(self):
        assert sanitize_chat_text('hello   world') == 'hello world'

    def test_unicode_message_preserved(self):
        assert sanitize_chat_text('  Алтай  ') == 'Алтай'


class TestAppendMessage:
    def test_trims_to_max_messages(self):
        room = {"chat_messages": [{"text": str(i)} for i in range(CHAT_MAX_MESSAGES)]}
        _append_message(room, {"text": "new"})
        assert len(room["chat_messages"]) == CHAT_MAX_MESSAGES
        assert room["chat_messages"][-1]["text"] == "new"
        assert room["chat_messages"][0]["text"] == "1"


@pytest.mark.asyncio
class TestRateLimit:
    async def test_blocks_after_limit(self):
        from backend.chat import _check_rate_limit

        mock_redis = AsyncMock()
        counts = {"n": 0}

        async def incr(key):
            counts["n"] += 1
            return counts["n"]

        mock_redis.incr = incr
        mock_redis.expire = AsyncMock()

        with patch("backend.chat.redis_client", mock_redis):
            for i in range(CHAT_RATE_LIMIT):
                assert await _check_rate_limit("r", "c") is True
            assert await _check_rate_limit("r", "c") is False

    async def test_rate_limit_error_message(self):
        room_id = "r1"
        room = {"room_id": room_id, "chat_messages": [], "player_meta": {}}
        stored = {room_id: room}

        ws = AsyncMock()
        ws.send_json = AsyncMock()

        with (
            patch("backend.chat.get_room", new_callable=AsyncMock, return_value=stored[room_id]),
            patch("backend.chat.set_room", new_callable=AsyncMock),
            patch("backend.chat._check_rate_limit", new_callable=AsyncMock, return_value=False),
        ):
            ok = await handle_chat_message(
                room_id, "c1", ws, {"text": "spam"}, is_ai_room=False
            )
        assert ok is True
        msg = ws.send_json.call_args[0][0]
        assert msg["message_code"] == "chat.rate_limit"


@pytest.mark.asyncio
class TestChatHistory:
    async def test_empty_history_no_send(self):
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        with patch("backend.chat.manager") as mgr:
            mgr.send_to_player = AsyncMock()
            await send_chat_history(ws, {"chat_messages": []})
            mgr.send_to_player.assert_not_called()

    async def test_sends_chat_history_payload(self):
        ws = AsyncMock()
        history = [{"text": "old", "ts": 1.0}]
        with patch("backend.chat.manager") as mgr:
            mgr.send_to_player = AsyncMock()
            await send_chat_history(ws, {"chat_messages": history})
            mgr.send_to_player.assert_awaited_once()
            payload = mgr.send_to_player.call_args[0][1]
            assert payload["type"] == "chat_history"
            assert payload["messages"] == history


@pytest.mark.asyncio
class TestHandleChatMessage:
    async def test_room_not_found_returns_false(self):
        ws = AsyncMock()
        with patch("backend.chat.get_room", new_callable=AsyncMock, return_value=None):
            ok = await handle_chat_message("x", "c", ws, {"text": "a"}, is_ai_room=False)
        assert ok is False

    async def test_empty_after_sanitize_errors(self):
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        room = {"chat_messages": [], "player_meta": {}}
        with patch("backend.chat.get_room", new_callable=AsyncMock, return_value=room):
            ok = await handle_chat_message(
                "r", "c", ws, {"text": "   "}, is_ai_room=False
            )
        assert ok is True
        assert ws.send_json.call_args[0][0]["message_code"] == "chat.empty"

    async def test_broadcast_includes_display_name(self):
        room_id = "r1"
        room = {
            "chat_messages": [],
            "player_meta": {
                "c1": {"username": "hero", "is_anonymous": False},
            },
        }
        stored = {room_id: dict(room)}

        async def fake_get(rid):
            return stored[rid]

        async def fake_set(rid, data):
            stored[rid] = data

        ws = MagicMock()
        with (
            patch("backend.chat.get_room", side_effect=fake_get),
            patch("backend.chat.set_room", side_effect=fake_set),
            patch("backend.chat._check_rate_limit", new_callable=AsyncMock, return_value=True),
            patch("backend.chat.manager") as mgr,
        ):
            mgr.send_to_room = AsyncMock()
            await handle_chat_message(
                room_id, "c1", ws, {"text": "gg"}, is_ai_room=False
            )
            broadcast = mgr.send_to_room.call_args[0][1]
        assert broadcast["type"] == "chat"
        assert broadcast["display_name"] == "hero"
        assert broadcast["text"] == "gg"

    async def test_anonymous_broadcast_display_name(self):
        room_id = "r1"
        stored = {
            room_id: {
                "chat_messages": [],
                "player_meta": {"c1": {"username": None, "is_anonymous": True}},
            }
        }

        with (
            patch("backend.chat.get_room", new_callable=AsyncMock, return_value=stored[room_id]),
            patch("backend.chat.set_room", new_callable=AsyncMock),
            patch("backend.chat._check_rate_limit", new_callable=AsyncMock, return_value=True),
            patch("backend.chat.manager") as mgr,
        ):
            mgr.send_to_room = AsyncMock()
            await handle_chat_message(
                room_id, "c1", MagicMock(), {"text": "?"}, is_ai_room=False
            )
            assert mgr.send_to_room.call_args[0][1]["display_name"] == "Аноним"
