# pieces/batyr.py
from словари import batyr_moves_and_captures
from .base import Piece

class Batyr(Piece):
    def __init__(self, color: str):
        super().__init__(color)

    def can_move(self, positions: dict, from_pos: int, to_pos: int) -> bool:
        if positions.get(from_pos) is None: return False
        if positions.get(to_pos) is not None: return False

        # Выход из резерва
        if self.color == "черный" and from_pos in range(1, 10) and to_pos in range(11, 32): return True
        if self.color == "белый" and from_pos in range(54, 63) and to_pos in range(32, 53): return True

        # Обычный ход (проверка пути)
        return self._check_path(positions, from_pos, to_pos, capture=False)

    def can_capture(self, positions: dict, from_pos: int, to_pos: int, pending_captures: list = None) -> bool:
        if positions.get(from_pos) is None: return False
        if positions.get(to_pos) is not None: return False

        # pending_captures - это список позиций, которые батыр уже "съел" в этом ходу (виртуально)
        return self._check_path(positions, from_pos, to_pos, capture=True, pending_captures=pending_captures)

    def _check_path(self, positions: dict, from_pos: int, to_pos: int, capture: bool, pending_captures: list = None) -> bool:
        pending = pending_captures or []
        
        for direction in batyr_moves_and_captures.get(from_pos, []):
            pieces_count = 0
            enemy_pos = None
            
            for pos in direction:
                if pos == to_pos:
                    # Если дошли до цели
                    if pieces_count == 0: return True # Просто ход
                    if pieces_count == 1 and enemy_pos: 
                        if capture: 
                            # Тут логика добавления в список съеденных
                            # Но так как мы только проверяем can_capture, 
                            # GameLogic сам обновит список
                            pass
                        return True
                    return False # Слишком много фигур
                
                # Проверяем клетку на пути
                cell_content = positions.get(pos)
                is_pending_capture = pos in pending
                
                if cell_content is not None or is_pending_capture:
                    pieces_count += 1
                    if cell_content and self.color not in cell_content: # Враг
                        enemy_pos = pos
                else:
                    enemy_pos = None # Сброс, если прошел пустую клетку после врага (не по правилам батыра)
                    
        return False

    def get_type(self) -> str:
        return "батыр"