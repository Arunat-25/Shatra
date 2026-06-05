"""Side-file corridors and biy anchor evaluation bonuses."""
from backend.ai import SearchState, _move_sort_key, _opponent_has_mass, evaluate
from backend.ai_geometry import (
    BLACK_BATYR_ANCHOR,
    BLACK_BIY_ANCHOR,
    DANGER_ZONE_CELLS,
    SIDE_FILE_CELLS,
    WHITE_BIY_ANCHOR,
    biy_anchor_factor,
    main_field_density,
)
from backend.ai_weights import EvalWeights, use_weights


def _empty_board() -> dict:
    return {i: None for i in range(1, 63)}


def _fill_main_field(board: dict, count: int, piece: str) -> None:
    n = 0
    for c in range(11, 53):
        if n >= count:
            break
        if board.get(c) is None:
            board[c] = piece
            n += 1


def _add_opponent_mass(board: dict, opponent_piece: str, count: int = 7) -> None:
    """>6 фигур соперника для бонусов боковых/опасных клеток."""
    _fill_main_field(board, count, opponent_piece)


def test_side_file_cells_match_professional_corridors():
    assert SIDE_FILE_CELLS == frozenset(
        {11, 18, 25, 32, 39, 46, 17, 24, 31, 38, 45, 52}
    )
    assert BLACK_BIY_ANCHOR == frozenset({11, 17, 7, 9})
    assert WHITE_BIY_ANCHOR == frozenset({46, 52, 54, 56})


def test_evaluate_prefers_shatra_on_side_file_when_opponent_has_mass():
    w = EvalWeights(side_file_shatra_bonus=500, side_file_batyr_bonus=0, biy_anchor_bonus=0)
    flank = _empty_board()
    flank[11] = "черная шатра"
    flank[10] = "черный бий"
    flank[53] = "белый бий"
    _add_opponent_mass(flank, "белая шатра")
    center = _empty_board()
    center[14] = "черная шатра"
    center[10] = "черный бий"
    center[53] = "белый бий"
    _add_opponent_mass(center, "белая шатра")
    with use_weights(w):
        assert evaluate(flank, "черный") > evaluate(center, "черный")


def test_evaluate_no_side_file_bonus_when_opponent_light():
    flank = _empty_board()
    flank[11] = "черная шатра"
    flank[10] = "черный бий"
    flank[53] = "белый бий"
    with use_weights(EvalWeights(side_file_shatra_bonus=0, side_file_batyr_bonus=0, biy_anchor_bonus=0)):
        base = evaluate(flank, "черный")
    with use_weights(EvalWeights(side_file_shatra_bonus=500, side_file_batyr_bonus=0, biy_anchor_bonus=0)):
        with_bonus = evaluate(flank, "черный")
    assert base == with_bonus


def test_evaluate_prefers_biy_on_anchor_when_crowded():
    w = EvalWeights(
        side_file_shatra_bonus=0,
        side_file_batyr_bonus=0,
        biy_anchor_bonus=400,
        crowded_main_field_threshold=18,
    )
    anchor = _empty_board()
    anchor[7] = "черный бий"
    anchor[53] = "белый бий"
    _fill_main_field(anchor, 20, "черная шатра")

    other = _empty_board()
    other[15] = "черный бий"
    other[53] = "белый бий"
    _fill_main_field(other, 20, "черная шатра")

    assert main_field_density(anchor) >= w.crowded_main_field_threshold
    with use_weights(w):
        assert evaluate(anchor, "черный") > evaluate(other, "черный")


def test_biy_anchor_factor_sparse_vs_crowded():
    assert biy_anchor_factor(10, 20) == 0.35
    assert biy_anchor_factor(20, 20) == 1.0


def test_move_sort_prefers_biy_to_anchor_over_center():
    board = _empty_board()
    for c in range(1, 10):
        board[c] = None
    board[10] = "черный бий"
    board[53] = "белый бий"
    state = SearchState(board, "черный")
    w = EvalWeights(biy_anchor_bonus=800, crowded_main_field_threshold=10)
    with use_weights(w):
        to_anchor = _move_sort_key(state, (10, 7), "черный")
        to_center = _move_sort_key(state, (10, 15), "черный")
    assert to_anchor > to_center
    assert to_anchor > 0
    assert to_center >= 0


def test_move_sort_penalizes_exposing_biy():
    board = _empty_board()
    board[10] = "черный бий"
    board[28] = "белая шатра"
    board[53] = "белый бий"
    state = SearchState(board, "черный")
    with use_weights(EvalWeights(biy_anchor_bonus=5000)):
        score = _move_sort_key(state, (10, 20), "черный")
    assert score == -300_000


def test_danger_zone_cells():
    assert DANGER_ZONE_CELLS == frozenset({27, 28, 29, 34, 35, 36})


def test_evaluate_penalizes_pieces_in_danger_zone_when_opponent_has_mass():
    board = _empty_board()
    board[27] = "черная шатра"
    board[35] = "черная шатра"
    board[10] = "черный бий"
    board[53] = "белый бий"
    _add_opponent_mass(board, "белая шатра")
    with use_weights(EvalWeights(danger_zone_penalty=0)):
        base = evaluate(board, "черный")
    with use_weights(EvalWeights(danger_zone_penalty=200)):
        penalized = evaluate(board, "черный")
    assert base - penalized == 400


def test_opponent_mass_counts_all_pieces_on_board():
    board = _empty_board()
    board[10] = "черный бий"
    board[53] = "белый бий"
    for c in range(11, 16):
        board[c] = "белая шатра"
    assert not _opponent_has_mass(board, "черный")
    board[16] = "белая шатра"
    assert _opponent_has_mass(board, "черный")


def test_shatra_has_no_center_position_bonus():
    w = EvalWeights(
        side_file_shatra_bonus=0,
        side_file_batyr_bonus=0,
        promotion_progress_weight=0,
        promotion_bonus=0,
        position_scale=99,
    )
    center = _empty_board()
    center[28] = "черная шатра"
    center[10] = "черный бий"
    center[53] = "белый бий"
    flank = _empty_board()
    flank[25] = "черная шатра"
    flank[10] = "черный бий"
    flank[53] = "белый бий"
    with use_weights(w):
        assert evaluate(center, "черный") == evaluate(flank, "черный")


def test_batyr_bonus_only_on_anchor_cells():
    w = EvalWeights(
        batyr_anchor_bonus=500,
        side_file_batyr_bonus=0,
        position_scale=99,
    )
    board = _empty_board()
    board[8] = "черный батыр"
    board[10] = "черный бий"
    board[53] = "белый бий"
    _add_opponent_mass(board, "белая шатра")
    off_anchor = dict(board)
    off_anchor[20] = off_anchor.pop(8)
    with use_weights(w):
        assert evaluate(board, "черный") > evaluate(off_anchor, "черный")
    assert 8 in BLACK_BATYR_ANCHOR


def test_move_sort_prefers_safe_cell_over_danger_when_opponent_has_mass():
    board = _empty_board()
    board[46] = "белая шатра"
    board[10] = "черный бий"
    board[53] = "белый бий"
    for c in range(39, 46):
        board[c] = "черная шатра"
    state = SearchState(board, "белый")
    w = EvalWeights(
        danger_zone_penalty=200,
        side_file_shatra_bonus=0,
        side_file_batyr_bonus=0,
        biy_anchor_bonus=0,
        promotion_progress_weight=0,
        promotion_bonus=0,
    )
    with use_weights(w):
        to_danger = _move_sort_key(state, (46, 34), "белый")
        to_safe = _move_sort_key(state, (46, 32), "белый")
    assert to_safe > to_danger


def test_evaluate_no_danger_zone_penalty_when_opponent_light():
    board = _empty_board()
    board[27] = "черная шатра"
    board[35] = "черная шатра"
    board[10] = "черный бий"
    board[53] = "белый бий"
    with use_weights(EvalWeights(danger_zone_penalty=0)):
        base = evaluate(board, "черный")
    with use_weights(EvalWeights(danger_zone_penalty=200)):
        penalized = evaluate(board, "черный")
    assert base == penalized


