"""WS-протокол, разбор ходов, отклонение невалидных ходов."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.game_helpers import (
    apply_move_result,
    is_move_message,
    is_hint_request,
    is_rejected_move,
    parse_client_event,
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
            ({"type": "resign"}, False),
            ({"board": "not-a-dict", "movers_color": "белый"}, False),
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
