"""REST API комнат: create, join, list."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from backend.models import CreateRoomRequest
from backend.room_manager import create_room, join_room, list_rooms


@pytest.mark.asyncio
class TestJoinRoom:
    async def test_not_found(self):
        with patch("backend.room_manager.get_room", new_callable=AsyncMock, return_value=None):
            with pytest.raises(HTTPException) as exc:
                await join_room("missing")
            assert exc.value.status_code == 404

    async def test_game_already_started(self):
        room = {"room_id": "abc", "game_started": True, "players": {"a": "белый"}}
        with patch("backend.room_manager.get_room", new_callable=AsyncMock, return_value=room):
            with pytest.raises(HTTPException) as exc:
                await join_room("abc")
            assert exc.value.status_code == 409
            assert "началась" in exc.value.detail.lower()

    async def test_room_full(self):
        room = {
            "room_id": "abc",
            "game_started": False,
            "players": {"a": "белый", "b": "черный"},
        }
        with patch("backend.room_manager.get_room", new_callable=AsyncMock, return_value=room):
            with pytest.raises(HTTPException) as exc:
                await join_room("abc")
            assert exc.value.status_code == 409
            assert "заполнена" in exc.value.detail.lower()

    async def test_success(self):
        room = {"room_id": "abc", "game_started": False, "players": {"a": "белый"}}
        with patch("backend.room_manager.get_room", new_callable=AsyncMock, return_value=room):
            assert await join_room("abc") == {"room_id": "abc"}


@pytest.mark.asyncio
class TestCreateRoom:
    async def test_stores_creator_and_color_preference(self):
        stored = {}

        async def fake_set_room(room_id, data):
            stored[room_id] = data

        request = CreateRoomRequest(
            type="public",
            time_control=180,
            increment=3,
            creator_client_id="client-abc",
            color_preference="черный",
        )
        with patch("backend.room_manager.set_room", side_effect=fake_set_room):
            result = await create_room(request)

        assert result["type"] == "public"
        assert len(result["room_id"]) == 8
        room = stored[result["room_id"]]
        assert room["creator_client_id"] == "client-abc"
        assert room["creator_color_preference"] == "черный"
        assert room["time_control"] == 180
        assert room["increment"] == 3
        assert room["timer_white"] == 180.0
        assert room["timer_black"] == 180.0

    async def test_untimed_room_has_no_clocks(self):
        stored = {}

        async def fake_set_room(room_id, data):
            stored[room_id] = data

        request = CreateRoomRequest(type="ai", creator_client_id="c1", color_preference="random")
        with patch("backend.room_manager.set_room", side_effect=fake_set_room):
            result = await create_room(request)
        room = stored[result["room_id"]]
        assert room["time_control"] is None
        assert room.get("timer_white") is None


@pytest.mark.asyncio
class TestListRooms:
    async def test_lists_waiting_public_rooms_with_time_fields(self):
        waiting = {
            "room_id": "pub1",
            "type": "public",
            "game_started": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "time_control": 60,
            "increment": 1,
        }
        started = {**waiting, "room_id": "pub2", "game_started": True}
        private = {**waiting, "room_id": "prv1", "type": "private"}

        async def fake_get_raw(key):
            data = {"room:pub1": waiting, "room:pub2": started, "room:prv1": private}[key]
            return json.dumps(data)

        with patch("backend.room_manager.scan_keys", new_callable=AsyncMock, return_value=["room:pub1", "room:pub2", "room:prv1"]):
            with patch("backend.room_manager.get_raw", side_effect=fake_get_raw):
                result = await list_rooms()

        assert len(result["rooms"]) == 1
        room = result["rooms"][0]
        assert room["room_id"] == "pub1"
        assert room["time_control"] == 60
        assert room["increment"] == 1
