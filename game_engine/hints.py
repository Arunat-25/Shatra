from typing import List
from game_engine.board import Board
from game_engine.models import GameEventResult
from game_engine.validation import validate_move
from game_engine.message_codes import CAPTURE_CONTINUE_SAME
from game_engine.dictionaries import (
    shatra_and_biy_possible_captures,
    batyr_moves_and_captures,
    black_shatra_possible_moves,
    white_shatra_possible_moves,
    black_biy_possible_moves,
    white_biy_possible_moves,
)


def _get_all_candidates(
    cells: dict,
    current_color: str,
    from_cell: int,
    piece_type: str
) -> List[int]:
    """Собирает все возможные цели из словарей (ходы + взятия)."""
    candidates = set()

    if piece_type in ["шатра", "бий"]:
        moves = None
        if piece_type == "шатра":
            moves = black_shatra_possible_moves if current_color == "черный" else white_shatra_possible_moves
        else:
            moves = black_biy_possible_moves if current_color == "черный" else white_biy_possible_moves
        for target in moves.get(from_cell, []):
            candidates.add(target)
        for target in shatra_and_biy_possible_captures.get(from_cell, {}):
            candidates.add(target)

    elif piece_type == "батыр":
        for direction in batyr_moves_and_captures.get(from_cell, []):
            for target in direction:
                candidates.add(target)

    return list(candidates)


def get_hints(
    cells: dict,
    current_color: str,
    from_cell: int,
    batyr_captured_this_turn: List[int] = None,
    chain_capture_cell: int = None
) -> GameEventResult:
    """Возвращает подсказки (куда можно пойти) для фигуры на from_cell.
    
    Простая прослойка: собирает кандидатов из словарей, прогоняет через
    validate_move(), подсвечивает то, что вернуло True.
    """
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []

    board = Board(cells)
    piece = board.get_piece_object(from_cell)
    if not piece or piece.get_color() != current_color:
        return GameEventResult(essential_positions=[], captured_pieces=batyr_captured_this_turn.copy())

    # Если есть цепочка — показываем только взятия этой фигурой
    if chain_capture_cell and chain_capture_cell != 0:
        if from_cell != chain_capture_cell:
            return GameEventResult(
                essential_positions=[],
                captured_pieces=batyr_captured_this_turn.copy(),
                message_code=CAPTURE_CONTINUE_SAME,
            )
        return _get_chain_hints(cells, current_color, from_cell, batyr_captured_this_turn, piece)

    # Собираем всех кандидатов и прогоняем через validate_move
    candidates = _get_all_candidates(cells, current_color, from_cell, piece.get_type())
    allowed = []
    for target in candidates:
        valid, _ = validate_move(
            cells, from_cell, target, current_color,
            batyr_captured_this_turn, check_mandatory=True
        )
        if valid:
            allowed.append(target)

    return GameEventResult(
        essential_positions=allowed,
        captured_pieces=batyr_captured_this_turn.copy()
    )


def _get_chain_hints(
    cells: dict,
    current_color: str,
    from_cell: int,
    batyr_captured_this_turn: List[int],
    piece
) -> GameEventResult:
    """Подсказки для продолжения цепочки взятий."""
    allowed = []
    if piece.get_type() in ["шатра", "бий"]:
        for to_cell in shatra_and_biy_possible_captures.get(from_cell, {}):
            if piece.can_capture(cells, from_cell, to_cell, batyr_captured_this_turn):
                allowed.append(to_cell)
    elif piece.get_type() == "батыр":
        for direction in batyr_moves_and_captures.get(from_cell, []):
            for to_cell in direction:
                if piece.can_capture(cells, from_cell, to_cell, batyr_captured_this_turn):
                    allowed.append(to_cell)
    return GameEventResult(
        essential_positions=allowed,
        captured_pieces=batyr_captured_this_turn.copy()
    )