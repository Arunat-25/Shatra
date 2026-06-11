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


def _hint_payload(*, position="position53"):
    return {"position": position}


def _legacy_hint_payload(game, *, color="белый", position="position53"):
    """Old clients sent board; server must ignore it for hints."""
    return {
        "position": position,
        "board": keys_int_to_str(game["board"]),
        "movers_color": color,
    }


@pytest.mark.asyncio
async def test_hint_sent_only_to_requester(ws):
    with PvpState(ws) as st:
        with patch("backend.session.messages.manager.send_to_room", AsyncMock()) as send_room:
            with patch("backend.session.messages.manager.send_to_player", AsyncMock()) as send_player:
                await process_client_message(
                    "room1", "p-white", _hint_payload(), ws, is_ai_room=False
                )
                send_room.assert_not_called()
                send_player.assert_awaited_once()
                assert send_player.call_args[0][0] is ws
                payload = send_player.call_args[0][1]
                assert "essential_positions" in payload
                assert payload.get("hint_position") == 53


@pytest.mark.asyncio
async def test_hint_rejected_when_not_your_turn(ws):
    with PvpState(ws) as st:
        black_ws = manager.connections["room1"]["p-black"]
        with patch("backend.session.messages.manager.send_to_room", AsyncMock()) as send_room:
            with patch("backend.session.messages.manager.send_to_player", AsyncMock()) as send_player:
                await process_client_message(
                    "room1", "p-black", _hint_payload(), black_ws, is_ai_room=False
                )
                send_room.assert_not_called()
                send_player.assert_awaited_once()
                payload = send_player.call_args[0][1]
                assert payload.get("status") == "error"
                assert payload.get("message_code") == "ws.not_your_turn"


@pytest.mark.asyncio
async def test_hint_rejected_when_game_over(ws):
    with PvpState(ws) as st:
        st.game["game_over"] = True
        with patch("backend.session.messages.manager.send_to_room", AsyncMock()):
            with patch("backend.session.messages.manager.send_to_player", AsyncMock()) as send_player:
                await process_client_message(
                    "room1", "p-white", _hint_payload(), ws, is_ai_room=False
                )
                payload = send_player.call_args[0][1]
                assert payload.get("status") == "error"
                assert payload.get("message_code") == "ws.game_over"


@pytest.mark.asyncio
async def test_hint_invalid_position_returns_error(ws):
    with PvpState(ws):
        with patch("backend.session.messages.manager.send_to_room", AsyncMock()):
            with patch("backend.session.messages.manager.send_to_player", AsyncMock()) as send_player:
                await process_client_message(
                    "room1", "p-white", {"position": "not-a-cell"}, ws, is_ai_room=False
                )
                payload = send_player.call_args[0][1]
                assert payload.get("status") == "error"
                assert payload.get("message_code") == "ws.invalid_move_data"


@pytest.mark.asyncio
async def test_hint_for_different_cell_sets_hint_position(ws):
    with PvpState(ws):
        with patch("backend.session.messages.manager.send_to_room", AsyncMock()):
            with patch("backend.session.messages.manager.send_to_player", AsyncMock()) as send_player:
                await process_client_message(
                    "room1", "p-white", _hint_payload(position="position10"), ws, is_ai_room=False
                )
                payload = send_player.call_args[0][1]
                assert payload.get("hint_position") == 10
                assert "essential_positions" in payload


@pytest.mark.asyncio
async def test_hint_during_mandatory_capture_uses_server_chain_state(ws):
    from game_engine.game_logic import logic

    from backend.game_helpers import build_hint_event_from_game

    with PvpState(ws) as st:
        st.game["board"] = {
            19: "белый бий",
            26: "черная шатра",
            33: None,
            35: None,
        }
        st.game["pending_mandatory_position"] = 19
        event = build_hint_event_from_game(st.game, 19)
        expected = logic.handle_event(
            event,
            batyr_captured_this_turn=st.game.get("pending_batyr_captures"),
        )
        with patch("backend.session.messages.manager.send_to_room", AsyncMock()):
            with patch("backend.session.messages.manager.send_to_player", AsyncMock()) as send_player:
                await process_client_message(
                    "room1", "p-white", _hint_payload(position="position19"), ws, is_ai_room=False
                )
                payload = send_player.call_args[0][1]
                assert payload["essential_positions"] == expected.essential_positions
                assert payload.get("hint_position") == 19


@pytest.mark.asyncio
async def test_legacy_hint_payload_still_works(ws):
    with PvpState(ws) as st:
        with patch("backend.session.messages.manager.send_to_room", AsyncMock()):
            with patch("backend.session.messages.manager.send_to_player", AsyncMock()) as send_player:
                await process_client_message(
                    "room1",
                    "p-white",
                    _legacy_hint_payload(st.game, color="черный"),
                    ws,
                    is_ai_room=False,
                )
                payload = send_player.call_args[0][1]
                assert payload.get("hint_position") == 53
                assert "essential_positions" in payload


@pytest.mark.asyncio
async def test_full_move_payload_not_routed_as_hint(ws):
    with PvpState(ws) as st:
        move_payload = {
            "board": keys_int_to_str(st.game["board"]),
            "movers_color": "белый",
            "move_from": "position53",
            "move_to": "position32",
            "position": "position53",
        }
        with patch("backend.session.messages.manager.send_to_room", AsyncMock()) as send_room:
            with patch("backend.session.messages.manager.send_to_player", AsyncMock()) as send_player:
                with patch("backend.session.messages.apply_move_result", AsyncMock(return_value={"desk": {}})) as apply_move:
                    await process_client_message(
                        "room1", "p-white", move_payload, ws, is_ai_room=False
                    )
                    apply_move.assert_awaited()
                    send_room.assert_awaited()
                    send_player.assert_not_called()
                    assert send_player.call_args_list == []


@pytest.mark.asyncio
async def test_hint_uses_server_board_not_client_board(ws):
    from game_engine.hints import get_hints

    with PvpState(ws) as st:
        server_hints = get_hints(st.game["board"], "белый", 53)
        stale_board = keys_int_to_str(st.game["board"])
        stale_board["position53"] = None
        payload = {
            "position": "position53",
            "board": stale_board,
            "movers_color": "черный",
        }
        with patch("backend.session.messages.manager.send_to_room", AsyncMock()):
            with patch("backend.session.messages.manager.send_to_player", AsyncMock()) as send_player:
                await process_client_message(
                    "room1", "p-white", payload, ws, is_ai_room=False
                )
                response = send_player.call_args[0][1]
                assert response["essential_positions"] == server_hints.essential_positions
                assert response.get("hint_position") == 53
