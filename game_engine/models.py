from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class GameEvent:
    """
    Единый входной объект для GameLogic.handle_event()

    Для хода: position=None, from_pos=39, to_pos=32
    Для подсказок: position=39, from_pos=None, to_pos=None
    """
    positions: dict
    mover_color: str
    from_pos: Optional[int] = None
    to_pos: Optional[int] = None
    position: Optional[int] = None
    position_for_mandatory_capture: Optional[int] = None


@dataclass
class GameEventResult:
    """Единый результат от GameLogic.handle_event()."""
    message_code: str = ""
    message_params: dict = field(default_factory=dict)
    movers_color: Optional[str] = None
    game_over: bool = False
    winner_color: Optional[str] = None
    draw_reason: Optional[str] = None
    updated_positions: Optional[dict] = None
    opportunity_pass_the_move: bool = False
    captured_positions: List[int] = field(default_factory=list)
    captured_pieces: List[int] = field(default_factory=list)
    essential_positions: List[int] = field(default_factory=list)
    position_for_mandatory_capture: Optional[int] = None

    @property
    def message(self) -> str:
        """Legacy accessor for tests migrating to message_code."""
        return self.message_code

    @property
    def winner(self) -> Optional[str]:
        """Legacy: winner color string for game state."""
        return self.winner_color
