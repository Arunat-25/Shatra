"""Подсказки отправляются только игроку на ходу, не в комнату."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.board_utils import keys_int_to_str
from backend.session import process_client_message
from backend.ws_manager import manager
from tests.server.disconnect_helpers import game_state as _game, pvp_room as _pvp_room


@pytest.fixture
def ws():
    mock = AsyncMock()
    mock.send_json = AsyncMock()
    return mock


class PvpState:
    def __init__(self, ws):
        self.game = _game()
        self.room = _pvp_room()
        self.ws = ws

    def __enter__(self):
        async def get_game_side_effect(rid):
            return self.game if rid == "room1" else None

        async def get_room_side_effect(rid):
            return self.room if rid == "room1" else None

        manager.connections["room1"] = {
            "p-white": self.ws,
            "p-black": AsyncMock(send_json=AsyncMock()),
        }
        self._patches = [
            patch("backend.session.messages.get_game", side_effect=get_game_side_effect),
            patch("backend.session.messages.get_room", side_effect=get_room_side_effect),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *args):
        for p in self._patches:
            p.stop()
        manager.connections.pop("room1", None)


def _hint_payload(game, *, color="белый", position="position53"):
    return {
        "board": keys_int_to_str(game["board"]),
        "movers_color": color,
        "position": position,
    }


@pytest.mark.asyncio
async def test_hint_sent_only_to_requester(ws):
    with PvpState(ws) as st:
        with patch("backend.session.messages.manager.send_to_room", AsyncMock()) as send_room:
            with patch("backend.session.messages.manager.send_to_player", AsyncMock()) as send_player:
                await process_client_message(
                    "room1", "p-white", _hint_payload(st.game), ws, is_ai_room=False
                )
                send_room.assert_not_called()
                send_player.assert_awaited_once()
                assert send_player.call_args[0][0] is ws
                assert "essential_positions" in send_player.call_args[0][1]


@pytest.mark.asyncio
async def test_hint_rejected_when_not_your_turn(ws):
    with PvpState(ws) as st:
        black_ws = manager.connections["room1"]["p-black"]
        with patch("backend.session.messages.manager.send_to_room", AsyncMock()) as send_room:
            with patch("backend.session.messages.manager.send_to_player", AsyncMock()) as send_player:
                await process_client_message(
                    "room1", "p-black", _hint_payload(st.game), black_ws, is_ai_room=False
                )
                send_room.assert_not_called()
                send_player.assert_awaited_once()
                payload = send_player.call_args[0][1]
                assert payload.get("status") == "error"
                assert payload.get("message_code") == "ws.not_your_turn"
