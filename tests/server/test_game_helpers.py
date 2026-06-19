"""WS-протокол, разбор ходов, отклонение невалидных ходов."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.game_helpers import (
    apply_move_result,
    build_hint_event_from_game,
    is_move_message,
    is_hint_request,
    is_rejected_move,
    parse_client_event,
    persist_pending_mandatory_position,
    ws_error_payload,
    build_game_started_response,
    _norm_board_keys,
)
from backend.ws_control_handlers import CONTROL_MESSAGE_TYPES
from game_engine.message_codes import MOVE_WRONG_COLOR
from game_engine.models import GameEventResult


class TestWsErrorPayload:
    def test_shape(self):
        assert ws_error_payload("room.not_found") == {"status": "error", "message_code": "room.not_found"}


class TestIsMoveMessage:
    @pytest.mark.parametrize(
        "payload,expected",
        [
            ({"board": {}, "movers_color": "белый"}, True),
            ({"board": {}, "movers_color": "белый", "position": "position53"}, True),
            ({"type": "resign"}, False),
            ({"board": "not-a-dict", "movers_color": "белый"}, False),
            ({"position": "position53"}, False),
            (None, False),
        ],
    )
    def test_move_detection(self, payload, expected):
        assert is_move_message(payload) is expected


class TestParseClientEvent:
    def test_parses_move_positions(self):
        data = {
            "board": {"11": "черная шатра"},
            "movers_color": "черный",
            "move_from": "position11",
            "move_to": "position19",
        }
        event, raw_from, raw_to = parse_client_event(data)
        assert event.mover_color == "черный"
        assert raw_from == 11
        assert raw_to == 19

    def test_parses_hint_position(self):
        data = {
            "board": {"11": "черная шатра"},
            "movers_color": "черный",
            "position": "position11",
        }
        event, raw_from, raw_to = parse_client_event(data)
        assert event.position == 11
        assert raw_from is None

    def test_missing_board(self):
        with pytest.raises(ValueError, match="missing_board"):
            parse_client_event({"movers_color": "белый"})

    def test_missing_mover(self):
        with pytest.raises(ValueError, match="missing_mover"):
            parse_client_event({"board": {}})


class TestIsRejectedMove:
    def test_rejected_illegal_move(self):
        board = {11: "черная шатра"}
        result = GameEventResult(
            message_code=MOVE_WRONG_COLOR,
            movers_color="черный",
            updated_positions=dict(board),
        )
        assert is_rejected_move(result, board, 11, 19) is True

    def test_pass_is_not_rejected(self):
        board = {11: "черная шатра"}
        result = GameEventResult(message_code="", movers_color="белый", updated_positions=dict(board))
        assert is_rejected_move(result, board, 0, 0) is False

    def test_hint_with_essential_not_rejected(self):
        board = {11: "черная шатра"}
        result = GameEventResult(
            essential_positions=[19],
            updated_positions=dict(board),
        )
        assert is_rejected_move(result, board, None, None) is False


class TestBuildHintEventFromGame:
    def test_uses_server_game_state(self):
        game = {
            "board": {53: "белая шатра"},
            "mover": "белый",
            "pending_mandatory_position": 48,
        }
        event = build_hint_event_from_game(game, 53)
        assert event.position == 53
        assert event.mover_color == "белый"
        assert event.positions[53] == "белая шатра"
        assert event.position_for_mandatory_capture == 48


class TestIsHintRequest:
    def test_position_without_move_is_hint(self):
        from game_engine.models import GameEvent

        event = GameEvent(positions={11: "x"}, mover_color="белый", position=11)
        assert is_hint_request(None, None, event) is True

    def test_move_is_not_hint(self):
        from game_engine.models import GameEvent

        event = GameEvent(
            positions={11: "x"}, mover_color="белый", from_pos=11, to_pos=19, position=None
        )
        assert is_hint_request(11, 19, event) is False


class TestNormBoardKeys:
    def test_string_keys_become_int(self):
        assert _norm_board_keys({"11": "x", 12: "y"}) == {11: "x", 12: "y"}


class TestPersistPendingMandatoryPosition:
    def test_only_same_player_chain_is_persisted(self):
        from game_engine.game_logic import logic
        from game_engine.models import GameEvent
        from tests.helpers.engine_boards import empty_board

        board = empty_board()
        board.update({20: "белая шатра", 28: "черная шатра", 36: None, 44: "черная шатра"})
        result = logic.handle_event(
            GameEvent(positions=board, mover_color="белый", from_pos=20, to_pos=36)
        )
        game = {"mover": "белый"}
        persist_pending_mandatory_position(game, result, prev_mover="белый")
        assert game["pending_mandatory_position"] == 36

        persist_pending_mandatory_position(game, result, prev_mover="черный")
        assert "pending_mandatory_position" not in game


class TestBuildGameStartedResponse:
    def test_includes_color_timer_and_terminal_state(self, game_in_progress, sample_room_data):
        game_in_progress["game_over"] = True
        game_in_progress["winner"] = "белый"
        game_in_progress["reason"] = "resign"
        resp = build_game_started_response(game_in_progress, sample_room_data, "черный")
        assert resp["status"] == "game_started"
        assert resp["your_color"] == "черный"
        assert resp["time_control"] == 300
        assert resp["time"]["белый"] == 300.0
        assert resp["game_over"] is True
        assert resp["reason"] == "resign"

    def test_no_timer_when_untimed(self, game_in_progress, sample_room_data):
        sample_room_data["time_control"] = None
        resp = build_game_started_response(game_in_progress, sample_room_data, "белый")
        assert "time" not in resp
        assert "time_control" not in resp


class TestControlMessageTypes:
    def test_known_types_for_session_router(self):
        assert CONTROL_MESSAGE_TYPES == frozenset({
            "request_rematch",
            "decline_draw",
            "offer_draw",
            "resign",
            "cancel_game",
        })


@pytest.mark.asyncio
class TestApplyMoveResultReason:
    async def test_engine_win_sets_biy_wins_not_unknown(self, game_in_progress, sample_room_data):
        room_id = sample_room_data["room_id"]
        result = GameEventResult(
            message_code="turn.now",
            updated_positions=game_in_progress["board"],
            movers_color="черный",
            game_over=True,
            winner_color="белый",
        )

        with (
            patch("backend.game_helpers.get_room", AsyncMock(return_value=sample_room_data)),
            patch("backend.game_helpers.set_room", AsyncMock()),
            patch("backend.game_helpers.set_game", AsyncMock()),
            patch("backend.game_archive.on_game_finished", AsyncMock()),
            patch("backend.timers.stop_game_timer"),
        ):
            response = await apply_move_result(
                room_id, game_in_progress, result, "белый", 53, 46,
            )

        assert game_in_progress["reason"] == "biy_wins"
        assert response["reason"] == "biy_wins"
