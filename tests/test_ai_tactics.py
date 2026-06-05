"""Tactical move selection: sacrifices, side files, fortress deploy, depth."""
from backend.ai import SearchState, _is_deprioritized_move, _move_sort_key
from backend.ai_trained import get_best_move as strong_move
from backend.board_utils import get_starting_board
from game_engine.game_logic import logic
from game_engine.models import GameEvent
from game_engine.hints import get_hints


def _board_after_opening():
    moves = [
        ("белый", 40, 34),
        ("черный", 18, 26),
        ("белый", 34, 18),
        ("черный", 11, 25),
        ("белый", 41, 34),
        ("черный", 19, 18),
    ]
    board = get_starting_board()
    for color, f, t in moves:
        board = logic.handle_event(
            GameEvent(positions=board, mover_color=color, from_pos=f, to_pos=t),
            position_history={},
        ).updated_positions
    return board


def test_strong_ai_avoids_hanging_39_32_in_user_line():
    board = _board_after_opening()
    move = strong_move(board, "белый", depth=5)
    assert move is not None
    assert move != (39, 32)
    hints = get_hints(board, "белый", move[0])
    assert move[1] in hints.essential_positions


def test_hanging_39_32_sort_key_heavily_penalized():
    board = _board_after_opening()
    state = SearchState(board, "белый")
    bad = _move_sort_key(state, (39, 32), "белый")
    safe = _move_sort_key(state, (44, 36), "белый")
    assert bad < -40_000
    assert bad < safe - 10_000


def _board_before_black_29():
    moves = [
        ("белый", 44, 38), ("черный", 23, 29), ("белый", 51, 44), ("черный", 18, 25),
        ("белый", 40, 32), ("черный", 9, 18), ("белый", 44, 37), ("черный", 16, 23),
        ("белый", 37, 31), ("черный", 17, 16), ("белый", 31, 17), ("черный", 19, 26),
        ("белый", 43, 37), ("черный", 11, 19), ("белый", 41, 34), ("черный", 20, 28),
        ("белый", 32, 20), ("белый", 20, 36), ("черный", 29, 43), ("черный", 43, 41),
        ("черный", 41, 27), ("белый", 17, 29), ("черный", 22, 36), ("белый", 37, 35),
        ("черный", 27, 43), ("белый", 50, 36), ("черный", 10, 23), ("белый", 36, 30),
    ]
    from backend.board_utils import get_starting_board
    from game_engine.game_logic import logic
    from game_engine.models import GameEvent

    board = get_starting_board()
    for color, f, t in moves:
        board = logic.handle_event(
            GameEvent(positions=board, mover_color=color, from_pos=f, to_pos=t),
            position_history={},
        ).updated_positions
    return board


def _board_before_black_move_38_user_game():
    moves = [
        ("белый", 45, 38), ("черный", 23, 31), ("белый", 44, 45), ("черный", 24, 23),
        ("белый", 38, 24), ("черный", 17, 31), ("белый", 50, 44), ("черный", 16, 17),
        ("белый", 44, 38), ("черный", 9, 24), ("белый", 40, 32), ("черный", 19, 25),
        ("белый", 41, 40), ("черный", 12, 19), ("белый", 40, 33), ("черный", 25, 41),
        ("белый", 49, 33), ("черный", 19, 25), ("белый", 51, 44), ("черный", 25, 41),
        ("белый", 42, 40), ("черный", 11, 12), ("белый", 40, 33), ("черный", 12, 11),
        ("белый", 33, 25), ("черный", 11, 12), ("белый", 25, 11), ("черный", 15, 16),
        ("белый", 44, 37), ("черный", 31, 30), ("белый", 37, 31), ("черный", 23, 29),
        ("белый", 43, 44), ("черный", 14, 15), ("белый", 48, 49), ("черный", 8, 14),
        ("белый", 49, 50),
    ]
    board = get_starting_board()
    for color, f, t in moves:
        board = logic.handle_event(
            GameEvent(positions=board, mover_color=color, from_pos=f, to_pos=t),
            position_history={},
        ).updated_positions
    return board


def test_black_rejects_29_35_double_shatra_loss():
    """38. Ч 29-35 отдаёт две шатры под цепочку 31-29, 29-41."""
    from backend.ai import get_best_move as easy_move

    board = _board_before_black_move_38_user_game()
    assert strong_move(board, "черный", depth=3) != (29, 35)
    assert easy_move(board, "черный", depth=3) != (29, 35)


def test_black_biy_rejects_shatra_trade_23_37():
    """Чёрный бий 23-37: шатра за бия — сильный ИИ не должен так играть."""
    board = _board_before_black_29()
    move = strong_move(board, "черный", depth=5)
    assert move is not None
    assert move != (23, 37)


def test_full_depth_used_with_many_pieces(monkeypatch):
    import backend.ai as ai

    board = get_starting_board()
    depths_seen = []

    def spy_minimax(state, depth, alpha, beta, maximizing, ai_color, start_time=None, time_limit=ai.math.inf):
        depths_seen.append(depth)
        return 0, None

    monkeypatch.setattr(ai, "minimax", spy_minimax)
    monkeypatch.setattr(ai, "_filter_moves_for_ai", lambda s, m, c: m)
    ai.get_best_move(board, "белый", depth=5)
    assert max(depths_seen) >= 5
