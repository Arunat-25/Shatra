from typing import Tuple, Optional
from game_engine.board import Board


def is_game_over(board: Board, position_history: dict = None) -> Tuple[bool, Optional[str]]:
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

    if position_history:
        pos_key = str(sorted(board.cells.items()))
        if position_history.get(pos_key, 0) >= 3:
            return True, "Ничья! Позиция повторилась 3 раза."

    return False, None


def add_to_history(position_history: dict, positions: dict):
    """Добавляет позицию в историю для обнаружения повторений."""
    pos_key = str(sorted(positions.items()))
    position_history[pos_key] = position_history.get(pos_key, 0) + 1