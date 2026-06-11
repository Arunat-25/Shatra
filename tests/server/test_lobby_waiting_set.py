"""Lobby waiting-public Redis SET maintenance."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.room_manager import list_rooms


@pytest.mark.asyncio
async def test_list_rooms_does_not_scan_all_room_keys():
    room = {
        "room_id": "lobby001",
        "type": "public",
        "game_started": False,
        "created_at": "2026-01-01T00:00:00",
        "players": {"creator": "белый"},
    }

    with (
        patch(
            "backend.room_manager.get_waiting_public_room_ids",
            AsyncMock(return_value=["lobby001"]),
        ),
        patch("backend.room_manager.get_room", AsyncMock(return_value=room)),
        patch("backend.room_manager.count_active_games", AsyncMock(return_value=0)),
        patch("backend.state.scan_keys") as scan,
    ):
        result = await list_rooms()

    scan.assert_not_called()
    assert any(r["room_id"] == "lobby001" for r in result["rooms"])
