"""Strong AI: trained weights, deeper search, transposition table, deterministic play."""
from __future__ import annotations

from typing import List, Optional, Tuple

import backend.ai as ai
from backend.ai import Move, get_best_move as _base_get_best_move
from backend.ai_weights import get_active_weights, has_context_weights, load_weights, use_weights

_CACHED_WEIGHTS = None


def _trained_weights():
    global _CACHED_WEIGHTS
    if _CACHED_WEIGHTS is None:
        _CACHED_WEIGHTS = load_weights()
    return _CACHED_WEIGHTS


def _resolve_weights():
    if has_context_weights():
        return get_active_weights()
    return _trained_weights()


def reload_weights() -> None:
    global _CACHED_WEIGHTS
    _CACHED_WEIGHTS = load_weights()


def get_best_move(
    cells: dict,
    ai_color: str,
    depth: int = 6,
    batyr_captured_this_turn=None,
    chain_capture_cell=None,
    position_history: dict | None = None,
) -> Optional[Move]:
    weights = _resolve_weights()
    prev_tf = ai._TIME_FACTOR
    prev_det = ai._DETERMINISTIC_FALLBACK
    prev_tt = ai._TT
    prev_move_cap = ai._MAX_MOVES_PER_NODE
    prev_max_time = getattr(ai, "_MAX_TIME_LIMIT", None)
    try:
        ai._TIME_FACTOR = 1.2
        ai._DETERMINISTIC_FALLBACK = True
        ai._TT = {}
        ai._MAX_MOVES_PER_NODE = 28
        ai._MAX_TIME_LIMIT = 2.0
        with use_weights(weights):
            return _base_get_best_move(
                cells,
                ai_color,
                depth=depth,
                batyr_captured_this_turn=batyr_captured_this_turn,
                chain_capture_cell=chain_capture_cell,
                position_history=position_history,
            )
    finally:
        ai._TIME_FACTOR = prev_tf
        ai._DETERMINISTIC_FALLBACK = prev_det
        ai._TT = prev_tt
        ai._MAX_MOVES_PER_NODE = prev_move_cap
        ai._MAX_TIME_LIMIT = prev_max_time
