"""Регрессия: pass разрешён только при обязательной цепочке взятий (P0-1)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.session.v2 import messages as m
from backend.session.v2.messages import process_v2_client_message


def _make_ws():
    ws = MagicMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.fixture
def pass_env(monkeypatch):
    """Изолированная комната: Redis-коллаборации замоканы, движок настоящий."""
    game = {
        "board": {10: "белый бий", 19: "белая шатра", 25: "черный бий", 62: "черная шатра"},
        "mover": "белый",
        "ply": 3,
        "game_over": False,
        "move_history": [],
        "pending_batyr_captures": [],
        "position_history": {},
        "moves_with_two_biys": 0,
    }
    room_data = {
        "room_id": "passtest",
        "type": "public",
        "players": {"c1": "белый", "c2": "черный"},
        "player_meta": {},
        "game_started": True,
    }
    sent = []

    async def fake_send_to_player(ws_, payload):
        sent.append(payload)

    class FakeLock:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    async def fake_get_game(room_id):
        return game

    async def fake_get_room(room_id):
        return room_data

    async def fake_set_game(room_id, data):
        pass

    async def fake_set_room(room_id, data):
        pass

    async def fake_apply_move_result(*args, **kwargs):
        return {}

    async def fake_broadcast_move(*args, **kwargs):
        return None

    monkeypatch.setattr(m, "get_game", fake_get_game)
    monkeypatch.setattr(m, "get_room", fake_get_room)
    monkeypatch.setattr(m, "set_game", fake_set_game)
    monkeypatch.setattr(m, "set_room", fake_set_room)
    monkeypatch.setattr(m, "get_room_lock", lambda room_id: FakeLock())
    monkeypatch.setattr(m.manager, "send_to_player", fake_send_to_player)
    monkeypatch.setattr(m, "apply_move_result", fake_apply_move_result)
    monkeypatch.setattr(m.manager, "broadcast_move", fake_broadcast_move)

    return {"game": game, "room_data": room_data, "sent": sent, "ws": _make_ws()}


def _reject_codes(sent) -> list:
    return [
        p.get("code")
        for p in sent
        if isinstance(p, dict) and p.get("t") == "reject"
    ]


async def test_pass_rejected_without_mandatory_capture_chain(pass_env):
    env = pass_env
    game = env["game"]
    sent = env["sent"]
    ws = env["ws"]

    ok = await process_v2_client_message(
        "passtest", "c1", {"v": 2, "t": "pass", "ply": 4}, ws, is_ai_room=False,
    )
    assert ok is True
    assert "ws.pass_not_allowed" in _reject_codes(sent)
    # Ход не должен применяться/менять ходовую очередь.
    assert game["mover"] == "белый"
    assert game["ply"] == 3


async def test_pass_allowed_in_mandatory_capture_chain(pass_env, monkeypatch):
    env = pass_env
    game = env["game"]
    sent = env["sent"]
    ws = env["ws"]
    game["pending_mandatory_position"] = 25

    async def fake_mandatory(board, color, batyr_captured_this_turn):
        return [(25, 19)]

    monkeypatch.setattr(m, "get_all_mandatory_captures", fake_mandatory)

    ok = await process_v2_client_message(
        "passtest", "c1", {"v": 2, "t": "pass", "ply": 4}, ws, is_ai_room=False,
    )
    assert ok is True
    assert "ws.pass_not_allowed" not in _reject_codes(sent)
