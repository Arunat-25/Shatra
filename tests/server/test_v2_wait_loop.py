"""v2 host wait loop must process client messages (not swallow resign)."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from backend.session.v2.endpoint import _wait_for_second_player_v2


@pytest.mark.asyncio
async def test_wait_loop_dispatches_control_messages_before_game_started_flag():
    room_id = "wait-loop"
    client_id = "host-id"
    websocket = AsyncMock()
    room_data = {"game_started": False, "type": "public"}
    resign = {"v": 2, "t": "resign"}

    room_states = [
        {"game_started": False, "type": "public"},
        {"game_started": True, "type": "public"},
    ]

    async def receive_json():
        return resign

    websocket.receive_json = receive_json

    process = AsyncMock(return_value=True)

    with patch("backend.session.v2.endpoint.get_room", AsyncMock(side_effect=room_states)):
        with patch("backend.session.v2.endpoint.manager.send_to_player", new_callable=AsyncMock):
            with patch("backend.session.v2.endpoint.build_players_info", return_value=[]):
                with patch("backend.session.v2.endpoint.process_v2_client_message", process):
                    result = await _wait_for_second_player_v2(
                        websocket,
                        room_id,
                        room_data,
                        client_id,
                        is_ai_room=False,
                    )

    assert result is not None
    assert result.get("game_started") is True
    process.assert_awaited_once_with(
        room_id, client_id, resign, websocket, is_ai_room=False
    )


@pytest.mark.asyncio
async def test_wait_loop_polls_room_without_blocking_on_timeout():
    room_id = "wait-timeout"
    websocket = AsyncMock()
    room_data = {"game_started": False, "type": "public"}

    async def slow_receive():
        await asyncio.sleep(10)
        return {}

    websocket.receive_json = slow_receive

    with patch("backend.session.v2.endpoint.get_room", AsyncMock(return_value={"game_started": True})):
        with patch("backend.session.v2.endpoint.manager.send_to_player", new_callable=AsyncMock):
            with patch("backend.session.v2.endpoint.build_players_info", return_value=[]):
                with patch("backend.session.v2.endpoint.process_v2_client_message", new_callable=AsyncMock):
                    result = await asyncio.wait_for(
                        _wait_for_second_player_v2(
                            websocket,
                            room_id,
                            room_data,
                            "host",
                            is_ai_room=False,
                        ),
                        timeout=1.5,
                    )

    assert result.get("game_started") is True
