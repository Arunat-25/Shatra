"""E2E: REST create → WebSocket connect → archive → PostgreSQL."""

import pytest

from tests.db.conftest import db_fetchone, db_scalar
from tests.integration.helpers import (
    assert_finished_game_for_player,
    assert_finished_game_row,
    auth_headers,
    create_room,
    finish_game,
    read_room_json,
    wait_game_started,
    ws_path,
)


pytestmark = pytest.mark.integration


class TestAiRoomIdentity:
    def test_authenticated_with_ws_token(self, client, auth_user_factory):
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
            finish_game(client, ws, room_id, db_scalar_fn=db_scalar)

        assert db_scalar("SELECT COUNT(*) FROM finished_games WHERE room_id = %s", (room_id,)) >= 1
        assert_finished_game_for_player(
            db_fetchone, room_id, user["client_id"], user_id=user["user_id"], is_anonymous=False
        )

    def test_authenticated_without_ws_token_regression(self, client, auth_user_factory):
        """REST JWT + WS без access_token — user_id не теряется."""
        user = auth_user_factory()
        room_id = create_room(
            client,
            room_type="ai",
            client_id=user["client_id"],
            headers=auth_headers(user["access_token"]),
        )
        room_before = read_room_json(room_id)
        meta = room_before["player_meta"][user["client_id"]]
        assert meta["user_id"] == user["user_id"]
        assert meta["is_anonymous"] is False

        with client.websocket_connect(ws_path(room_id, user["client_id"])) as ws:
            wait_game_started(ws)
            room_after_connect = read_room_json(room_id)
            meta_after = room_after_connect["player_meta"][user["client_id"]]
            assert meta_after["user_id"] == user["user_id"]
            assert meta_after["is_anonymous"] is False
            finish_game(client, ws, room_id, db_scalar_fn=db_scalar)

        assert_finished_game_for_player(
            db_fetchone, room_id, user["client_id"], user_id=user["user_id"], is_anonymous=False
        )

    def test_anonymous_player(self, client):
        client_id = "anon-ai-client"
        room_id = create_room(client, room_type="ai", client_id=client_id)
        with client.websocket_connect(ws_path(room_id, client_id)) as ws:
            wait_game_started(ws)
            finish_game(client, ws, room_id, db_scalar_fn=db_scalar)

        assert_finished_game_for_player(
            db_fetchone, room_id, client_id, user_id=None, is_anonymous=True
        )

    def test_anonymous_create_ws_with_token(self, client, auth_user_factory):
        user = auth_user_factory()
        client_id = user["client_id"]
        room_id = create_room(client, room_type="ai", client_id=client_id)
        with client.websocket_connect(
            ws_path(room_id, client_id, user["access_token"])
        ) as ws:
            wait_game_started(ws)
            finish_game(client, ws, room_id, db_scalar_fn=db_scalar)

        assert_finished_game_for_player(
            db_fetchone, room_id, client_id, user_id=user["user_id"], is_anonymous=False
        )

    def test_invalid_ws_token_preserves_rest_identity(self, client, auth_user_factory):
        user = auth_user_factory()
        room_id = create_room(
            client,
            room_type="ai",
            client_id=user["client_id"],
            headers=auth_headers(user["access_token"]),
        )
        with client.websocket_connect(
            ws_path(room_id, user["client_id"], "not-a-valid-jwt")
        ) as ws:
            wait_game_started(ws)
            room_data = read_room_json(room_id)
            assert room_data["player_meta"][user["client_id"]]["user_id"] == user["user_id"]
            finish_game(client, ws, room_id, db_scalar_fn=db_scalar)

        assert_finished_game_for_player(
            db_fetchone, room_id, user["client_id"], user_id=user["user_id"], is_anonymous=False
        )


class TestReconnectIdentity:
    def test_reconnect_without_token_preserves_user_id(self, client, auth_user_factory):
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

        from backend.ws_manager import manager
        manager.connections.pop(room_id, None)

        with client.websocket_connect(ws_path(room_id, user["client_id"])) as ws:
            wait_game_started(ws)
            room_data = read_room_json(room_id)
            assert room_data["player_meta"][user["client_id"]]["user_id"] == user["user_id"]
            finish_game(client, ws, room_id, db_scalar_fn=db_scalar)

        assert_finished_game_for_player(
            db_fetchone, room_id, user["client_id"], user_id=user["user_id"], is_anonymous=False
        )

    def test_reconnect_with_token_late_login(self, client, auth_user_factory):
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
            room_data = read_room_json(room_id)
            assert room_data["player_meta"][client_id]["user_id"] == user["user_id"]
            assert room_data["player_meta"][client_id]["is_anonymous"] is False
            finish_game(client, ws, room_id, db_scalar_fn=db_scalar)

        assert_finished_game_for_player(
            db_fetchone, room_id, client_id, user_id=user["user_id"], is_anonymous=False
        )


class TestCreateRoomEdgeCases:
    def test_create_without_creator_client_id_ws_sets_identity(self, client, auth_user_factory):
        user = auth_user_factory()
        room_id = create_room(
            client,
            room_type="ai",
            headers=auth_headers(user["access_token"]),
        )
        with client.websocket_connect(
            ws_path(room_id, user["client_id"], user["access_token"])
        ) as ws:
            wait_game_started(ws)
            room_data = read_room_json(room_id)
            assert room_data["player_meta"][user["client_id"]]["user_id"] == user["user_id"]
            finish_game(client, ws, room_id, db_scalar_fn=db_scalar)

        assert_finished_game_for_player(
            db_fetchone, room_id, user["client_id"], user_id=user["user_id"], is_anonymous=False
        )


class TestPresenceIdentity:
    def test_presence_user_id_without_ws_token(self, client, auth_user_factory):
        user = auth_user_factory()
        room_id = create_room(
            client,
            room_type="ai",
            client_id=user["client_id"],
            headers=auth_headers(user["access_token"]),
        )
        with client.websocket_connect(ws_path(room_id, user["client_id"])) as ws:
            wait_game_started(ws)
            finish_game(client, ws, room_id, db_scalar_fn=db_scalar)

        row = db_fetchone(
            """
            SELECT user_id, is_anonymous FROM presence_sessions
            WHERE client_id = %s ORDER BY connected_at DESC LIMIT 1
            """,
            (user["client_id"],),
        )
        assert row is not None
        assert str(row[0]) == user["user_id"]
        assert row[1] is False
