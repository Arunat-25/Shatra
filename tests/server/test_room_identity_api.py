"""REST API: создание комнаты с/без JWT (без PostgreSQL — dependency override)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.auth.dependencies import get_optional_user
from main import app


@pytest.fixture
def room_api_client():
    """TestClient с mock Redis lifecycle и перехватом set_room."""
    stored = {}

    async def fake_set(room_id, data):
        stored[room_id] = data

    async def fake_init_redis():
        import backend.state as st

        st.redis_client = AsyncMock()

    with (
        patch("main.init_redis", side_effect=fake_init_redis),
        patch("main.close_redis", new_callable=AsyncMock),
        patch("main.init_db", new_callable=AsyncMock),
        patch("main.close_db", new_callable=AsyncMock),
        patch("backend.room_manager.set_room", side_effect=fake_set),
    ):
        with TestClient(app) as client:
            yield client, stored


class TestCreateRoomWithAuth:
    def test_anonymous_create_no_creator_username(self, room_api_client):
        client, stored = room_api_client
        app.dependency_overrides.pop(get_optional_user, None)
        r = client.post(
            "/rooms",
            json={
                "type": "public",
                "creator_client_id": "guest-xyz",
                "color_preference": "random",
            },
        )
        assert r.status_code == 200
        room = stored[r.json()["room_id"]]
        assert room.get("creator_username") is None
        assert room["player_meta"]["guest-xyz"]["is_anonymous"] is True

    def test_authenticated_create_sets_creator(self, room_api_client):
        client, stored = room_api_client
        user = MagicMock()
        user.id = uuid.uuid4()
        user.username = "room_host"

        async def override_user():
            return user

        app.dependency_overrides[get_optional_user] = override_user
        try:
            r = client.post(
                "/rooms",
                json={
                    "type": "public",
                    "creator_client_id": "host-client",
                    "color_preference": "белый",
                },
            )
        finally:
            app.dependency_overrides.pop(get_optional_user, None)

        assert r.status_code == 200
        room = stored[r.json()["room_id"]]
        assert room["creator_username"] == "room_host"
        assert room["player_meta"]["host-client"]["username"] == "room_host"
        assert str(room["creator_user_id"]) == str(user.id)

    def test_optional_user_none_when_invalid_token(self, room_api_client):
        client, stored = room_api_client

        async def override_none():
            return None

        app.dependency_overrides[get_optional_user] = override_none
        try:
            r = client.post(
                "/rooms",
                json={"type": "public", "creator_client_id": "c1"},
            )
        finally:
            app.dependency_overrides.pop(get_optional_user, None)

        assert r.status_code == 200
        assert stored[r.json()["room_id"]].get("creator_username") is None
