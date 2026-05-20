from typing import List, Tuple, Optional, Dict
from game_engine.pieces.base import Piece
from game_engine.pieces.shatra import Shatra
from game_engine.pieces.biy import Biy
from game_engine.pieces.batyr import Batyr


class Board:
    def __init__(self, cells: Dict[int, Optional[str]]):
        for key in list(cells.keys()):
            if isinstance(key, str):
                cells[int(key)] = cells.pop(key)
        self.cells = cells
        self._piece_cache: Dict[int, Optional[Piece]] = {}

    def get_piece_object(self, cell: int) -> Optional[Piece]:
        cell = int(cell) if isinstance(cell, str) else cell
        if cell in self._piece_cache:
            return self._piece_cache[cell]
        piece_name = self.cells.get(cell)
        if not piece_name:
            self._piece_cache[cell] = None
            return None
        color = "белый" if "бел" in piece_name else "черный"
        if "шатра" in piece_name:
            piece = Shatra(color)
        elif "бий" in piece_name:
            piece = Biy(color)
        elif "батыр" in piece_name:
            piece = Batyr(color)
        else:
            self._piece_cache[cell] = None
            return None
        self._piece_cache[cell] = piece
        return piece

    def move_piece(self, from_cell: int, to_cell: int) -> None:
        from_cell = int(from_cell) if isinstance(from_cell, str) else from_cell
        to_cell = int(to_cell) if isinstance(to_cell, str) else to_cell
        self.cells[to_cell] = self.cells[from_cell]
        self.cells[from_cell] = None
        self._piece_cache.clear()

    def remove_piece(self, cell: int) -> None:
        cell = int(cell) if isinstance(cell, str) else cell
        self.cells[cell] = None
        self._piece_cache.clear()

    def get_all_pieces(self) -> List[Tuple[int, Piece]]:
        result = []
        for cell, piece_name in self.cells.items():
            if piece_name:
                piece = self.get_piece_object(cell)
                if piece:
                    result.append((cell, piece))
        return result

    def is_empty(self, cell: int) -> bool:
        cell = int(cell) if isinstance(cell, str) else cell
        return self.cells.get(cell) is None

    def copy_cells(self) -> Dict[int, Optional[str]]:
        return {k: v for k, v in self.cells.items()}