# pieces/biy.py
from game_engine.словари import black_biy_possible_moves, white_biy_possible_moves, shatra_and_biy_possible_captures
from game_engine.pieces.base import Piece
from typing import Optional


class Biy(Piece):
    def __init__(self, color: str):
        super().__init__(color)
        self.possible_moves = black_biy_possible_moves if color == "черный" else white_biy_possible_moves

    def can_move(self, cells: dict, from_cell: int, to_cell: int) -> bool:
        if cells.get(from_cell) is None:
            return False
        if cells.get(to_cell) is not None:
            return False

        if to_cell not in self.possible_moves.get(from_cell, []):
            return False

        if not self._can_enter_fortress(cells, from_cell, to_cell):
            return False

        return True

    def _find_enemy_cell_for_capture(self, cells: dict, from_cell: int, to_cell: int) -> Optional[int]:
        possible_captures = shatra_and_biy_possible_captures.get(from_cell, {})
        return possible_captures.get(to_cell)

    def _can_capture_impl(self, cells: dict, from_cell: int, to_cell: int, captured_this_turn: list[int] | None = None) -> bool:
        if captured_this_turn is None:
            captured_this_turn = []

        enemy_cell = self._find_enemy_cell_for_capture(cells, from_cell, to_cell)
        if enemy_cell is None:
            return False

        enemy_piece = cells.get(enemy_cell)
        if not enemy_piece:
            return False

        if cells.get(to_cell) is not None:
            return False

        return self._can_enter_fortress(cells, from_cell, to_cell)

    def _can_enter_fortress(self, cells: dict, from_cell: int, to_cell: int) -> bool:
        # Чёрный Бий входит в свою крепость (клетки 1-9)
        if self.color == "черный" and 1 <= to_cell <= 9:
            if from_cell not in range(1, 10):
                for cell in range(1, 10):
                    piece = cells.get(cell)
                    if piece and "черная шатра" in piece:
                        return False
            return True

        # Белый Бий входит в свою крепость (клетки 54-62)
        if self.color == "белый" and 54 <= to_cell <= 62:
            if from_cell not in range(54, 63):
                for cell in range(54, 63):
                    piece = cells.get(cell)
                    if piece and "белая шатра" in piece:
                        return False
            return True

        return True

    def get_type(self) -> str:
        return "бий"