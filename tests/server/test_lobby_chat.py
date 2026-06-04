"""Тесты общего чата лобби."""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.lobby_chat import (
    LOBBY_CHAT_MAX_LENGTH,
    LOBBY_CHAT_MAX_MESSAGES,
    LOBBY_CHAT_MIN_INTERVAL,
    LOBBY_CHAT_REDIS_KEY,
    LobbyChatManager,
    _build_entry,
    _cooldown_active,
    _save_history,
    _set_cooldown,
    clear_lobby_chat_storage,
    get_history,
    handle_lobby_chat_message,
    lobby_chat_manager,
    send_lobby_chat_history,
)
from backend.chat import sanitize_chat_text


@pytest.fixture(autouse=True)
async def _reset_lobby_chat():
    lobby_chat_manager.connections.clear()
    await clear_lobby_chat_storage()
    yield
    lobby_chat_manager.connections.clear()
    await clear_lobby_chat_storage()


class TestLobbySanitize:
    def test_truncates_to_500(self):
        long_text = "a" * 600
        assert len(sanitize_chat_text(long_text, LOBBY_CHAT_MAX_LENGTH)) == LOBBY_CHAT_MAX_LENGTH

    def test_exactly_500_chars_preserved(self):
        text = "я" * 500
        assert len(sanitize_chat_text(text, LOBBY_CHAT_MAX_LENGTH)) == 500

    def test_strips_html(self):
        assert sanitize_chat_text("<b>hi</b>", LOBBY_CHAT_MAX_LENGTH) == "hi"

    def test_whitespace_only_becomes_none(self):
        assert sanitize_chat_text("\n\t  \r", LOBBY_CHAT_MAX_LENGTH) is None

    def test_zero_width_and_unicode_survive_sanitize(self):
        raw = "café\u200b\u200c"
        assert "café" in sanitize_chat_text(raw, LOBBY_CHAT_MAX_LENGTH)


@pytest.mark.asyncio
class TestLobbyHistory:
    async def test_trims_to_30_messages(self):
        messages = [
            _build_entry(f"c{i}", f"msg{i}", float(i), None)
            for i in range(LOBBY_CHAT_MAX_MESSAGES + 1)
        ]
        with patch("backend.state.redis_client", None):
            from backend import lobby_chat as lc

            lc._memory_messages = messages
            await lc._save_history(messages)
            stored = await get_history()
        assert len(stored) == LOBBY_CHAT_MAX_MESSAGES
        assert stored[0]["text"] == f"msg{1}"
        assert stored[-1]["text"] == f"msg{LOBBY_CHAT_MAX_MESSAGES}"


@pytest.mark.asyncio
class TestLobbyCooldown:
    async def test_second_message_within_3s_rejected(self):
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        client_id = "client-a"
        now = time.time()
        with patch("backend.state.redis_client", None):
            from backend import lobby_chat as lc

            lc._memory_messages = [
                _build_entry(client_id, "first", now - 0.5, None),
            ]
            ok = await handle_lobby_chat_message(
                client_id, ws, {"text": "second"}, None
            )
        assert ok is True
        assert ws.send_json.call_args[0][0]["message_code"] == "chat.too_fast"

    async def test_cooldown_allows_after_interval(self):
        ws = MagicMock()
        client_id = "client-b"
        old_ts = time.time() - LOBBY_CHAT_MIN_INTERVAL - 1
        with (
            patch("backend.state.redis_client", None),
            patch("backend.lobby_chat.lobby_chat_manager") as mgr,
        ):
            from backend import lobby_chat as lc

            lc._memory_messages = [
                _build_entry(client_id, "first", old_ts, None),
            ]
            mgr.broadcast = AsyncMock()
            ok = await handle_lobby_chat_message(
                client_id, ws, {"text": "second"}, None
            )
        assert ok is True
        mgr.broadcast.assert_awaited_once()
        stored = await get_history()
        assert stored[-1]["text"] == "second"


@pytest.mark.asyncio
class TestLobbyHandleMessage:
    async def test_empty_message_rejected(self):
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        ok = await handle_lobby_chat_message("c1", ws, {"text": "   "}, None)
        assert ok is True
        assert ws.send_json.call_args[0][0]["message_code"] == "chat.empty"

    async def test_broadcast_includes_display_name(self):
        user = MagicMock()
        user.id = "00000000-0000-0000-0000-000000000001"
        user.username = "hero"
        with patch("backend.lobby_chat.lobby_chat_manager") as mgr:
            mgr.broadcast = AsyncMock()
            ok = await handle_lobby_chat_message(
                "c1", MagicMock(), {"text": "hello lobby"}, user
            )
        assert ok is True
        payload = mgr.broadcast.call_args[0][0]
        assert payload["type"] == "chat"
        assert payload["display_name"] == "hero"
        assert payload["text"] == "hello lobby"


@pytest.mark.asyncio
class TestLobbyRedisFallback:
    async def test_corrupt_redis_json_returns_empty_history(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="{not-json")
        with patch("backend.state.redis_client", mock_redis):
            assert await get_history() == []

    async def test_redis_cooldown_key_blocks_without_local_history(self):
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)
        with patch("backend.state.redis_client", mock_redis):
            assert await _cooldown_active("any-client") is True

    async def test_persists_history_via_redis(self):
        entry = _build_entry("c1", "redis-msg", 1.0, None)
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        with patch("backend.state.redis_client", mock_redis):
            await _save_history([entry])
            mock_redis.set.assert_awaited_once()
            key, payload = mock_redis.set.call_args[0]
            assert key == LOBBY_CHAT_REDIS_KEY
            stored = json.loads(payload)
            assert stored[0]["text"] == "redis-msg"

    async def test_set_cooldown_uses_redis_ttl(self):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        with patch("backend.state.redis_client", mock_redis):
            await _set_cooldown("cid-x")
        mock_redis.set.assert_awaited_once_with(
            "lobby_chat:cooldown:cid-x",
            "1",
            ex=int(LOBBY_CHAT_MIN_INTERVAL),
        )


@pytest.mark.asyncio
class TestLobbyChatManager:
    async def test_reconnect_replaces_same_client_socket(self):
        mgr = LobbyChatManager()
        ws1, ws2 = AsyncMock(), AsyncMock()
        await mgr.connect("dup", ws1)
        await mgr.connect("dup", ws2)
        assert mgr.connections["dup"] is ws2

    async def test_broadcast_reaches_all_connected_including_sender(self):
        mgr = LobbyChatManager()
        ws_a = AsyncMock()
        ws_b = AsyncMock()
        ws_a.send_json = AsyncMock()
        ws_b.send_json = AsyncMock()
        await mgr.connect("a", ws_a)
        await mgr.connect("b", ws_b)
        payload = {"type": "chat", "text": "all"}
        await mgr.broadcast(payload)
        ws_a.send_json.assert_awaited_once_with(payload)
        ws_b.send_json.assert_awaited_once_with(payload)

    async def test_broadcast_except_skips_one_client(self):
        mgr = LobbyChatManager()
        ws_a = AsyncMock()
        ws_b = AsyncMock()
        ws_a.send_json = AsyncMock()
        ws_b.send_json = AsyncMock()
        await mgr.connect("a", ws_a)
        await mgr.connect("b", ws_b)
        await mgr.broadcast({"type": "chat"}, except_client_id="a")
        ws_a.send_json.assert_not_awaited()
        ws_b.send_json.assert_awaited_once()

    async def test_send_swallows_broken_websocket(self):
        ws = AsyncMock()
        ws.send_json = AsyncMock(side_effect=RuntimeError("broken"))
        await LobbyChatManager._send(ws, {"type": "chat"})

    async def test_send_lobby_chat_history_always_includes_messages_key(self):
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        with patch("backend.lobby_chat.get_history", AsyncMock(return_value=[])):
            await send_lobby_chat_history(ws)
        ws.send_json.assert_awaited_once_with(
            {"type": "chat_history", "messages": []}
        )


@pytest.mark.asyncio
class TestLobbyCooldownIsolation:
    async def test_user_b_not_blocked_by_user_a_recent_message(self):
        now = time.time()
        with patch("backend.state.redis_client", None):
            from backend import lobby_chat as lc

            lc._memory_messages = [
                _build_entry("user-a", "recent", now, None),
            ]
            assert await _cooldown_active("user-b") is False
