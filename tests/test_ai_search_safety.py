"""Regression tests for minimax move pruning, TT depth, and time checks."""
from unittest.mock import patch

import backend.ai as ai
from backend.ai import (
    SearchState,
    _mandatory_moves_set,
    _select_moves_for_search,
    minimax,
)
from backend.board_utils import get_starting_board
import backend.ai_trained as ai_trained


def test_mandatory_moves_never_dropped():
    """All mandatory captures stay in search set even when tier3 is capped."""
    board = {i: None for i in range(1, 63)}
    board[10] = "черный бий"
    board[53] = "белый бий"
    board[18] = "белая шатра"
    board[26] = "черная шатра"
    state = SearchState(board, "белый")
    legal = ai.get_legal_moves(state)
    mandatory = _mandatory_moves_set(state)
    if not mandatory:
        return
    with patch.object(ai, "_MAX_MOVES_PER_NODE", 2):
        selected = _select_moves_for_search(state, legal, "белый", True, tier3_cap=0)
    for m in mandatory:
        assert m in selected


def test_tt_not_used_at_depth_zero():
    store = {}

    class TrackingDict(dict):
        def __setitem__(self, key, value):
            store["written"] = True
            super().__setitem__(key, value)

    board = get_starting_board()
    state = SearchState(board, "белый")
    tracking = TrackingDict()
    with patch.object(ai, "_TT", tracking):
        minimax(state, 0, -ai.WIN_SCORE, ai.WIN_SCORE, True, "белый")
    assert "written" not in store


def test_time_check_in_move_loop_returns_without_hanging():
    board = get_starting_board()
    state = SearchState(board, "белый")
    times = [0.0, 100.0]

    def fake_time():
        return times[min(len(times) - 1, 1)] if len(times) > 1 else times[0]

    with patch.object(ai, "time") as mock_time:
        mock_time.time.side_effect = lambda: times[0]
        # First call at entry ok, second in loop exceeded
        call_count = [0]

        def tick():
            call_count[0] += 1
            if call_count[0] <= 2:
                return 0.0
            return 100.0

        mock_time.time.side_effect = tick
        val, move = minimax(state, 1, -ai.WIN_SCORE, ai.WIN_SCORE, True, "белый", start_time=0.0, time_limit=0.01)
    assert isinstance(val, (int, float))


def test_strong_has_higher_move_limit():
    board = get_starting_board()
    original = ai_trained._base_get_best_move
    seen = []

    def hook(*args, **kwargs):
        seen.append(ai._MAX_MOVES_PER_NODE)
        return original(*args, **kwargs)

    with patch.object(ai_trained, "_base_get_best_move", side_effect=hook):
        ai_trained.get_best_move(board, "белый", depth=2)
    assert seen == [28]
    assert ai._MAX_MOVES_PER_NODE is None
