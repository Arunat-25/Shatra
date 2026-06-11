"""
WebSocket connect: дубли вкладок, переполнение комнаты, переподключение.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.ws_manager import ConnectionManager, manager


def _room(players=None, **extra):
    data = {
        "room_id": "room1",
        "type": "public",
        "game_started": False,
        "creator_client_id": "creator",
        "creator_color_preference": "белый",
        "players": dict(players or {}),
    }
    data.update(extra)
    return data


@pytest.fixture
def cm():
    return ConnectionManager()


@pytest.fixture
def mock_ws():
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.mark.asyncio
class TestConnectionManagerConnect:
    async def test_room_not_found_closes_socket(self, cm, mock_ws):
        with patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=None):
            ok = await cm.connect("missing", mock_ws, "c1")
        assert ok is False
        mock_ws.close.assert_called_once()

    async def test_duplicate_tab_same_client_rejected(self, cm, mock_ws):
        room = _room()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.close = AsyncMock()

        with patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room):
            with patch("backend.ws_manager.set_room", new_callable=AsyncMock):
                ok1 = await cm.connect("room1", mock_ws, "player-a")
                assert ok1 is True
                ok2 = await cm.connect("room1", ws2, "player-a")
                assert ok2 is False
                ws2.close.assert_called()
                assert ws2.close.call_args.kwargs.get("reason") == "already_in_game"

    async def test_third_player_rejected_when_two_in_room(self, cm, mock_ws):
        room = _room({"p1": "белый", "p2": "черный"})
        ws3 = AsyncMock()
        ws3.accept = AsyncMock()
        ws3.close = AsyncMock()

        with patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room):
            with patch("backend.ws_manager.set_room", new_callable=AsyncMock):
                ok = await cm.connect("room1", ws3, "p3")
        assert ok is False

    async def test_reconnect_after_disconnect_slot(self, cm, mock_ws):
        """Игрок уже в players, но WS пропал — новое соединение принимается."""
        room = _room({"player-a": "белый"})
        opponent_ws = AsyncMock()

        with patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room):
            with patch("backend.ws_manager.set_room", new_callable=AsyncMock):
                with patch("backend.ws_manager.disconnect_timers", {}):
                    cm.connections["room1"] = {}
                    ok = await cm.connect("room1", mock_ws, "player-a")
        assert ok is True
        assert "room1" in cm.connections
        assert cm.connections["room1"]["player-a"] is mock_ws

    async def test_reconnect_notifies_opponent(self, cm, mock_ws):
        room = _room({"player-a": "белый", "player-b": "черный"})
        opponent_ws = AsyncMock()
        opponent_ws.send_json = AsyncMock()

        with patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room):
            with patch("backend.ws_manager.set_room", new_callable=AsyncMock):
                with patch("backend.ws_manager.disconnect_timers", {}):
                    cm.connections["room1"] = {"player-b": opponent_ws}
                    await cm.connect("room1", mock_ws, "player-a")

        opponent_ws.send_json.assert_called()
        payload = opponent_ws.send_json.call_args[0][0]
        assert payload.get("status") == "opponent_reconnected"

    async def test_joiner_gets_opposite_color_of_creator(self, cm, mock_ws):
        stored = {}

        async def capture_set(room_id, data):
            stored.update(data)

        room = _room()

        with patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room):
            with patch("backend.ws_manager.set_room", side_effect=capture_set):
                await cm.connect("room1", mock_ws, "joiner")

        assert stored["players"]["joiner"] == "черный"


@pytest.mark.asyncio
class TestConnectionManagerMetrics:
    async def test_room_not_found_records_reject_not_connect(self, cm, mock_ws):
        with (
            patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=None),
            patch("backend.ws_manager.record_ws_reject") as reject,
            patch("backend.ws_manager.record_ws_connect") as connect,
        ):
            ok = await cm.connect("missing", mock_ws, "c1")
        assert ok is False
        reject.assert_called_once_with("room_not_found")
        connect.assert_not_called()

    async def test_duplicate_tab_records_already_in_game(self, cm, mock_ws):
        room = _room({"player-a": "белый"})
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.close = AsyncMock()

        with patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room):
            with patch("backend.ws_manager.set_room", new_callable=AsyncMock):
                with patch("backend.ws_manager.start_session", new_callable=AsyncMock):
                    with patch("backend.ws_manager.record_ws_connect"):
                        await cm.connect("room1", mock_ws, "player-a")
                    cm.connections["room1"] = {"player-a": mock_ws}
                    with patch("backend.ws_manager.record_ws_reject") as reject:
                        ok = await cm.connect("room1", ws2, "player-a")
        assert ok is False
        reject.assert_called_once_with("already_in_game")

    async def test_room_full_records_reject(self, cm, mock_ws):
        room = _room({"p1": "белый", "p2": "черный"})
        ws3 = AsyncMock()
        ws3.accept = AsyncMock()
        ws3.close = AsyncMock()

        with (
            patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room),
            patch("backend.ws_manager.set_room", new_callable=AsyncMock),
            patch("backend.ws_manager.record_ws_reject") as reject,
        ):
            ok = await cm.connect("room1", ws3, "p3")
        assert ok is False
        reject.assert_called_once_with("room_full")

    async def test_successful_join_records_connect(self, cm, mock_ws):
        room = _room()
        with (
            patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room),
            patch("backend.ws_manager.set_room", new_callable=AsyncMock),
            patch("backend.ws_manager.start_session", new_callable=AsyncMock),
            patch("backend.ws_manager.record_ws_connect") as connect,
        ):
            ok = await cm.connect("room1", mock_ws, "joiner")
        assert ok is True
        connect.assert_called_once_with()

    async def test_reconnect_records_connect_with_reason(self, cm, mock_ws):
        room = _room({"player-a": "белый"})
        with (
            patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room),
            patch("backend.ws_manager.set_room", new_callable=AsyncMock),
            patch("backend.ws_manager.disconnect_timers", {}),
            patch("backend.ws_manager.start_session", new_callable=AsyncMock),
            patch("backend.ws_manager.record_ws_connect") as connect,
        ):
            cm.connections["room1"] = {}
            ok = await cm.connect("room1", mock_ws, "player-a")
        assert ok is True
        connect.assert_called_once_with(reason="reconnect")

    async def test_disconnect_records_ws_disconnect(self, cm, mock_ws):
        cm.connections["room1"] = {"player-a": mock_ws}
        with (
            patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=_room({"player-a": "белый"})),
            patch("backend.ws_manager.set_room", new_callable=AsyncMock),
            patch("backend.ws_manager.end_session", new_callable=AsyncMock),
            patch("backend.ws_manager.record_ws_disconnect") as disconnect,
        ):
            await cm.disconnect("room1", mock_ws)
        disconnect.assert_called_once_with()


@pytest.mark.asyncio
class TestListRoomsEdgeCases:
    async def test_skips_private_ai_and_started_games(self):
        import json
        from backend.room_manager import list_rooms

        payloads = {
            "room:pub-wait": {
                "room_id": "pub-wait",
                "type": "public",
                "game_started": False,
                "time_control": 60,
                "increment": 0,
            },
            "room:pub-live": {
                "room_id": "pub-live",
                "type": "public",
                "game_started": True,
            },
            "room:priv": {
                "room_id": "priv",
                "type": "private",
                "game_started": False,
            },
            "room:ai": {
                "room_id": "ai1",
                "type": "ai",
                "game_started": False,
            },
        }

        async def fake_get_room(room_id: str):
            for payload in payloads.values():
                if payload["room_id"] == room_id:
                    return payload
            return None

        with patch(
            "backend.room_manager.get_waiting_public_room_ids",
            new_callable=AsyncMock,
            return_value=[p["room_id"] for p in payloads.values()],
        ):
            with patch("backend.room_manager.get_room", side_effect=fake_get_room):
                result = await list_rooms()

        ids = {r["room_id"] for r in result["rooms"]}
        assert ids == {"pub-wait"}
