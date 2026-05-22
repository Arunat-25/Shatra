from typing import List
from game_engine.board import Board
from game_engine.models import GameEventResult
from game_engine.validation import get_all_mandatory_captures, validate_move
from game_engine.dictionaries import (
    shatra_and_biy_possible_captures,
    batyr_moves_and_captures,
    black_shatra_possible_moves,
    white_shatra_possible_moves,
    black_biy_possible_moves,
    white_biy_possible_moves,
)


def get_hints(
    cells: dict,
    current_color: str,
    from_cell: int,
    batyr_captured_this_turn: List[int] = None,
    chain_capture_cell: int = None
) -> GameEventResult:
    """Возвращает подсказки (куда можно пойти) для фигуры на from_cell."""
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []

    board = Board(cells)
    piece = board.get_piece_object(from_cell)
    if not piece or piece.get_color() != current_color:
        return GameEventResult(essential_positions=[], captured_pieces=batyr_captured_this_turn.copy())
    if not piece:
        return GameEventResult(essential_positions=[], captured_pieces=batyr_captured_this_turn.copy())

    # Если есть цепочка — показываем только взятия этой фигурой
    if chain_capture_cell and chain_capture_cell != 0:
        if from_cell != chain_capture_cell:
            return GameEventResult(essential_positions=[], captured_pieces=batyr_captured_this_turn.copy(),
                message="Продолжайте взятие той же фигурой!")
        return _get_chain_hints(cells, current_color, from_cell, batyr_captured_this_turn, piece)

    # Проверяем обязательные взятия
    mandatory_captures = get_all_mandatory_captures(board, current_color, batyr_captured_this_turn)
    mandatory_from = {f for f, _ in mandatory_captures}

    if from_cell in mandatory_from:
        if piece.get_type() == "бий":
            allowed = []
            for f, t in mandatory_captures:
                if f == from_cell:
                    allowed.append(t)

            if not batyr_captured_this_turn:
                moves = black_biy_possible_moves if current_color == "черный" else white_biy_possible_moves
                for target in moves.get(from_cell, []):
                    valid, _ = validate_move(
                        cells, from_cell, target, current_color,
                        batyr_captured_this_turn, check_mandatory=False
                    )
                    if valid:
                        allowed.append(target)
            return GameEventResult(
                essential_positions=allowed,
                captured_pieces=batyr_captured_this_turn.copy()
            )
        allowed = [t for f, t in mandatory_captures if f == from_cell]
        return GameEventResult(
            essential_positions=allowed,
            captured_pieces=batyr_captured_this_turn.copy()
        )

    if mandatory_captures:
        return GameEventResult(essential_positions=[], captured_pieces=batyr_captured_this_turn.copy())

    # Нет обязательных взятий — собираем все возможные ходы
    possible_moves = _get_all_possible_moves(cells, current_color, from_cell, batyr_captured_this_turn, piece.get_type())

    return GameEventResult(
        essential_positions=possible_moves,
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
        enemy_prefix = "чер" if current_color == "белый" else "бел"
        for to_cell, enemy_cell in shatra_and_biy_possible_captures.get(from_cell, {}).items():
            enemy_piece = cells.get(enemy_cell)
            target_free = cells.get(to_cell) is None
            if enemy_piece and target_free and enemy_prefix in enemy_piece:
                allowed.append(to_cell)
    elif piece.get_type() == "батыр":
        opponent_prefix = "чер" if current_color == "белый" else "бел"
        for direction in batyr_moves_and_captures.get(from_cell, []):
            enemy_found = False
            for cell in direction:
                cell_piece = cells.get(cell)
                if cell in batyr_captured_this_turn:
                    continue
                if cell_piece and opponent_prefix in cell_piece:
                    if cell not in batyr_captured_this_turn:
                        enemy_found = True
                        # Добавляем только пустые клетки за этим врагом (до следующего врага)
                        for next_cell in direction[direction.index(cell) + 1:]:
                            next_piece = cells.get(next_cell)
                            if next_piece is None:
                                allowed.append(next_cell)
                            elif opponent_prefix in next_piece:
                                # Следующий враг сразу — не добавляем клетки за ним
                                break
                            else:
                                break
                        break
                    continue
    return GameEventResult(
        essential_positions=allowed,
        captured_pieces=batyr_captured_this_turn.copy()
    )


def _get_all_possible_moves(
    cells: dict,
    current_color: str,
    from_cell: int,
    batyr_captured_this_turn: List[int],
    piece_type: str
) -> List[int]:
    """Собирает все возможные ходы для фигуры."""
    possible_moves = []

    if piece_type == "шатра":
        moves = black_shatra_possible_moves if current_color == "черный" else white_shatra_possible_moves
        for target in moves.get(from_cell, []):
            valid, _ = validate_move(
                cells, from_cell, target, current_color,
                batyr_captured_this_turn, check_mandatory=False
            )
            if valid:
                possible_moves.append(target)

        for target in shatra_and_biy_possible_captures.get(from_cell, {}):
            valid, _ = validate_move(
                cells, from_cell, target, current_color,
                batyr_captured_this_turn, check_mandatory=False
            )
            if valid:
                possible_moves.append(target)

    elif piece_type == "бий":
        moves = black_biy_possible_moves if current_color == "черный" else white_biy_possible_moves
        for target in moves.get(from_cell, []):
            valid, _ = validate_move(
                cells, from_cell, target, current_color,
                batyr_captured_this_turn, check_mandatory=False
            )
            if valid:
                possible_moves.append(target)

        for target in shatra_and_biy_possible_captures.get(from_cell, {}):
            valid, _ = validate_move(
                cells, from_cell, target, current_color,
                batyr_captured_this_turn, check_mandatory=False
            )
            if valid:
                possible_moves.append(target)

    elif piece_type == "батыр":
        for direction in batyr_moves_and_captures.get(from_cell, []):
            for target in direction:
                valid, _ = validate_move(
                    cells, from_cell, target, current_color,
                    batyr_captured_this_turn, check_mandatory=False
                )
                if valid:
                    possible_moves.append(target)

    return possible_moves