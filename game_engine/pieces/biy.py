# pieces/biy.py
from game_engine.dictionaries import black_biy_possible_moves, white_biy_possible_moves, shatra_and_biy_possible_captures
from game_engine.pieces.base import Piece, _is_own_color
from typing import Optional

def _dbg(*_args, **_kwargs):
    """No-op. Оставлен, чтобы не трогать места вызова; отладочный лог удалён."""
    return None


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
            _dbg(
                "H4",
                "game_engine/pieces/biy.py:can_move",
                "blocked entering fortress",
                {"color": self.color, "from": from_cell, "to": to_cell},
            )
            return False

        if (self.color == "черный" and 1 <= to_cell <= 10) or (self.color == "белый" and 53 <= to_cell <= 62):
            _dbg(
                "H4",
                "game_engine/pieces/biy.py:can_move",
                "allowed entering fortress",
                {
                    "color": self.color,
                    "from": from_cell,
                    "to": to_cell,
                    "fortressPieces": [cells.get(c) for c in (range(1, 10) if self.color == "черный" else range(54, 63)) if cells.get(c)],
                },
            )
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

        if _is_own_color(enemy_piece, self.color):
            return False

        if cells.get(to_cell) is not None:
            return False

        return self._can_enter_fortress(cells, from_cell, to_cell)

    def _can_enter_fortress(self, cells: dict, from_cell: int, to_cell: int) -> bool:
        if self.color == "черный" and 1 <= to_cell <= 10:
            # По правилам: нельзя ходить/бить в свою крепость/ворота, если там есть хотя бы одна своя шатра
            for cell in range(1, 10):
                piece = cells.get(cell)
                if piece and "черная шатра" in piece:
                    return False
            return True

        if self.color == "белый" and 53 <= to_cell <= 62:
            for cell in range(54, 63):
                piece = cells.get(cell)
                if piece and "белая шатра" in piece:
                    return False
            return True

        return True

    def get_type(self) -> str:
        return "бий"