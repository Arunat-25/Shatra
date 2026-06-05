"""Hanging sacrifice: opponent picks the worst capture for us, not the best."""
from backend.ai import SearchState, _evaluate_hanging_sacrifice, _filter_moves_for_ai, get_legal_moves
from backend.ai_trained import get_best_move as strong_move
from backend.ai_weights import EvalWeights, use_weights
from backend.board_utils import get_starting_board
from game_engine.game_logic import logic
from game_engine.models import GameEvent


def _board_before_move_7():
    moves = [
        ("белый", 40, 32), ("черный", 19, 26), ("белый", 47, 40), ("черный", 26, 25),
        ("белый", 40, 33), ("черный", 20, 19),
    ]
    board = get_starting_board()
    for color, f, t in moves:
        board = logic.handle_event(
            GameEvent(positions=board, mover_color=color, from_pos=f, to_pos=t),
            position_history={},
        ).updated_positions
    return board


def _board_before_move_11():
    moves = [
        ("белый", 40, 32), ("черный", 19, 26), ("белый", 47, 40), ("черный", 26, 25),
        ("белый", 40, 33), ("черный", 20, 19), ("белый", 33, 26), ("черный", 25, 27),
        ("белый", 42, 34), ("черный", 12, 20),
    ]
    board = get_starting_board()
    for color, f, t in moves:
        board = logic.handle_event(
            GameEvent(positions=board, mover_color=color, from_pos=f, to_pos=t),
            position_history={},
        ).updated_positions
    return board


def test_33_26_sacrifice_not_justified_when_black_takes_cleanly():
    board = _board_before_move_7()
    state = SearchState(board, "белый")
    assert _evaluate_hanging_sacrifice(state, (33, 26), "белый") <= 0


def test_34_28_sacrifice_not_justified_on_user_line():
    board = _board_before_move_11()
    state = SearchState(board, "белый")
    assert _evaluate_hanging_sacrifice(state, (34, 28), "белый") <= 0


def test_even_trade_gets_small_bonus_not_penalty(monkeypatch):
    """Шатра за шатру (net=0): небольшой плюс за равный размен, не штраф за зевок."""
    import backend.ai as ai

    board = {i: None for i in range(1, 63)}
    board[40] = "белая шатра"
    state = ai.SearchState(board, "белый")
    move = (40, 33)
    calls = {"n": 0}

    def fake_child(s, fm, to):
        calls["n"] += 1
        if calls["n"] == 1:
            return ai.SearchState(board, "черный"), type("R", (), {"game_over": False})()
        return ai.SearchState(board, "белый"), type("R", (), {"game_over": False})()

    monkeypatch.setattr(ai, "_child_state", fake_child)
    monkeypatch.setattr(ai, "_is_cell_capturable", lambda cells, by, cell: True)
    monkeypatch.setattr(ai, "get_legal_moves", lambda s: [(25, 33)] if s.to_move == "черный" else [])
    monkeypatch.setattr(ai, "_move_captures_cell", lambda cells, mover, fm, to, target: True)
    monkeypatch.setattr(ai, "_get_strict_mandatory_captures", lambda cells, color: [(44, 33)])
    monkeypatch.setattr(ai, "_simulate_capture_sequence", lambda *args, **kwargs: (100, [(44, 33)]))

    with use_weights(EvalWeights(even_trade_bonus=75)):
        assert ai._evaluate_hanging_sacrifice(state, move, "белый") == 75


def test_ai_rejects_hanging_34_28():
    board = _board_before_move_11()
    state = SearchState(board, "белый")
    bad = (34, 28)
    assert bad not in _filter_moves_for_ai(state, get_legal_moves(state), "белый")
    assert strong_move(board, "белый", depth=6) != bad
