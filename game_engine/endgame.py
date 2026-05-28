from typing import Tuple, Optional
from game_engine.board import Board


def _count_biys(board: Board) -> int:
    """Считает количество биев на доске."""
    count = 0
    for pos, piece_name in board.cells.items():
        if piece_name and "бий" in piece_name:
            count += 1
    return count


def _only_two_biys_left(board: Board) -> bool:
    """Проверяет, что на доске остались только два бия и больше никаких фигур."""
    biy_count = 0
    other_count = 0
    for pos, piece_name in board.cells.items():
        if piece_name:
            if "бий" in piece_name:
                biy_count += 1
            else:
                other_count += 1
    return biy_count == 2 and other_count == 0


def is_game_over(board: Board, position_history: dict = None,
                 moves_with_two_biys: int = 0) -> Tuple[bool, Optional[str]]:
    """Проверяет, закончилась ли игра.
    
    Возвращает (True, winner_message) если игра окончена, иначе (False, None).
    """
    biy_count = 0
    last_biy_color = None
    for pos, piece_name in board.cells.items():
        if piece_name and "бий" in piece_name:
            biy_count += 1
            last_biy_color = "белый" if "бел" in piece_name else "черный"
    if biy_count == 1:
        return True, f"{last_biy_color.capitalize()} бий победил!"

    # Ничья: 3 хода, когда на доске остались только два бия
    if biy_count == 2 and moves_with_two_biys >= 3 and _only_two_biys_left(board):
        return True, "Ничья! Сделано 3 хода с двумя биями."

    if position_history:
        pos_key = str(sorted(board.cells.items()))
        if position_history.get(pos_key, 0) >= 3:
            return True, "Ничья! Позиция повторилась 3 раза."

    return False, None


def add_to_history(position_history: dict, positions: dict):
    """Добавляет позицию в историю для обнаружения повторений."""
    pos_key = str(sorted(positions.items()))
    position_history[pos_key] = position_history.get(pos_key, 0) + 1
