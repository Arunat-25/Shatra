"""Tests for creator username resolution in room listing."""

import json

import pytest

from backend.player_identity import meta_from_user
from tests.integration.helpers import flush_redis, new_client_id, redis_client

pytestmark = pytest.mark.server


@pytest.fixture(autouse=True)
def _clean_redis():
    flush_redis()
    yield
    flush_redis()


class TestListRoomsCreator:
    def test_fallback_from_player_meta(self, client):
        room_id = "crt00001"
        creator_id = new_client_id()
        meta = meta_from_user(None)
        meta["username"] = "hidden_name"
        meta["is_anonymous"] = False
        room = {
            "room_id": room_id,
            "type": "public",
            "game_started": False,
            "created_at": "2026-01-01T00:00:00",
            "creator_client_id": creator_id,
            "creator_username": None,
            "player_meta": {creator_id: meta},
            "players": {creator_id: "белый"},
        }
        redis_client().set(f"room:{room_id}", json.dumps(room))
        rooms = client.get(f"/rooms?client_id={new_client_id()}").json()["rooms"]
        match = [r for r in rooms if r["room_id"] == room_id]
        assert len(match) == 1
        assert match[0]["creator_username"] == "hidden_name"

    def test_create_with_auth_shows_username(self, client):
        payload = {"username": "creator_user", "password": "secret12"}
        reg = client.post("/api/auth/register", json=payload)
        assert reg.status_code == 200
        user = reg.json()
        cid = new_client_id()
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        r = client.post(
            "/rooms",
            json={"type": "public", "creator_client_id": cid},
            headers=headers,
        )
        assert r.status_code == 200
        room_id = r.json()["room_id"]
        rooms = client.get(f"/rooms?client_id={new_client_id()}").json()["rooms"]
        match = [x for x in rooms if x["room_id"] == room_id]
        assert match[0]["creator_username"] == "creator_user"
