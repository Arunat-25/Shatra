"""Fortress shatra deploy: justified only on capture, sacrifice gain, or necessary defense."""
from backend.ai import (
    SearchState,
    _can_defend_cell_with_field_piece,
    _count_own_main_field_shatras,
    _filter_moves_for_ai,
    _fortress_deploy_justified,
    _fortress_deploy_search_penalty,
    _fortress_entry_piece_bonus,
    _fortress_entry_search_adjustment,
    _move_sort_key,
    evaluate,
    get_legal_moves,
)
from backend.ai_geometry import is_fortress_entry
from backend.ai_trained import get_best_move as strong_move
from backend.ai_weights import EvalWeights, use_weights
from backend.board_utils import get_starting_board
from game_engine.game_logic import logic
from game_engine.hints import get_hints
from game_engine.models import GameEvent


def _empty_board():
    return {i: None for i in range(1, 63)}


def test_fortress_entry_bonus_only_for_shatra_below_piece_value():
    w = EvalWeights(piece_shatra=100, fortress_entry_shatra_bonus=45)
    with use_weights(w):
        assert 0 < _fortress_entry_piece_bonus("белая шатра") < w.piece_shatra
        assert _fortress_entry_piece_bonus("черный батыр") == 0
        assert _fortress_entry_piece_bonus("черный бий") == 0


def test_is_fortress_entry_enemy_fortress_only():
    assert is_fortress_entry(15, 7, "белый")
    assert is_fortress_entry(40, 53, "черный")
    assert not is_fortress_entry(19, 10, "черный")
    assert not is_fortress_entry(14, 10, "черный")
    assert not is_fortress_entry(54, 52, "белый")


def test_move_sort_rewards_shatra_entering_enemy_fortress():
    board = _empty_board()
    board[15] = "белая шатра"
    board[10] = "черный батыр"
    board[2] = "черный бий"
    board[53] = "белый бий"
    state = SearchState(board, "белый")
    move = (15, 7)
    base_w = EvalWeights(fortress_entry_shatra_bonus=0)
    bonus_w = EvalWeights(fortress_entry_shatra_bonus=80)
    with use_weights(base_w):
        base = _move_sort_key(state, move, "белый")
    with use_weights(bonus_w):
        rewarded = _move_sort_key(state, move, "белый")
    assert rewarded > base
    assert rewarded - base == bonus_w.fortress_entry_shatra_bonus


def test_move_sort_no_bonus_for_own_fortress_entry():
    board = _empty_board()
    board[19] = "черный батыр"
    board[2] = "черный бий"
    board[53] = "белый бий"
    state = SearchState(board, "черный")
    move = (19, 10)
    with use_weights(EvalWeights(fortress_entry_shatra_bonus=0)):
        base = _move_sort_key(state, move, "черный")
    with use_weights(EvalWeights(fortress_entry_shatra_bonus=200)):
        same = _move_sort_key(state, move, "черный")
    assert same == base


def test_evaluate_penalizes_opponent_shatra_in_empty_own_fortress():
    board = _empty_board()
    board[7] = "белая шатра"
    board[20] = "черный бий"
    board[53] = "белый бий"
    with use_weights(EvalWeights(fortress_intrusion_penalty=0)):
        base = evaluate(board, "черный")
    with use_weights(EvalWeights(fortress_intrusion_penalty=5000)):
        penalized = evaluate(board, "черный")
    assert base - penalized == 5000


def test_evaluate_no_fortress_intrusion_penalty_when_own_piece_in_fortress():
    board = _empty_board()
    board[7] = "белая шатра"
    board[10] = "черный бий"
    board[53] = "белый бий"
    with use_weights(EvalWeights(fortress_intrusion_penalty=0)):
        base = evaluate(board, "черный")
    with use_weights(EvalWeights(fortress_intrusion_penalty=5000)):
        penalized = evaluate(board, "черный")
    assert base == penalized


def test_fortress_entry_search_penalty_when_own_fortress_empty():
    board = _empty_board()
    board[15] = "белая шатра"
    board[53] = "белый бий"
    state = SearchState(board, "белый")
    move = (15, 7)
    w = EvalWeights(fortress_intrusion_penalty=8000, fortress_entry_shatra_bonus=45)
    with use_weights(w):
        assert _fortress_entry_search_adjustment(state, move, "черный") == -8000


def test_fortress_entry_search_adjustment_for_shatra_in_enemy_fortress():
    board = _empty_board()
    board[15] = "белая шатра"
    board[10] = "черный батыр"
    board[2] = "черный бий"
    board[53] = "белый бий"
    state = SearchState(board, "белый")
    move = (15, 7)
    w = EvalWeights(fortress_entry_shatra_bonus=60)
    with use_weights(w):
        assert _fortress_entry_search_adjustment(state, move, "белый") == 60


def test_plain_fortress_deploy_not_justified():
    board = _empty_board()
    board[54] = "белая шатра"
    board[53] = "белый бий"
    board[10] = "черный бий"
    state = SearchState(board, "белый")
    move = (54, 52)
    hints = get_hints(board, "белый", 54)
    assert 52 in (hints.essential_positions or [])
    assert not _fortress_deploy_justified(state, move, "белый")


def _board_with_n_white_main_field_shatras(n: int) -> dict:
    """n шатр на большом поле (39–47), плюс резерв в крепости на 54 для выставления."""
    board = _empty_board()
    board[53] = "белый бий"
    board[10] = "черный бий"
    board[54] = "белая шатра"
    for i, cell in enumerate(range(39, 48)):
        if i >= n:
            break
        board[cell] = "белая шатра"
    return board


def test_fortress_deploy_sort_key_penalty_when_many_shatras():
    board = _board_with_n_white_main_field_shatras(9)
    state = SearchState(board, "белый")
    move = (54, 52)
    with use_weights(EvalWeights(fortress_deploy_penalty=0, side_file_shatra_bonus=0)):
        base = _move_sort_key(state, move, "белый")
    with use_weights(EvalWeights(fortress_deploy_penalty=90_000, side_file_shatra_bonus=0)):
        penalized = _move_sort_key(state, move, "белый")
    assert base - penalized == 90_000


def test_fortress_deploy_no_penalty_when_at_most_eight_shatras():
    board = _board_with_n_white_main_field_shatras(8)
    assert _count_own_main_field_shatras(board, "белый") == 8
    state = SearchState(board, "белый")
    move = (54, 52)
    with use_weights(EvalWeights(fortress_deploy_penalty=90_000, side_file_shatra_bonus=0)):
        penalized = _move_sort_key(state, move, "белый")
    with use_weights(EvalWeights(fortress_deploy_penalty=0, side_file_shatra_bonus=0)):
        base = _move_sort_key(state, move, "белый")
    assert penalized == base
    assert _fortress_deploy_search_penalty(state, move, "белый") == 0
    filtered = _filter_moves_for_ai(state, get_legal_moves(state), "белый")
    assert move in filtered


def test_redundant_fortress_defense_not_justified():
    """
    Шатра 39 под боем (46→39). Бий 40→32 защищает.
    Выставление 54→32 тоже снимает угрозу — но бий на поле мог защитить сам.
    """
    board = _empty_board()
    board[54] = "белая шатра"
    board[53] = "белый бий"
    board[40] = "белый бий"
    board[39] = "белая шатра"
    board[46] = "черная шатра"
    board[10] = "черный бий"
    state = SearchState(board, "белый")
    deploy = (54, 32)
    assert _can_defend_cell_with_field_piece(state, "белый", 39, exclude_from=54)
    assert not _fortress_deploy_justified(state, deploy, "белый")


def test_necessary_fortress_defense_is_justified():
    """
    Шатра 39 под боем, на большом поле нет фигур, которые могут защитить.
    Выставление 54→32 — единственная защита.
    """
    board = _empty_board()
    board[54] = "белая шатра"
    board[53] = "белый бий"
    board[39] = "белая шатра"
    board[46] = "черная шатра"
    board[10] = "черный бий"
    state = SearchState(board, "белый")
    deploy = (54, 32)
    assert not _can_defend_cell_with_field_piece(state, "белый", 39, exclude_from=54)
    assert _fortress_deploy_justified(state, deploy, "белый")


def _board_before_user_game_move_26():
    moves = [
        ("белый", 45, 37), ("черный", 22, 29), ("белый", 51, 45), ("черный", 29, 30),
        ("белый", 37, 38), ("черный", 30, 31), ("белый", 43, 37), ("черный", 31, 43),
        ("белый", 49, 37), ("черный", 16, 22), ("белый", 37, 31), ("черный", 18, 25),
        ("белый", 40, 32), ("черный", 12, 18), ("белый", 41, 40), ("черный", 9, 12),
        ("белый", 42, 41), ("черный", 8, 26), ("белый", 41, 33), ("черный", 25, 41),
        ("белый", 48, 34), ("черный", 26, 42), ("белый", 50, 34), ("черный", 19, 26),
        ("белый", 34, 33),
    ]
    board = get_starting_board()
    for color, f, t in moves:
        board = logic.handle_event(
            GameEvent(positions=board, mover_color=color, from_pos=f, to_pos=t),
            position_history={},
        ).updated_positions
    return board


def test_user_line_rejects_fortress_7_19_when_13_19_defends():
    """26. Ч 7-19: резерв не нужен — шатра 13-19 защищает 26."""
    board = _board_before_user_game_move_26()
    state = SearchState(board, "черный")
    deploy = (7, 19)
    defend = (13, 19)
    assert not _fortress_deploy_justified(state, deploy, "черный")
    filtered = _filter_moves_for_ai(state, get_legal_moves(state), "черный")
    assert deploy not in filtered
    assert defend in filtered
    assert strong_move(board, "черный", depth=5) != deploy
