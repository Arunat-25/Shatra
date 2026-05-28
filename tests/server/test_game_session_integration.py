"""Интеграционные тесты process_client_message и связанных потоков."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.board_utils import get_starting_board, keys_int_to_str
from backend.game_session import (
    process_client_message,
    _start_ai_game,
    _handle_disconnect,
)
from backend.ws_manager import handle_player2_join, _delete_room_after_grace, manager


def _pvp_room():
    return {
        "room_id": "room1",
        "type": "public",
        "game_started": True,
        "players": {"p-white": "белый", "p-black": "черный"},
        "time_control": None,
        "rematch_ready": [],
    }


def _game(**extra):
    g = {
        "board": get_starting_board(),
        "mover": "белый",
        "game_over": False,
        "move_history": [],
        "pending_batyr_captures": [],
        "position_history": {},
        "moves_with_two_biys": 0,
    }
    g.update(extra)
    return g


def _legal_white_move_payload(game):
    return {
        "board": keys_int_to_str(game["board"]),
        "movers_color": "белый",
        "move_from": "position53",
        "move_to": "position46",
    }


@pytest.fixture
def ws():
    mock = AsyncMock()
    mock.send_json = AsyncMock()
    return mock


class PvpState:
    """Хранилище состояния + контекст моков Redis для async-тестов."""

    def __init__(self, ws):
        self.game = _game()
        self.room = _pvp_room()
        self.ws = ws

    def __enter__(self):
        async def get_game_side_effect(rid):
            return self.game if rid == "room1" else None

        async def get_room_side_effect(rid):
            return self.room if rid == "room1" else None

        async def set_game_side_effect(rid, g):
            self.game = dict(g)

        async def set_room_side_effect(rid, r):
            self.room = dict(r)

        manager.connections["room1"] = {
            "p-white": self.ws,
            "p-black": AsyncMock(send_json=AsyncMock()),
        }
        self._patches = [
            patch("backend.game_session.get_game", side_effect=get_game_side_effect),
            patch("backend.game_session.get_room", side_effect=get_room_side_effect),
            patch("backend.game_session.set_game", side_effect=set_game_side_effect),
            patch("backend.game_session.set_room", side_effect=set_room_side_effect),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *args):
        for p in self._patches:
            p.stop()
        manager.connections.pop("room1", None)


@pytest.fixture
def pvp_state(ws):
    return PvpState(ws)


@pytest.mark.asyncio
class TestProcessClientMessageDraw:
    async def test_mutual_draw_agreement(self, pvp_state, ws):
        with pvp_state as st:
            st.game["draw_offer_from"] = "белый"
            st.room["rematch_ready"] = ["x"]

            with patch("backend.game_session.manager.send_to_room", new_callable=AsyncMock) as broadcast:
                ok = await process_client_message(
                    "room1", "p-black", {"type": "offer_draw"}, ws, is_ai_room=False
                )

            assert ok is True
            assert st.game["game_over"] is True
            assert st.game["reason"] == "draw_agreed"
            assert "draw_offer_from" not in st.game
            assert st.room["rematch_ready"] == []
            broadcast.assert_called_once()
            assert broadcast.call_args[0][1]["reason"] == "draw_agreed"

    async def test_double_offer_from_same_player_is_noop(self, pvp_state, ws):
        with pvp_state as st:
            st.game["draw_offer_from"] = "белый"

            with patch("backend.game_session.manager.send_to_player", new_callable=AsyncMock) as send:
                await process_client_message(
                    "room1", "p-white", {"type": "offer_draw"}, ws, is_ai_room=False
                )

            send.assert_called_once()
            assert "уже предложили" in send.call_args[0][1]["message"].lower()

    async def test_resign_after_game_over_is_noop(self, pvp_state, ws):
        with pvp_state as st:
            st.game["game_over"] = True

            with patch("backend.game_session.manager.send_to_room", new_callable=AsyncMock) as broadcast:
                await process_client_message(
                    "room1", "p-white", {"type": "resign"}, ws, is_ai_room=False
                )

            broadcast.assert_not_called()


@pytest.mark.asyncio
class TestProcessClientMessageMoves:
    async def test_move_after_game_over_sends_error_only_to_sender(self, pvp_state, ws):
        with pvp_state as st:
            st.game["game_over"] = True

            with patch("backend.game_session._send_ws_error", new_callable=AsyncMock) as err:
                with patch("backend.game_session.manager.send_to_room", new_callable=AsyncMock) as room:
                    await process_client_message(
                        "room1",
                        "p-white",
                        _legal_white_move_payload(st.game),
                        ws,
                        is_ai_room=False,
                    )

            err.assert_called_once()
            assert "окончена" in err.call_args[0][1].lower()
            room.assert_not_called()

    async def test_move_clears_draw_offer(self, pvp_state, ws):
        with pvp_state as st:
            st.game["draw_offer_from"] = "черный"

            with patch("backend.game_session._decline_draw_offer", new_callable=AsyncMock) as decline:
                with patch("backend.game_session.apply_move_result", new_callable=AsyncMock) as apply:
                    apply.return_value = {"message": "ok", "desk": {}}
                    with patch("backend.game_session.logic.handle_event") as handle:
                        from game_engine.models import GameEventResult
                        handle.return_value = GameEventResult(
                            message="",
                            movers_color="черный",
                            updated_positions=dict(st.game["board"]),
                        )
                        await process_client_message(
                            "room1",
                            "p-white",
                            _legal_white_move_payload(st.game),
                            ws,
                            is_ai_room=False,
                        )

            decline.assert_called_once()

    async def test_rejected_move_not_broadcast(self, pvp_state, ws):
        with pvp_state as st:
            with patch("backend.game_session._send_ws_error", new_callable=AsyncMock) as err:
                with patch("backend.game_session.manager.send_to_room", new_callable=AsyncMock) as room:
                    await process_client_message(
                        "room1",
                        "p-black",
                        {
                            "board": keys_int_to_str(st.game["board"]),
                            "movers_color": "черный",
                            "move_from": "position12",
                            "move_to": "position20",
                        },
                        ws,
                        is_ai_room=False,
                    )

            err.assert_called_once()
            room.assert_not_called()


@pytest.mark.asyncio
class TestProcessClientMessageAi:
    async def test_offer_draw_declined_by_bot(self, ws):
        with PvpState(ws) as st:
            st.room = {
                "room_id": "ai1",
                "type": "ai",
                "players": {"human": "черный"},
            }
            manager.connections["room1"] = {"human": ws}

            with patch("backend.game_session.manager.send_to_player", new_callable=AsyncMock) as send:
                await process_client_message(
                    "room1", "human", {"type": "offer_draw"}, ws, is_ai_room=True
                )

            send.assert_called_once()
            assert "бот" in send.call_args[0][1]["message"].lower()


@pytest.mark.asyncio
class TestProcessClientMessageRematch:
    async def test_both_ready_starts_rematch(self, pvp_state, ws):
        with pvp_state as st:
            st.game["game_over"] = True
            st.room["rematch_ready"] = ["p-white"]

            with patch("backend.game_session._start_rematch", new_callable=AsyncMock) as start:
                with patch("backend.game_session._broadcast_rematch_status", new_callable=AsyncMock):
                    await process_client_message(
                        "room1", "p-black", {"type": "request_rematch"}, ws, is_ai_room=False
                    )

            start.assert_called_once()


@pytest.mark.asyncio
class TestAiGameStart:
    async def test_human_black_triggers_ai_opening(self, ws):
        room = {
            "room_id": "ai-room",
            "type": "ai",
            "players": {"human": "черный"},
            "time_control": None,
        }
        game_after_init = _game()

        with patch(
            "backend.game_session.get_game",
            new_callable=AsyncMock,
            side_effect=[None, game_after_init],
        ):
            with patch("backend.game_session.init_game", new_callable=AsyncMock):
                with patch("backend.game_session.set_room", new_callable=AsyncMock):
                    with patch(
                        "backend.game_session.build_game_started_response",
                        return_value={"status": "game_started"},
                    ):
                        with patch(
                            "backend.game_session.manager.send_to_player",
                            new_callable=AsyncMock,
                        ):
                            with patch(
                                "backend.game_session.handle_ai_move",
                                new_callable=AsyncMock,
                            ) as ai_move:
                                await _start_ai_game("ai-room", ws, room, "черный")

        ai_move.assert_called_once()


@pytest.mark.asyncio
class TestHandleDisconnectRematch:
    async def test_disconnect_cancels_rematch_and_notifies(self, ws):
        room = _pvp_room()
        room["rematch_ready"] = ["p-white", "p-black"]
        game = _game(game_over=True)
        opponent_ws = AsyncMock()

        with patch("backend.game_session.manager") as mgr:
            mgr.disconnect = AsyncMock()
            mgr.get_client_id = MagicMock(return_value="p-white")
            mgr.get_opponent_ws = MagicMock(return_value=opponent_ws)
            with patch("backend.game_session.get_game", new_callable=AsyncMock, return_value=game):
                with patch("backend.game_session.get_room", new_callable=AsyncMock, return_value=room):
                    with patch("backend.game_session.set_room", new_callable=AsyncMock) as set_room:
                        await _handle_disconnect("room1", ws, is_ai_room=False)

        assert room["rematch_ready"] == []
        set_room.assert_called_once()
        opponent_ws.send_json.assert_called_once()
        assert opponent_ws.send_json.call_args[0][0]["status"] == "rematch_cancelled"


@pytest.mark.asyncio
class TestGraceRoomDeletion:
    async def test_deletes_empty_waiting_room_after_grace(self):
        room = {"room_id": "g1", "game_started": False, "type": "public"}

        with patch("backend.ws_manager.asyncio.sleep", new_callable=AsyncMock):
            with patch("backend.ws_manager.get_room", new_callable=AsyncMock, return_value=room):
                with patch("backend.ws_manager.delete_game", new_callable=AsyncMock) as dg:
                    with patch("backend.ws_manager.delete_room", new_callable=AsyncMock) as dr:
                        manager.connections.pop("g1", None)
                        await _delete_room_after_grace("g1", 0.01)

        dg.assert_called_once()
        dr.assert_called_once()

    async def test_skips_deletion_if_someone_reconnected(self):
        room = {"room_id": "g2", "game_started": False, "type": "public"}
        manager.connections["g2"] = {"c": AsyncMock()}

        with patch("backend.ws_manager.asyncio.sleep", new_callable=AsyncMock):
            with patch("backend.ws_manager.delete_game", new_callable=AsyncMock) as dg:
                await _delete_room_after_grace("g2", 0.01)

        dg.assert_not_called()
        manager.connections.pop("g2", None)


@pytest.mark.asyncio
class TestHandlePlayer2Join:
    async def test_starts_game_for_both_players(self):
        room = {
            "room_id": "j1",
            "type": "public",
            "game_started": False,
            "players": {"a": "белый", "b": "черный"},
            "time_control": 60,
        }
        game = _game()
        ws_a = AsyncMock()
        ws_b = AsyncMock()

        with patch("backend.ws_manager.init_game", new_callable=AsyncMock):
            with patch("backend.ws_manager.get_game", new_callable=AsyncMock, return_value=game):
                with patch("backend.ws_manager.set_room", new_callable=AsyncMock):
                    with patch("backend.ws_manager.manager") as mgr:
                        mgr.get_ws = MagicMock(side_effect=lambda rid, cid: ws_a if cid == "a" else ws_b)
                        mgr.send_to_player = AsyncMock()
                        with patch("backend.ws_manager.game_timers", {}):
                            with patch("backend.ws_manager.asyncio.create_task") as create_task:
                                def close_coro(coro):
                                    coro.close()
                                    return MagicMock(done=MagicMock(return_value=False))

                                create_task.side_effect = close_coro
                                await handle_player2_join("j1", room)

        assert room["game_started"] is True
        assert mgr.send_to_player.call_count == 2
        create_task.assert_called_once()
