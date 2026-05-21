from abc import ABC, abstractmethod
from typing import Optional


def _is_own_color(piece_name, color):
    """Проверить, принадлежит ли фигура тому же цвету, что color."""
    if "бел" in piece_name:
        return color.startswith("бел")
    return color.startswith("чер")


class Piece(ABC):
    def __init__(self, color: str):
        self.color = color

    @abstractmethod
    def can_move(self, cells: dict, from_cell: int, to_cell: int) -> bool:
        pass

    def can_capture(self, cells: dict, from_cell: int, to_cell: int,
                    captured_this_turn: list[int] = None) -> bool:
        """captured_this_turn – для батыра, чтобы знать, кого уже съели в этом ходу"""
        # Базовая проверка: нельзя бить свои фигуры
        enemy_cell = self._find_enemy_cell_for_capture(cells, from_cell, to_cell)
        if enemy_cell:
            enemy_piece = cells.get(enemy_cell)
            if enemy_piece and _is_own_color(enemy_piece, self.color):
                return False
        return self._can_capture_impl(cells, from_cell, to_cell, captured_this_turn)
        
    @abstractmethod
    def _can_capture_impl(self, cells: dict, from_cell: int, to_cell: int,
                          captured_this_turn: list[int] = None) -> bool:
        pass

    @abstractmethod
    def _find_enemy_cell_for_capture(self, cells: dict, from_cell: int, to_cell: int) -> Optional[int]:
        """Возвращает позицию вражеской фигуры для взятия, если она есть"""
        pass

    @abstractmethod
    def get_type(self) -> str:
        pass

    def get_color(self) -> str:
        return self.color