"""v2 WebSocket clients must receive wrapped control payloads."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.session.rematch import _broadcast_rematch_status, _start_rematch
from backend.session.v2.outbound import send_control_v1
from backend.session.v2.protocol import PROTO_VERSION


def _manager_mock(*, proto: int = PROTO_VERSION):
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    mgr = MagicMock()
    mgr.connections = {"r1": {"p1": ws1, "p2": ws2}}
    mgr.connection_proto = MagicMock(return_value=proto)
    mgr.send_to_player = AsyncMock()
    mgr.send_join_state = AsyncMock()
    return mgr, ws1, ws2


@pytest.mark.asyncio
class TestV2ControlOutbound:
    async def test_rematch_status_wrapped_for_v2(self):
        mgr, ws1, ws2 = _manager_mock(proto=PROTO_VERSION)
        room = {"rematch_ready": ["p1"]}

        with patch("backend.session.v2.outbound.manager", mgr):
            await _broadcast_rematch_status("r1", room)

        assert mgr.send_to_player.await_count == 2
        p1_payload = mgr.send_to_player.await_args_list[0].args[1]
        assert p1_payload["v"] == PROTO_VERSION
        assert p1_payload["t"] == "rematch_status"
        assert p1_payload["self_ready"] is True
        assert p1_payload["opponent_ready"] is False
        assert "status" not in p1_payload

    async def test_rematch_status_plain_for_v1(self):
        mgr, _, _ = _manager_mock(proto=1)
        room = {"rematch_ready": ["p1"]}

        with patch("backend.session.v2.outbound.manager", mgr):
            await _broadcast_rematch_status("r1", room)

        p1_payload = mgr.send_to_player.await_args_list[0].args[1]
        assert p1_payload["status"] == "rematch_status"
        assert p1_payload.get("v") is None

    async def test_start_rematch_uses_snapshot_for_v2(self):
        mgr, _, _ = _manager_mock(proto=PROTO_VERSION)
        room = {
            "players": {"p1": "белый", "p2": "черный"},
            "rematch_ready": ["p1", "p2"],
        }

        with patch("backend.session.v2.outbound.manager", mgr):
            with patch("backend.session.rematch.manager", mgr):
                with patch("backend.session.rematch.stop_game_timer"):
                    with patch("backend.session.rematch._archive_finished_game_locked", new_callable=AsyncMock):
                        with patch("backend.session.rematch.init_game", new_callable=AsyncMock):
                            with patch(
                                "backend.session.rematch.get_game",
                                new_callable=AsyncMock,
                                return_value={"board": {}, "mover": "белый"},
                            ):
                                with patch("backend.session.rematch.set_room", new_callable=AsyncMock):
                                    with patch("backend.session.rematch.mark_game_started"):
                                        await _start_rematch("r1", room)

        assert mgr.send_join_state.await_count == 2
        mgr.send_to_player.assert_not_called()

    async def test_send_control_v1_draw_declined(self):
        mgr, ws1, _ = _manager_mock(proto=PROTO_VERSION)
        payload = {"status": "draw_declined", "message_code": "draw.opponent_declined"}

        with patch("backend.session.v2.outbound.manager", mgr):
            await send_control_v1("r1", "p1", ws1, payload)

        sent = mgr.send_to_player.await_args.args[1]
        assert sent["t"] == "draw_declined"
        assert sent["message_code"] == "draw.opponent_declined"
