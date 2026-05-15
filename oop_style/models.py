# models.py
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class MoveData:
    """Входные данные от фронтенда"""
    positions: dict
    mover_color: str
    from_pos: int
    to_pos: int
    position_for_mandatory_capture: Optional[int] = None

@dataclass
class MoveResult:
    """Результат от GameLogic"""
    message: str
    movers_color: Optional[str]
    captured_positions: List[int] = field(default_factory=list)
    game_over: bool = False
    winner: Optional[str] = None
    updated_positions: Optional[dict] = None  # ← Новое поле
    opportunity_pass_the_move: bool = False    # ← Для бия