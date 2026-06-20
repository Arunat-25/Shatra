"""v2 client sync must mark snapshot as resync (no game-start feedback)."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.session.v2.messages import _process_v2_client_message_locked


@pytest.mark.asyncio
async def test_sync_snapshot_includes_resync_flag():
    game = {"board": {}, "mover": "белый", "ply": 2, "move_history": []}
    room = {"player_meta": {"c1": {"color": "белый"}}}
    ws = AsyncMock()
    sent = []

    async def capture_send(_ws, payload):
        sent.append(payload)

    with patch("backend.session.v2.messages.get_game", AsyncMock(return_value=game)):
        with patch("backend.session.v2.messages.get_room", AsyncMock(return_value=room)):
            with patch("backend.session.v2.messages.get_player_color", return_value="белый"):
                with patch("backend.session.v2.messages._send_v2", side_effect=capture_send):
                    ok = await _process_v2_client_message_locked(
                        "room1",
                        "c1",
                        {"v": 2, "t": "sync", "ply": 2},
                        ws,
                        is_ai_room=False,
                    )

    assert ok is True
    assert len(sent) == 1
    assert sent[0]["t"] == "snapshot"
    assert sent[0]["resync"] is True
