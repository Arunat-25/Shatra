"""WebSocket endpoint auth: resolve_user_from_access_token + full connect stack."""

import pytest

from tests.db.conftest import db_fetchone, db_scalar
from tests.integration.helpers import (
    assert_finished_game_for_player,
    auth_headers,
    create_room,
    finish_game,
    read_room_json,
    wait_game_started,
    ws_path,
)


pytestmark = pytest.mark.integration


class TestWebsocketEndpointAuth:
    def test_endpoint_resolves_valid_jwt(self, client, auth_user_factory):
        user = auth_user_factory()
        room_id = create_room(
            client,
            room_type="ai",
            client_id=user["client_id"],
            headers=auth_headers(user["access_token"]),
        )
        with client.websocket_connect(
            ws_path(room_id, user["client_id"], user["access_token"])
        ) as ws:
            wait_game_started(ws)
            room_data = read_room_json(room_id)
            meta = room_data["player_meta"][user["client_id"]]
            assert meta["user_id"] == user["user_id"]
            assert meta["is_anonymous"] is False
            finish_game(client, ws, room_id, db_scalar_fn=db_scalar)

        assert_finished_game_for_player(
            db_fetchone, room_id, user["client_id"], user_id=user["user_id"], is_anonymous=False
        )

    def test_endpoint_missing_token_preserves_rest_meta(self, client, auth_user_factory):
        user = auth_user_factory()
        room_id = create_room(
            client,
            room_type="ai",
            client_id=user["client_id"],
            headers=auth_headers(user["access_token"]),
        )
        with client.websocket_connect(ws_path(room_id, user["client_id"])) as ws:
            wait_game_started(ws)
            room_data = read_room_json(room_id)
            assert room_data["player_meta"][user["client_id"]]["user_id"] == user["user_id"]
            finish_game(client, ws, room_id, db_scalar_fn=db_scalar)

        assert_finished_game_for_player(
            db_fetchone, room_id, user["client_id"], user_id=user["user_id"], is_anonymous=False
        )

    def test_endpoint_invalid_token_treated_as_anonymous_connect(self, client, auth_user_factory):
        user = auth_user_factory()
        room_id = create_room(
            client,
            room_type="ai",
            client_id=user["client_id"],
            headers=auth_headers(user["access_token"]),
        )
        with client.websocket_connect(
            ws_path(room_id, user["client_id"], "garbage.token.here")
        ) as ws:
            wait_game_started(ws)
            finish_game(client, ws, room_id, db_scalar_fn=db_scalar)

        assert_finished_game_for_player(
            db_fetchone, room_id, user["client_id"], user_id=user["user_id"], is_anonymous=False
        )

    def test_endpoint_anonymous_connect_then_auth_reconnect(self, client, auth_user_factory):
        user = auth_user_factory()
        client_id = user["client_id"]
        room_id = create_room(client, room_type="ai", client_id=client_id)

        with client.websocket_connect(ws_path(room_id, client_id)) as ws:
            wait_game_started(ws)

        from backend.ws_manager import manager
        manager.connections.pop(room_id, None)

        with client.websocket_connect(
            ws_path(room_id, client_id, user["access_token"])
        ) as ws:
            wait_game_started(ws)
            finish_game(client, ws, room_id, db_scalar_fn=db_scalar)

        assert_finished_game_for_player(
            db_fetchone, room_id, client_id, user_id=user["user_id"], is_anonymous=False
        )
