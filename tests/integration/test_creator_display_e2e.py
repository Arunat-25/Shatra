"""E2E: creator username visible in GET /rooms after WS auth connect."""

import pytest

from tests.integration.helpers import (
    auth_headers,
    create_room,
    flush_redis,
    new_client_id,
    ws_path,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _flush():
    flush_redis()
    yield
    flush_redis()


class TestCreatorDisplayE2E:
    def test_anonymous_create_auth_ws_shows_username_in_list(
        self, client, auth_user_factory
    ):
        user = auth_user_factory()
        cid = user["client_id"]
        room_id = create_room(
            client,
            room_type="public",
            client_id=cid,
        )
        with client.websocket_connect(
            ws_path(room_id, cid, user["access_token"])
        ) as ws:
            msg = ws.receive_json()
            assert msg.get("status") == "waiting"

        rooms = client.get(f"/rooms?client_id={new_client_id()}").json()["rooms"]
        match = [r for r in rooms if r["room_id"] == room_id]
        assert len(match) == 1
        assert match[0]["creator_username"] == user["username"]
        assert match[0]["creator_rating"] == 1200
