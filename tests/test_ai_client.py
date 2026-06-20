"""Tests for backend.ai_client."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.ai_client import AiTurnOutcome, compute_ai_turn_async
from game_engine.models import GameEventResult


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
