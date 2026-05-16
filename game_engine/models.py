from dataclasses import dataclass, field
from typing import Optional, List

# ─────────────────────────────────────────────────────────────
# Входные данные (унифицированные)
# ─────────────────────────────────────────────────────────────
@dataclass
class GameEvent:
    """
    Единый входной объект для GameLogic.handle_ivent()
    
    Для хода: position=None, from_pos=39, to_pos=32
    Для подсказок: position=39, from_pos=None, to_pos=None
    """
    positions: dict                          # Состояние доски (ключи int)
    mover_color: str                         # Кто ходит
    from_pos: Optional[int] = None           # Откуда (для хода)
    to_pos: Optional[int] = None             # Куда (для хода)
    position: Optional[int] = None           # Позиция для подсказок
    position_for_mandatory_capture: Optional[int] = None


# ─────────────────────────────────────────────────────────────
# Выходные данные (унифицированные)
# ─────────────────────────────────────────────────────────────
@dataclass
class GameEventResult:
    """
    Единый результат от GameLogic.handle_ivent()
    """
    # Общие поля
    message: str = ""
    movers_color: Optional[str] = None
    game_over: bool = False
    winner: Optional[str] = None
    updated_positions: Optional[dict] = None
    opportunity_pass_the_move: bool = False
    
    # Для хода: какие позиции были захвачены в ЭТОМ ходу
    captured_positions: List[int] = field(default_factory=list)
    
    # Для подсказок: какие фигуры уже захвачены батыром в цепочке (виртуально)
    captured_pieces: List[int] = field(default_factory=list)
    
    # Для подсказок: куда можно ходить обязательно
    essential_positions: List[int] = field(default_factory=list)