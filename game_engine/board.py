from typing import List, Tuple, Optional, Dict
from game_engine.pieces.base import Piece
from game_engine.pieces.shatra import Shatra
from game_engine.pieces.biy import Biy
from game_engine.pieces.batyr import Batyr


class Board:
    def __init__(self, positions: Dict[int, Optional[str]]):
        # Конвертируем ключи в int на месте (если нужно)
        for key in list(positions.keys()):
            if isinstance(key, str):
                positions[int(key)] = positions.pop(key)
        
        self.positions = positions  # ← тот же объект, не копия!
        self._pieces_cache: Dict[int, Optional[Piece]] = {}

    def get_piece_object(self, pos: int) -> Optional[Piece]:
        """Создаёт объект фигуры из строкового имени"""
        pos = int(pos) if isinstance(pos, str) else pos
        
        # Проверяем кеш
        if pos in self._pieces_cache:
            return self._pieces_cache[pos]
        
        name = self.positions.get(pos)
        if not name:
            self._pieces_cache[pos] = None
            return None
        
        # Определяем цвет и тип
        color = "белый" if "бел" in name else "черный"
        
        if "шатра" in name:
            piece = Shatra(color)
        elif "бий" in name:
            piece = Biy(color)
        elif "батыр" in name:
            piece = Batyr(color)
        else:
            self._pieces_cache[pos] = None
            return None
        
        self._pieces_cache[pos] = piece
        return piece

    def move_piece(self, from_pos: int, to_pos: int) -> None:
        """Перемещает фигуру, сохраняя все ключи доски"""
        from_pos = int(from_pos) if isinstance(from_pos, str) else from_pos
        to_pos = int(to_pos) if isinstance(to_pos, str) else to_pos
        
        # Перемещаем значение
        self.positions[to_pos] = self.positions[from_pos]
        # Освобождаем старую позицию (не удаляем ключ!)
        self.positions[from_pos] = None
        # Сбрасываем кеш
        self._pieces_cache.clear()

    def remove_piece(self, pos: int) -> None:
        """Удаляет фигуру с позиции"""
        pos = int(pos) if isinstance(pos, str) else pos
        self.positions[pos] = None
        self._pieces_cache.clear()

    def get_all_pieces(self) -> List[Tuple[int, Piece]]:
        """Возвращает список всех фигур: [(позиция, объект), ...]"""
        result = []
        for pos, name in self.positions.items():
            if name:  # если клетка не пуста
                piece = self.get_piece_object(pos)
                if piece:
                    result.append((pos, piece))
        return result

    def is_empty(self, pos: int) -> bool:
        """Проверяет, пуста ли клетка"""
        pos = int(pos) if isinstance(pos, str) else pos
        return self.positions.get(pos) is None

    def copy_positions(self) -> Dict[int, Optional[str]]:
        """Возвращает копию словаря позиций (для отправки на клиент)"""
        return {k: v for k, v in self.positions.items()}