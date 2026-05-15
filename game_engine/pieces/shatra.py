# pieces/shatra.py
from game_engine.словари import black_shatra_possible_moves, white_shatra_possible_moves, shatra_and_biy_possible_captures
from game_engine.pieces.base import Piece

class Shatra(Piece):
    def __init__(self, color: str):
        super().__init__(color)
        self.moves_dict = black_shatra_possible_moves if color == "черный" else white_shatra_possible_moves

    def can_move(self, positions: dict, from_pos: int, to_pos: int) -> bool:
        # 1. Проверка наличия фигуры и пустоты цели
        if positions.get(from_pos) is None: return False
        if positions.get(to_pos) is not None: return False
        
        # 2. Проверка допустимости хода по словарю
        if to_pos not in self.moves_dict.get(from_pos, []): return False

        # 3. Логика выхода из крепости (твоя старая логика)
        if self.color == "черный" and 1 <= from_pos <= 8:
            for p in range(1, from_pos):
                # Если впереди стоит своя фигура - нельзя выйти
                if positions.get(p) and self.color in positions[p]: 
                    return False
        elif self.color == "белый" and 54 <= from_pos <= 62:
            for p in range(from_pos + 1, 63):
                if positions.get(p) and self.color in positions[p]:
                    return False
        return True

    def can_capture(self, positions: dict, from_pos: int, to_pos: int, pending_captures: list = None) -> bool:
        # Взятие шатры (через шашку)
        captures_map = shatra_and_biy_possible_captures.get(from_pos, {})
        enemy_pos = captures_map.get(to_pos)
        
        if enemy_pos is None: return False
        enemy_name = positions.get(enemy_pos)
        
        # Проверка: враг ли это?
        if not enemy_name or self.color in enemy_name: return False
        
        # Проверка: пуста ли клетка за врагом?
        if positions.get(to_pos) is not None: return False

        # Логика входа в крепость (твоя функция can_piece_enter_in_fortress)
        return self._can_enter_fortress(positions, from_pos, to_pos)

    def _can_enter_fortress(self, positions: dict, from_pos: int, to_pos: int) -> bool:
        # Черные входят в 53-62
        if self.color == "черный" and 53 <= to_pos <= 62:
            if from_pos not in range(53, 63): # Если вход извне
                for p in range(53, 63):
                    if positions.get(p) and "черный" in positions[p]: return False
            return True
        # Белые входят в 1-10
        if self.color == "белый" and 1 <= to_pos <= 10:
            if from_pos not in range(1, 11):
                for p in range(1, 11):
                    if positions.get(p) and "белый" in positions[p]: return False
            return True
        return True

    def get_type(self) -> str:
        return "шатра"