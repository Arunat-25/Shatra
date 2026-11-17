"""Tests for backend.ai_client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.ai_client import AiTurnOutcome, _proto_to_game_event_result, compute_ai_turn_async
from game_engine.models import GameEventResult


def test_proto_to_game_event_result_turn_now_params():
    msg = MagicMock()
    msg.message_code = "turn.now"
    msg.movers_color = "черный"
    msg.game_over = False
    msg.winner_color = ""
    msg.HasField = lambda name: False
    msg.updated_positions = {}
    msg.captured_positions = []
    msg.captured_pieces = []
    msg.position_for_mandatory_capture = None
    msg.opportunity_pass_the_move = False

    result = _proto_to_game_event_result(msg, 1, 2, mover_color="белый")
    assert result.message_params == {"color": "черный"}


def test_proto_to_game_event_result_promotion_uses_mover_not_next_turn():
    msg = MagicMock()
    msg.message_code = "piece.promoted"
    msg.movers_color = "черный"
    msg.game_over = False
    msg.winner_color = ""
    msg.HasField = lambda name: False
    msg.updated_positions = {}
    msg.captured_positions = []
    msg.captured_pieces = []
    msg.position_for_mandatory_capture = None
    msg.opportunity_pass_the_move = False

    result = _proto_to_game_event_result(msg, 1, 2, mover_color="белый")
    assert result.message_params == {"color": "белый"}


def test_proto_to_game_event_result_draw_reason():
    msg = MagicMock()
    msg.message_code = ""
    msg.movers_color = None
    msg.game_over = True
    msg.winner_color = ""
    msg.draw_reason = "draw.repetition"
    msg.HasField = lambda name: name == "draw_reason"
    msg.updated_positions = {}
    msg.captured_positions = []
    msg.captured_pieces = []
    msg.position_for_mandatory_capture = None
    msg.opportunity_pass_the_move = False

    result = _proto_to_game_event_result(msg, 1, 2, mover_color="белый")
    assert result.draw_reason == "draw.repetition"


@pytest.mark.asyncio
async def test_compute_ai_turn_python_path_by_default():
    game = {
        "board": {45: "белый бий", 18: "черный бий"},
        "mover": "белый",
        "position_history": {},
    }
    fake_result = GameEventResult(
        message_code="move.ok",
        updated_positions={45: None, 37: "белый бий"},
        movers_color="черный",
    )
    outcome = AiTurnOutcome(result=fake_result, from_pos=45, to_pos=37, engine="python")

    with patch("backend.ai_client.settings") as cfg:
        cfg.ai_engine = "python"
        with patch(
            "backend.ai_client._compute_python_turn",
            new_callable=AsyncMock,
            return_value=outcome,
        ) as py_mock:
            result = await compute_ai_turn_async(game, "белый")

    assert result is outcome
    py_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_compute_ai_turn_grpc_path():
    game = {"board": {45: "белый бий"}, "mover": "белый", "position_history": {}}
    fake_result = GameEventResult(
        message_code="move.ok",
        updated_positions={45: None, 37: "белый бий"},
        movers_color="черный",
    )
    outcome = AiTurnOutcome(result=fake_result, from_pos=45, to_pos=37, engine="grpc")

    with patch("backend.ai_client.settings") as cfg:
        cfg.ai_engine = "grpc"
        with patch(
            "backend.ai_client._compute_grpc_turn",
            new_callable=AsyncMock,
            return_value=outcome,
        ) as grpc_mock:
            result = await compute_ai_turn_async(game, "белый")

    assert result.engine == "grpc"
    grpc_mock.assert_awaited_once()
