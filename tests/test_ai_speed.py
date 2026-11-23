"""Speed regression: бот в партии с ботом не должен выжигать весь бюджет на каждый ход.

Цикл (как в /tmp/opencode/driver_ai_speed.py): игра из бота + случайных ходов
игрока; усреднённое время compute_ai_turn_async ограничено лёгким запасом
при бюджете AI_MOVE_TIME_MS (до фикса бот делал ~3.0-3.3 с при бюджете 3.0;
после оптимизаций поиска + снижения дефолтного бюджета показывает ~1.05 с).
"""

import random
import statistics
import time

import pytest

from backend.ai import SearchState, get_legal_moves
from backend.ai_client import compute_ai_turn_async
from backend.config import settings
from backend.game_helpers import bump_ply, persist_pending_mandatory_position, update_captures
from game_engine.game_logic import logic
from game_engine.models import GameEvent
from tests.helpers.server_game_sim import new_server_game


def _apply_result(game: dict, result) -> None:
    prev_mover = game["mover"]
    if result.updated_positions:
        game["board"] = result.updated_positions
    persist_pending_mandatory_position(game, result, prev_mover)
    update_captures(game, result)
    if result.movers_color:
        game["mover"] = result.movers_color
    bump_ply(game)


def _player_move(game: dict, rng) -> bool:
    state = SearchState(
        cells=game["board"],
        to_move=game["mover"],
        chain_cell=game.get("pending_mandatory_position"),
    )
    moves = get_legal_moves(state)
    if not moves:
        return False
    fm, to = rng.choice(moves)
    prev = game["mover"]
    result = logic.handle_event(
        GameEvent(
            positions=game["board"],
            mover_color=prev,
            from_pos=fm,
            to_pos=to,
            position_for_mandatory_capture=game.get("pending_mandatory_position"),
        ),
        batyr_captured_this_turn=game.get("pending_batyr_captures"),
    )
    _apply_result(game, result)
    return True


@pytest.mark.asyncio
async def test_bot_moves_are_fast():
    """Усреднённое время бот-хода не должно быть существенно выше бюджета поиска."""
    saved_engine = settings.ai_engine
    settings.ai_engine = "python"
    rng = random.Random(42)
    game = new_server_game()
    durs = []
    try:
        for _ in range(4):
            t0 = time.perf_counter()
            outcome = await compute_ai_turn_async(game, game["mover"])
            dt = time.perf_counter() - t0
            if outcome is None or not outcome.result.updated_positions or dt < 0.05:
                break
            durs.append(dt)
            _apply_result(game, outcome.result)
            if not _player_move(game, rng):
                break
    finally:
        settings.ai_engine = saved_engine

    assert durs, "no bot moves measured"
    threshold = settings.ai_move_time_ms / 1000 * 2.5
    avg = statistics.mean(durs)
    assert avg < threshold, f"avg bot move latency {avg:.3f}s >= {threshold:.3f}s"
