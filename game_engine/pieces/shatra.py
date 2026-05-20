# pieces/shatra.py
from game_engine.словари import black_shatra_possible_moves, white_shatra_possible_moves, shatra_and_biy_possible_captures
from game_engine.pieces.base import Piece
from typing import Optional


class Shatra(Piece):
    def __init__(self, color: str):
        super().__init__(color)
        self.possible_moves = black_shatra_possible_moves if color == "черный" else white_shatra_possible_moves

    def can_move(self, cells: dict, from_cell: int, to_cell: int) -> bool:
        if cells.get(from_cell) is None:
            return False
        if cells.get(to_cell) is not None:
            return False

        if to_cell not in self.possible_moves.get(from_cell, []):
            return False

        # Выход из крепости (выставление): проверяем, что впереди нет своих фигур
        if self.color == "черный" and 1 <= from_cell <= 9:
            # Очерёдность выставления чёрных: 9 → 8 → 7→ ... →1
            # Проверяем клетки с БОЛЬШИМ номером чем текущая
            for cell in range(from_cell + 1, 10):
                piece = cells.get(cell)
                # Проверяем только шатры того же цвета
                if piece and "черная шатра" in piece:
                    return False
        elif self.color == "белый" and 54 <= from_cell <= 62:
            # Очерёдность выставления белых: 54 →55 →56→ ... →62
            # Проверяем клетки с МЕНЬШИМ номером чем текущая
            for cell in range(54, from_cell):
                piece = cells.get(cell)
                # Проверяем только шатры того же цвета
                if piece and "белая шатра" in piece:
                    return False
        return True

    def _find_enemy_cell_for_capture(self, cells: dict, from_cell: int, to_cell: int) -> Optional[int]:
        possible_captures = shatra_and_biy_possible_captures.get(from_cell, {})
        return possible_captures.get(to_cell)

    def _can_capture_impl(self, cells: dict, from_cell: int, to_cell: int, captured_this_turn: list = None) -> bool:
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

        # "Турецкий удар": нельзя дважды бить одну фигуру
        if enemy_cell in captured_this_turn:
            return False

        # Шатры с большого поля не могут бить в свою крепость или ворота
        if self.color == "белый":
            # Своя крепость белых: 53 (ворота), 54-62 (крепость)
            # "Большое поле" для белых: от 32 до 52
            if 32 <= from_cell <= 52 and 53 <= to_cell <= 62:
                return False
        else:  # чёрный
            # Своя крепость чёрных: 1-9 (крепость), 10 (ворота)
            # "Большое поле" для чёрных: от 11 до 31
            if 11 <= from_cell <= 31 and 1 <= to_cell <= 10:
                return False

        return self._can_enter_fortress(cells, from_cell, to_cell)

    def _can_enter_fortress(self, cells: dict, from_cell: int, to_cell: int) -> bool:
        # Чёрные входят в крепость 53-62
        if self.color == "черный" and 53 <= to_cell <= 62:
            if from_cell not in range(53, 63):
                for cell in range(53, 63):
                    if cells.get(cell) and "черный" in cells[cell]:
                        return False
            return True
        # Белые входят в крепость 1-10
        if self.color == "белый" and 1 <= to_cell <= 10:
            if from_cell not in range(1, 11):
                for cell in range(1, 11):
                    if cells.get(cell) and "белый" in cells[cell]:
                        return False
            return True
        return True

    def get_type(self) -> str:
        return "шатра"