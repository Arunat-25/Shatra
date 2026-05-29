"""REST/WS идентификация: комнаты, list, game_started, reconnect meta."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.game_helpers import build_game_started_response
from backend.models import CreateRoomRequest
from backend.player_identity import build_players_info
from backend.room_manager import create_room, list_rooms
from backend.ws_manager import ConnectionManager


@pytest.mark.asyncio
class TestListRoomsCreator:
    async def test_creator_username_in_public_lobby(self):
        now = datetime.now(timezone.utc).isoformat()
        raw_rooms = [
            {
                "room_id": "aaa",
                "type": "public",
                "game_started": False,
                "created_at": now,
                "time_control": 300,
                "increment": 0,
                "creator_username": "master",
            },
            {
                "room_id": "bbb",
                "type": "public",
                "game_started": False,
                "created_at": now,
                "time_control": None,
                "increment": None,
                "creator_username": None,
            },
        ]

        async def fake_scan(pattern):
            return [f"room:{r['room_id']}" for r in raw_rooms]

        async def fake_get_raw(key):
            rid = key.split(":")[-1]
            for r in raw_rooms:
                if r["room_id"] == rid:
                    return json.dumps(r)
            return None

        with (
            patch("backend.room_manager.scan_keys", side_effect=fake_scan),
            patch("backend.room_manager.get_raw", side_effect=fake_get_raw),
        ):
            result = await list_rooms()

        assert len(result["rooms"]) == 2
        by_id = {r["room_id"]: r for r in result["rooms"]}
        assert by_id["aaa"]["creator_username"] == "master"
        assert by_id["bbb"]["creator_username"] is None

    async def test_private_and_started_rooms_excluded(self):
        now = datetime.now(timezone.utc).isoformat()
        raw = json.dumps({
            "room_id": "priv",
            "type": "private",
            "game_started": False,
            "created_at": now,
        })

        with (
            patch("backend.room_manager.scan_keys", new_callable=AsyncMock, return_value=["room:priv"]),
            patch("backend.room_manager.get_raw", new_callable=AsyncMock, return_value=raw),
        ):
            assert await list_rooms() == {"rooms": []}


@pytest.mark.asyncio
class TestCreateRoomIdentity:
    async def test_no_creator_client_id_skips_player_meta_entry(self):
        stored = {}

        async def fake_set(room_id, data):
            stored[room_id] = data

        user = MagicMock()
        user.id = "11111111-1111-1111-1111-111111111111"
        user.username = "u"
        req = CreateRoomRequest(type="public", creator_client_id=None)
        with patch("backend.room_manager.set_room", side_effect=fake_set):
            await create_room(req, user=user)
        room = next(iter(stored.values()))
        assert room["player_meta"] == {}
        assert room["creator_username"] == "u"


@pytest.mark.asyncio
class TestWsConnectPlayerMeta:
    async def test_connect_authenticated_updates_meta(self):
        cm = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        user = MagicMock()
        user.id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        user.username = "Воин"
        room = {
            "room_id": "r1",
            "type": "public",
            "game_started": False,
            "creator_client_id": "other",
            "creator_color_preference": "random",
            "players": {},
            "player_meta": {},
        }

        async def capture_set(rid, data):
            room.update(data)

        with (
            patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room),
            patch("backend.ws_manager.set_room", side_effect=capture_set),
        ):
            ok = await cm.connect("r1", ws, "client-new", user=user)

        assert ok is True
        assert room["player_meta"]["client-new"]["username"] == "Воин"
        assert room["player_meta"]["client-new"]["is_anonymous"] is False

    async def test_reconnect_overwrites_meta_when_user_logs_in(self):
        """Игрок был анонимом, переподключился с JWT — meta обновляется."""
        cm = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        user = MagicMock()
        user.id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        user.username = "late_auth"
        room = {
            "room_id": "r1",
            "type": "public",
            "game_started": False,
            "players": {"player-a": "белый"},
            "player_meta": {
                "player-a": {"username": None, "is_anonymous": True, "user_id": None},
            },
        }

        with (
            patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room),
            patch("backend.ws_manager.set_room", new_callable=AsyncMock),
            patch("backend.ws_manager.disconnect_timers", {}),
        ):
            cm.connections["r1"] = {}
            ok = await cm.connect("r1", ws, "player-a", user=user)

        assert ok is True
        assert room["player_meta"]["player-a"]["username"] == "late_auth"
        assert room["player_meta"]["player-a"]["is_anonymous"] is False


class TestGameStartedPlayersInfo:
    def test_includes_players_info(self, sample_room_data, game_in_progress):
        sample_room_data["players"] = {"c1": "белый", "c2": "черный"}
        sample_room_data["player_meta"] = {
            "c1": {"username": "a", "is_anonymous": False},
            "c2": {"username": None, "is_anonymous": True},
        }
        resp = build_game_started_response(game_in_progress, sample_room_data, "белый")
        assert "players_info" in resp
        assert len(resp["players_info"]) == 2
        names = {p["display_name"] for p in resp["players_info"]}
        assert "a" in names
        assert "Аноним" in names


@pytest.mark.asyncio
class TestProcessClientMessageChatPriority:
    """Чат обрабатывается до проверки хода (можно писать не в свой ход)."""

    async def test_chat_does_not_require_game_state(self):
        from backend.game_session import _process_client_message_locked

        ws = AsyncMock()
        with patch(
            "backend.game_session.handle_chat_message",
            new_callable=AsyncMock,
            return_value=True,
        ) as chat_mock:
            ok = await _process_client_message_locked(
                "room1",
                "c1",
                {"type": "chat", "text": "hi"},
                ws,
                is_ai_room=False,
            )
        assert ok is True
        chat_mock.assert_awaited_once()
