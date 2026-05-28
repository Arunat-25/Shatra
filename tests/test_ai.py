from backend.ai import SearchState, _is_cell_capturable, _move_exposes_biy, get_best_move
from backend.board_utils import get_starting_board
from game_engine.board import Board
from game_engine.endgame import is_game_over
from game_engine.game_logic import logic
from game_engine.hints import get_hints
from game_engine.models import GameEvent
from game_engine.moves import process_move


def _is_legal_move(board, color, move):
    if move is None:
        return False

    from_cell, to_cell = move
    piece = board.get(from_cell)
    if piece is None:
        return False 

    hints = get_hints(board, color, from_cell)
    return to_cell in hints.essential_positions


def _play_moves(moves):
    board = get_starting_board()
    for color, from_cell, to_cell in moves:
        result = logic.handle_event(
            GameEvent(positions=board, mover_color=color, from_pos=from_cell, to_pos=to_cell),
            position_history={},
        )
        board = result.updated_positions
    return board


def test_get_best_move_returns_legal_move_for_starting_position():
    board = get_starting_board()

    for color in ("белый", "черный"):
        move = get_best_move(board, color, depth=2)

        assert move is not None
        assert _is_legal_move(board, color, move)


def test_get_best_move_returns_legal_move_after_reproduced_sequence():
    moves = [
        ("белый", 45, 37),
        ("черный", 23, 29),
        ("белый", 44, 45),
        ("черный", 22, 30),
        ("белый", 37, 23),
        ("белый", 23, 35),
        ("черный", 19, 27),
        ("белый", 35, 19),
        ("черный", 11, 27),
        ("белый", 41, 34),
        ("черный", 27, 41),
        ("белый", 48, 34),
        ("черный", 15, 22),
        ("белый", 42, 35),
        ("черный", 22, 29),
        ("белый", 35, 23),
        ("черный", 24, 22),
        ("белый", 45, 37),
        ("черный", 9, 11),
        ("белый", 37, 29),
        ("черный", 22, 36),
        ("белый", 43, 29),
        ("черный", 21, 37),
        ("белый", 52, 45),
        ("черный", 8, 30),
        ("белый", 45, 29),
        ("белый", 29, 31),
        ("черный", 16, 15),
        ("белый", 31, 23),
        ("черный", 17, 29),
        ("белый", 54, 36),
        ("черный", 29, 43),
        ("белый", 50, 36),
        ("черный", 7, 29),
        ("белый", 36, 22),
        ("черный", 15, 29),
        ("белый", 49, 42),
        ("черный", 29, 36),
        ("белый", 42, 30),
        ("черный", 20, 27),
        ("белый", 34, 20),
        ("черный", 12, 28),
        ("белый", 51, 44),
        ("черный", 14, 22),
        ("белый", 30, 14),
        ("белый", 14, 12),
        ("черный", 11, 13),
        ("белый", 44, 36),
    ]

    board = _play_moves(moves)

    game_over, _ = is_game_over(Board(board))

    assert game_over is False

    move = get_best_move(board, "черный", depth=2)

    assert move is not None
    assert _is_legal_move(board, "черный", move)


def test_get_best_move_returns_none_for_empty_board():
    assert get_best_move({}, "белый", depth=2) is None


def test_ai_does_not_move_biy_into_capture():
    board = {i: None for i in range(1, 63)}
    board[10] = "черный бий"
    board[28] = "белая шатра"
    board[36] = None

    move = get_best_move(board, "черный", depth=3)
    assert move is not None
    state = SearchState(board, "черный")
    assert not _move_exposes_biy(state, move, "черный")


def test_ai_takes_enemy_biy_when_it_wins():
    """Взятие единственного вражеского бия при своём бие на доске — победа."""
    board = {i: None for i in range(1, 63)}
    board[10] = "черный бий"
    board[29] = "белый бий"
    board[36] = "черная шатра"

    move = get_best_move(board, "черный", depth=3)
    assert move is not None
    assert move == (36, 22)
    result = process_move(board, "черный", move[0], move[1])
    assert result.game_over
    assert "черн" in result.winner.lower()


def test_shatra_promotion_turns_into_batyr_when_reaching_promotion_cell():
    """По правилам шатра превращается в батыра при достижении 60–62 (для чёрных)."""
    board = {i: None for i in range(1, 63)}
    board[57] = "черная шатра"
    board[10] = "черный бий"
    board[53] = "белый бий"

    # 57 -> 60 разрешён словарём ходов чёрной шатры
    result = process_move(board, "черный", 57, 60)
    assert result.updated_positions[60] == "черный батыр"
