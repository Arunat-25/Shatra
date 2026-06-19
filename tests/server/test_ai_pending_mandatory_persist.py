"""Regression: AI must persist cleared mandatory-capture state after finishing a chain."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.board_utils import get_starting_board
from backend.game_helpers import build_hint_event_from_game
from backend.session import process_client_message
from game_engine.game_logic import logic
from game_engine.models import GameEvent
from tests.server.disconnect_helpers import ai_room


def _board_before_single_white_capture():
    """
    White must capture once (32->18) and the chain ends immediately.
    User-reported sequence:
      white 40-32, black 19-25, white 41-33, black 25-41,
      white 42-40, black 18-25 (forces white to capture from 32).
    """
    moves = [
        ("белый", 40, 32),
        ("черный", 19, 25),
        ("белый", 41, 33),
        ("черный", 25, 41),
        ("белый", 42, 40),
        ("черный", 18, 25),
    ]
    board = get_starting_board()
    for color, f, t in moves:
        board = logic.handle_event(
            GameEvent(positions=board, mover_color=color, from_pos=f, to_pos=t),
            position_history={},
        ).updated_positions
    return board


@pytest.mark.asyncio
async def test_ai_persists_cleared_pending_mandatory_after_move():
    """
    handle_ai_move updates pending_mandatory_position after apply_move_result.
    Without a follow-up set_game, Redis keeps stale pending=32 and hints break.
    """
    from backend.session.ai import handle_ai_move

    game = {
        "board": _board_before_single_white_capture(),
        "mover": "белый",
        "pending_mandatory_position": 32,
        "move_history": [],
        "position_history": {},
        "pending_batyr_captures": [],
    }
    room = {"type": "ai"}

    set_game_calls = []

    async def _set_game(_room_id, g):
        set_game_calls.append(dict(g))

    async def _apply_move_result(_room_id, g, result, prev_mover, from_cell, to_cell):
        if result.updated_positions:
            g["board"] = result.updated_positions
        if result.movers_color:
            g["mover"] = result.movers_color
        # apply_move_result does not touch pending_mandatory_position.
        await _set_game(_room_id, g)
        return {}

    with (
        patch("backend.session.ai.asyncio.sleep", new_callable=AsyncMock),
        patch("backend.session.ai.get_ai_move", lambda *args, **kwargs: (32, 18)),
        patch("backend.session.ai.set_game", _set_game),
        patch("backend.session.ai.manager.send_to_room", new_callable=AsyncMock),
        patch("backend.session.ai.apply_move_result", _apply_move_result),
    ):
        await handle_ai_move("room-persist", game, room_data=room)

    assert game["mover"] == "черный"
    assert game.get("pending_mandatory_position") is None
    assert set_game_calls, "Expected at least one persistence call"
    assert set_game_calls[-1].get("pending_mandatory_position") is None


@pytest.mark.asyncio
async def test_hint_after_ai_capture_does_not_say_continue_same():
    """
    User symptom: after AI plays 32->18, clicking black piece 11 returned
    'capture.continue_same' because server still had pending_mandatory_position=32.
    """
    from backend.session.ai import handle_ai_move

    room_id = "room-hint"
    room = ai_room(room_id=room_id, players={"human-1": "черный"})
    game = {
        "board": _board_before_single_white_capture(),
        "mover": "белый",
        "pending_mandatory_position": 32,
        "move_history": [],
        "position_history": {},
        "pending_batyr_captures": [],
        "game_over": False,
    }

    persisted = {}
    ws = AsyncMock()
    ws.send_json = AsyncMock()

    async def _set_game(_room_id, g):
        persisted["game"] = dict(g)

    async def _apply_move_result(_room_id, g, result, prev_mover, from_cell, to_cell):
        if result.updated_positions:
            g["board"] = result.updated_positions
        if result.movers_color:
            g["mover"] = result.movers_color
        await _set_game(_room_id, g)
        return {}

    async def get_game(rid):
        return persisted.get("game") if rid == room_id else None

    async def get_room(rid):
        return room if rid == room_id else None

    with (
        patch("backend.session.ai.asyncio.sleep", new_callable=AsyncMock),
        patch("backend.session.ai.get_ai_move", lambda *args, **kwargs: (32, 18)),
        patch("backend.session.ai.set_game", _set_game),
        patch("backend.session.ai.apply_move_result", _apply_move_result),
        patch("backend.session.ai.manager.send_to_room", AsyncMock()),
        patch("backend.session.messages.get_game", get_game),
        patch("backend.session.messages.get_room", get_room),
        patch("backend.session.messages.manager.send_to_room", AsyncMock()),
        patch("backend.session.messages.manager.send_to_player", AsyncMock()) as send_player,
    ):
        await handle_ai_move(room_id, game, room_data=room)

        assert persisted["game"]["mover"] == "черный"
        assert persisted["game"].get("pending_mandatory_position") is None

        await process_client_message(
            room_id,
            "human-1",
            {"position": "position11"},
            ws,
            is_ai_room=True,
        )

        hint_payload = send_player.call_args[0][1]
        assert hint_payload.get("message_code") != "capture.continue_same"
        assert 25 in (hint_payload.get("essential_positions") or [])

        event = build_hint_event_from_game(persisted["game"], 11)
        expected = logic.handle_event(
            event,
            batyr_captured_this_turn=persisted["game"].get("pending_batyr_captures"),
            position_history=persisted["game"].get("position_history"),
        )
        assert hint_payload["essential_positions"] == expected.essential_positions


@pytest.mark.asyncio
async def test_stale_pending_mandatory_reproduces_continue_same():
    """Document the broken state: stale pending=32 makes black hints on 11 fail."""
    board = _board_before_single_white_capture()
    result = logic.handle_event(
        GameEvent(
            positions=board,
            mover_color="белый",
            from_pos=32,
            to_pos=18,
            position_for_mandatory_capture=32,
        ),
        position_history={},
    )
    game = {
        "board": result.updated_positions,
        "mover": "черный",
        "pending_mandatory_position": 32,  # stale — should have been cleared
        "pending_batyr_captures": [],
        "position_history": {},
    }

    event = build_hint_event_from_game(game, 11)
    hint = logic.handle_event(
        event,
        batyr_captured_this_turn=game.get("pending_batyr_captures"),
        position_history=game.get("position_history"),
    )

    assert hint.message_code == "capture.continue_same"
    assert hint.essential_positions == []
