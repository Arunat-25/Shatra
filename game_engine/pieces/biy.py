# pieces/biy.py
from game_engine.словари import black_biy_possible_moves, white_biy_possible_moves, shatra_and_biy_possible_captures
from game_engine.pieces.base import Piece

class Biy(Piece):
    def __init__(self, color: str):
        super().__init__(color)
        # Загружаем нужный словарь ходов в зависимости от цвета
        self.moves_dict = black_biy_possible_moves if color == "черный" else white_biy_possible_moves

    def can_move(self, positions: dict, from_pos: int, to_pos: int) -> bool:
        # 1. Фигура должна существовать, цель должна быть пуста
        if positions.get(from_pos) is None: return False
        if positions.get(to_pos) is not None: return False

        # 2. Ход должен быть в словаре допустимых ходов
        if to_pos not in self.moves_dict.get(from_pos, []): return False

        # 3. Проверка правил крепости (специфично для Бия)
        if not self._can_enter_fortress(positions, from_pos, to_pos):
            return False

        return True

    def can_capture(self, positions: dict, from_pos: int, to_pos: int, pending_captures: list[int] | None = None) -> bool:
        # Бий рубит так же, как Шатра (через шашку, по тому же словарю)
        captures_map = shatra_and_biy_possible_captures.get(from_pos, {})
        enemy_pos = captures_map.get(to_pos)

        if enemy_pos is None: return False
        
        enemy_name = positions.get(enemy_pos)
        # Проверка: на позиции врага стоит вражеская фигура
        if not enemy_name: return False
        # Если своя фигура — не взятие (используем префикс)
        color_prefix = "бел" if self.color == "белый" else "чер"
        if color_prefix in enemy_name: return False

        # Проверка: клетка за врагом (куда прыгаем) должна быть пуста
        if positions.get(to_pos) is not None: return False

        # Проверка правил входа в крепость при взятии
        return self._can_enter_fortress(positions, from_pos, to_pos)

    def _can_enter_fortress(self, positions: dict, from_pos: int, to_pos: int) -> bool:
        # 🟦 Чёрный Бий входит в свою крепость (клетки 1-9)
        if self.color == "черный" and 1 <= to_pos <= 9:
            # Если заходит извне, проверяем: нет ли в крепости своих Шатр
            if from_pos not in range(1, 10):
                for p in range(1, 10):
                    cell = positions.get(p)
                    if cell and "шатра" in cell and "черный" in cell:
                        return False
            return True

        # 🟨 Белый Бий входит в свою крепость (клетки 54-62)
        if self.color == "белый" and 54 <= to_pos <= 62:
            if from_pos not in range(54, 63):
                for p in range(54, 63):
                    cell = positions.get(p)
                    if cell and "шатра" in cell and "белый" in cell:
                        return False
            return True

        # Если ход не в крепость или происходит внутри неё → разрешаем (если прошёл проверку словаря)
        return True

    def get_type(self) -> str:
        return "бий"