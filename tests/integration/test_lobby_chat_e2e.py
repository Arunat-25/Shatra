"""Lobby WebSocket: history, broadcast, cooldown, auth — Redis + TestClient."""

import json
import time

import pytest
from starlette.websockets import WebSocketDisconnect

from tests.integration.helpers import (
    lobby_ws_path,
    new_client_id,
    read_lobby_chat_redis,
    redis_client,
    wait_error_code,
    wait_lobby_chat,
    wait_lobby_chat_history,
)


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _init_redis_on_test_loop(client):
    """TestClient (Starlette 1.0) не вызывает lifespan — init_redis вручную на loop клиента."""
    from backend.state import close_redis, init_redis

    client.portal.call(init_redis)
    yield
    client.portal.call(close_redis)


class TestLobbyWebsocketConnect:
    def test_missing_client_id_rejects_connection(self, client):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/lobby/") as ws:
                ws.receive_json()

    def test_connect_sends_empty_chat_history(self, client):
        cid = new_client_id()
        with client.websocket_connect(lobby_ws_path(cid)) as ws:
            hist = wait_lobby_chat_history(ws)
        assert hist["type"] == "chat_history"
        assert hist["messages"] == []


class TestLobbyChatBroadcast:
    def test_two_clients_guest_sees_host_message(self, client):
        host = new_client_id()
        guest = new_client_id()
        with client.websocket_connect(lobby_ws_path(host)) as ws_host:
            wait_lobby_chat_history(ws_host)
            with client.websocket_connect(lobby_ws_path(guest)) as ws_guest:
                wait_lobby_chat_history(ws_guest)
                ws_host.send_json({"type": "chat", "text": "hello lobby"})
                wait_lobby_chat(ws_host, text="hello lobby")
                msg = wait_lobby_chat(ws_guest, text="hello lobby")
        assert msg["client_id"] == host
        assert msg["from_client_id"] == host

    def test_late_joiner_receives_persisted_history(self, client):
        first = new_client_id()
        with client.websocket_connect(lobby_ws_path(first)) as ws:
            wait_lobby_chat_history(ws)
            ws.send_json({"type": "chat", "text": "survives reconnect"})
            wait_lobby_chat(ws, text="survives reconnect")

        second = new_client_id()
        with client.websocket_connect(lobby_ws_path(second)) as ws2:
            hist = wait_lobby_chat_history(ws2)
        texts = [m["text"] for m in hist["messages"]]
        assert texts == ["survives reconnect"]
        stored = read_lobby_chat_redis()
        assert [m["text"] for m in stored] == ["survives reconnect"]

    def test_authenticated_user_display_name_in_broadcast(self, client, auth_user_factory):
        user = auth_user_factory()
        with client.websocket_connect(
            lobby_ws_path(user["client_id"], user["access_token"])
        ) as ws:
            wait_lobby_chat_history(ws)
            ws.send_json({"type": "chat", "text": "signed in"})
            msg = wait_lobby_chat(ws, text="signed in")
        assert msg["is_anonymous"] is False
        assert msg["display_name"] == user["username"]


class TestLobbyChatValidation:
    def test_empty_message_returns_chat_empty(self, client):
        cid = new_client_id()
        with client.websocket_connect(lobby_ws_path(cid)) as ws:
            wait_lobby_chat_history(ws)
            ws.send_json({"type": "chat", "text": "   "})
            err = wait_error_code(ws, "chat.empty")
        assert err["status"] == "error"

    def test_cooldown_blocks_second_message(self, client):
        cid = new_client_id()
        with client.websocket_connect(lobby_ws_path(cid)) as ws:
            wait_lobby_chat_history(ws)
            ws.send_json({"type": "chat", "text": "first"})
            wait_lobby_chat(ws, text="first")
            ws.send_json({"type": "chat", "text": "too soon"})
            err = wait_error_code(ws, "chat.too_fast")
        assert err["status"] == "error"
        stored = read_lobby_chat_redis()
        assert len(stored) == 1
        assert stored[0]["text"] == "first"

    def test_cooldown_allows_after_interval(self, client):
        cid = new_client_id()
        with client.websocket_connect(lobby_ws_path(cid)) as ws:
            wait_lobby_chat_history(ws)
            ws.send_json({"type": "chat", "text": "one"})
            wait_lobby_chat(ws, text="one")
            time.sleep(3.1)
            ws.send_json({"type": "chat", "text": "two"})
            wait_lobby_chat(ws, text="two")
        texts = [m["text"] for m in read_lobby_chat_redis()]
        assert texts == ["one", "two"]

    def test_two_users_independent_cooldowns(self, client):
        a, b = new_client_id(), new_client_id()
        with client.websocket_connect(lobby_ws_path(a)) as ws_a:
            wait_lobby_chat_history(ws_a)
            with client.websocket_connect(lobby_ws_path(b)) as ws_b:
                wait_lobby_chat_history(ws_b)
                ws_a.send_json({"type": "chat", "text": "from-a"})
                wait_lobby_chat(ws_a, text="from-a")
                wait_lobby_chat(ws_b, text="from-a")
                ws_b.send_json({"type": "chat", "text": "from-b"})
                wait_lobby_chat(ws_b, text="from-b")
        assert [m["text"] for m in read_lobby_chat_redis()] == ["from-a", "from-b"]

    def test_invalid_json_then_valid_chat(self, client):
        cid = new_client_id()
        with client.websocket_connect(lobby_ws_path(cid)) as ws:
            wait_lobby_chat_history(ws)
            ws.send_text("not-json")
            wait_error_code(ws, "ws.invalid_json")
            ws.send_json({"type": "chat", "text": "after bad json"})
            wait_lobby_chat(ws, text="after bad json")

    def test_unknown_type_returns_ws_unknown_type(self, client):
        cid = new_client_id()
        with client.websocket_connect(lobby_ws_path(cid)) as ws:
            wait_lobby_chat_history(ws)
            ws.send_json({"type": "resign"})
            wait_error_code(ws, "ws.unknown_type")


class TestLobbyHistoryLimits:
    def test_connect_trims_seeded_redis_history_to_30(self, client):
        seeded = [
            {
                "client_id": "seed",
                "text": f"msg{i}",
                "ts": float(i),
                "is_anonymous": True,
                "display_name": "Гость",
            }
            for i in range(31)
        ]
        redis_client().set("lobby_chat:messages", json.dumps(seeded))

        cid = new_client_id()
        with client.websocket_connect(lobby_ws_path(cid)) as ws:
            hist = wait_lobby_chat_history(ws)
        assert len(hist["messages"]) == 30
        assert hist["messages"][0]["text"] == "msg1"
        assert hist["messages"][-1]["text"] == "msg30"
        assert len(read_lobby_chat_redis()) == 30
