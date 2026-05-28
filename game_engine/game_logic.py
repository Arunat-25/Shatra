from typing import Optional
from game_engine.models import GameEvent, GameEventResult
from game_engine.moves import process_move, has_mandatory_from_position
from game_engine.hints import get_hints as _get_hints


class GameLogic:
    """Stateless фасад. Все данные передаются через параметры методов."""

    def handle_event(self, data: GameEvent,
                     batyr_captured_this_turn: Optional[list[int]] = None,
                     position_history: Optional[dict[str, int]] = None,
                     moves_with_two_biys: int = 0) -> GameEventResult:
        """
        Единая точка входа.
        data.position — первое нажатие (подсказки)
        data.from_pos + data.to_pos — второе нажатие (ход)
        position_history — история позиций для проверки трёхкратного повтора
        """
        _captured = batyr_captured_this_turn or []
        _history = position_history or {}

        if data.position is not None and data.to_pos is None:
            return _get_hints(
                cells=data.positions,
                current_color=data.mover_color,
                from_cell=data.position,
                batyr_captured_this_turn=_captured,
                chain_capture_cell=data.position_for_mandatory_capture
            )
        if data.from_pos is not None and data.to_pos is not None:
            return process_move(
                cells=data.positions,
                current_color=data.mover_color,
                from_cell=data.from_pos,
                to_cell=data.to_pos,
                chain_capture_cell=data.position_for_mandatory_capture,
                batyr_captured_this_turn=_captured,
                position_history=_history,
                moves_with_two_biys=moves_with_two_biys
            )
        return GameEventResult(message="Некорректные данные события")

    def has_mandatory_from_position(self, cells: dict, color: str, pos: int = None) -> bool:
        return has_mandatory_from_position(cells, color, pos)


# Глобальный singleton
logic = GameLogic()
