"""v2 control message outbound shapes (draw / rematch / cancel)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.session.v2.outbound import send_control_v1, broadcast_control_v1
from backend.session.v2.protocol import PROTO_VERSION


def _mgr(proto=PROTO_VERSION):
    ws = AsyncMock()
    mgr = MagicMock()
    mgr.connection_proto = MagicMock(return_value=proto)
    mgr.send_to_player = AsyncMock()
    mgr.connections = {"r1": {"p1": ws, "p2": ws}}
    return mgr, ws


@pytest.mark.asyncio
@pytest.mark.parametrize("status,extra", [
    ("draw_offered", {"by": "белый", "message_code": "draw.you_offered"}),
    ("draw_declined", {"message_code": "draw.opponent_declined"}),
    ("rematch_status", {"self_ready": True, "opponent_ready": False}),
    ("rematch_cancelled", {"message_code": "rematch.opponent_left"}),
    ("game_cancelled", {"message_code": "cancel.opponent"}),
    ("opponent_reconnected", {}),
])
async def test_v2_control_wrapped(status, extra):
    mgr, ws = _mgr()
    payload = {"status": status, **extra}

    with patch("backend.session.v2.outbound.manager", mgr):
        await send_control_v1("r1", "p1", ws, payload)

    sent = mgr.send_to_player.await_args.args[1]
    assert sent["v"] == PROTO_VERSION
    assert sent["t"] == status
    assert sent.get("status") is None
    for key, value in extra.items():
        assert sent[key] == value


@pytest.mark.asyncio
async def test_v1_control_plain_shape():
    mgr, ws = _mgr(proto=1)
    payload = {"status": "rematch_status", "self_ready": False, "opponent_ready": True}

    with patch("backend.session.v2.outbound.manager", mgr):
        await send_control_v1("r1", "p1", ws, payload)

    sent = mgr.send_to_player.await_args.args[1]
    assert sent["status"] == "rematch_status"
    assert sent.get("v") is None


@pytest.mark.asyncio
async def test_broadcast_builds_per_client_payload():
    mgr, _ = _mgr()
    seen = []

    def build(cid):
        seen.append(cid)
        return {"status": "draw_offered", "by": "белый", "message_code": "draw.opponent_offers"}

    with patch("backend.session.v2.outbound.manager", mgr):
        await broadcast_control_v1("r1", build)

    assert set(seen) == {"p1", "p2"}
    assert mgr.send_to_player.await_count == 2
