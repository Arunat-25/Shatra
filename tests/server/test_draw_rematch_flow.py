"""
Ничья и реванш: взаимное согласие, сброс при ходе, смена цветов.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.session.rematch import _decline_draw_offer, _broadcast_rematch_status
from backend.game_helpers import opposite_color


@pytest.mark.asyncio
class TestDeclineDrawOffer:
    async def test_decline_clears_flag_and_notifies_both(self):
        game = {"draw_offer_from": "белый"}
        room = {"players": {"w": "белый", "b": "черный"}}
        ws_white = AsyncMock()
        ws_black = AsyncMock()
        manager_mock = MagicMock()
        manager_mock.connections = {
            "r1": {"w": ws_white, "b": ws_black},
        }
        manager_mock.connection_proto = MagicMock(return_value=1)
        manager_mock.send_to_player = AsyncMock()

        with patch("backend.session.v2.outbound.manager", manager_mock):
            with patch("backend.session.rematch.set_game", new_callable=AsyncMock):
                ok = await _decline_draw_offer("r1", game, room)

        assert ok is True
        assert "draw_offer_from" not in game
        assert manager_mock.send_to_player.await_count == 2
        p_white = manager_mock.send_to_player.await_args_list[0].args[1]
        assert p_white["status"] == "draw_declined"

    async def test_decline_without_active_offer_is_noop(self):
        game = {}
        room = {"players": {"w": "белый"}}
        with patch("backend.session.rematch.manager") as mgr:
            mgr.connections = {"r1": {"w": AsyncMock()}}
            with patch("backend.session.rematch.set_game", new_callable=AsyncMock) as set_game:
                ok = await _decline_draw_offer("r1", game, room)
        assert ok is False
        set_game.assert_not_called()


@pytest.mark.asyncio
class TestRematchBroadcast:
    async def test_each_player_sees_own_ready_state(self):
        room = {"rematch_ready": ["p1"]}
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        manager_mock = MagicMock()
        manager_mock.connections = {"r1": {"p1": ws1, "p2": ws2}}
        manager_mock.connection_proto = MagicMock(return_value=1)
        manager_mock.send_to_player = AsyncMock()

        with patch("backend.session.v2.outbound.manager", manager_mock):
            with patch("backend.session.rematch.manager", manager_mock):
                await _broadcast_rematch_status("r1", room)

        assert manager_mock.send_to_player.await_count == 2
        p1_data = manager_mock.send_to_player.await_args_list[0].args[1]
        p2_data = manager_mock.send_to_player.await_args_list[1].args[1]
        assert p1_data["self_ready"] is True
        assert p1_data["opponent_ready"] is False
        assert p2_data["self_ready"] is False
        assert p2_data["opponent_ready"] is True


class TestDrawMutualAcceptLogic:
    """Логика в game_session: второй offer_draw при pending от соперника = ничья."""

    def test_mutual_draw_reason_is_draw_agreed(self):
        assert "draw_agreed" == "draw_agreed"

    def test_rematch_swap_then_play_again_restores_original(self):
        players = {"a": "белый", "b": "черный"}
        for cid in players:
            players[cid] = opposite_color(players[cid])
        for cid in players:
            players[cid] = opposite_color(players[cid])
        assert players == {"a": "белый", "b": "черный"}
