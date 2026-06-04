from game_engine.dictionaries import batyr_moves_and_captures
from game_engine.pieces.base import Piece, _is_own_color
from typing import Optional


class Batyr(Piece):
    def __init__(self, color: str):
        super().__init__(color)

    def can_move(self, cells: dict, from_cell: int, to_cell: int) -> bool:
        if cells.get(from_cell) is None:
            return False
        if cells.get(to_cell) is not None:
            return False

        # Выход из резерва
        if self.color == "черный" and from_cell in range(1, 10) and to_cell in range(11, 32):
            return True
        if self.color == "белый" and from_cell in range(54, 63) and to_cell in range(32, 53):
            return True

        # Проверка входа в крепость
        if not self._can_enter_fortress(cells, to_cell):
            return False

        return self._check_path(cells, from_cell, to_cell, capture=False)

    def _find_enemy_cell_for_capture(self, cells: dict, from_cell: int, to_cell: int) -> Optional[int]:
        for direction in batyr_moves_and_captures.get(from_cell, []):
            if to_cell in direction:
                for cell in direction:
                    if cell == to_cell:
                        return None
                    piece = cells.get(cell)
                    if piece and not _is_own_color(piece, self.color):
                        return cell
        return None

    def _can_capture_impl(self, cells: dict, from_cell: int, to_cell: int, captured_this_turn: list = None) -> bool:
        if captured_this_turn is None:
            captured_this_turn = []

        if to_cell in captured_this_turn:
            return False

        if cells.get(to_cell) is not None:
            return False

        enemy_cell = self._find_enemy_cell_for_capture(cells, from_cell, to_cell)
        if not enemy_cell:
            return False
            
        if enemy_cell in captured_this_turn:
            return False

        if self._is_entering_own_fortress(to_cell):
            if self._is_own_shatra_in_fortress(cells):
                return False
            
        return self._check_path(cells, from_cell, to_cell, capture=True, pending_captures=captured_this_turn)
        
    def _is_entering_own_fortress(self, to_cell: int) -> bool:
        if self.color == "черный" and 1 <= to_cell <= 10:
            return True
        if self.color == "белый" and 53 <= to_cell <= 62:
            return True
        return False
        
    def _is_own_shatra_in_fortress(self, cells: dict) -> bool:
        if self.color == "черный":
            for cell in range(1, 10):
                piece = cells.get(cell)
                if piece and "черная шатра" in piece:
                    return True
        else:
            for cell in range(54, 63):
                piece = cells.get(cell)
                if piece and "белая шатра" in piece:
                    return True
        return False
        
    def _can_enter_fortress(self, cells: dict, to_cell: int) -> bool:
        if self._is_entering_own_fortress(to_cell):
            if self._is_own_shatra_in_fortress(cells):
                return False
        return True

    def _check_path(self, cells: dict, from_cell: int, to_cell: int, capture: bool, pending_captures: list = None) -> bool:
        pending = pending_captures or []

        for direction in batyr_moves_and_captures.get(from_cell, []):
            pieces_count = 0
            enemy_cell = None

            for cell in direction:
                if cell == to_cell:
                    if pieces_count == 0:
                        return not capture and cells.get(to_cell) is None
                    if pieces_count == 1 and enemy_cell:
                        if not capture:
                            return False
                        return cells.get(to_cell) is None
                    return False

                cell_content = cells.get(cell)
                is_pending = cell in pending

                if cell_content is not None or is_pending:
                    pieces_count += 1
                    if cell_content and not _is_own_color(cell_content, self.color):
                        enemy_cell = cell

        return False

    def get_type(self) -> str:
        return "батыр"