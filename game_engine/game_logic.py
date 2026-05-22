from typing import List, Optional
from game_engine.models import GameEvent, GameEventResult
from game_engine.validation import validate_move
from game_engine.moves import process_move, has_mandatory_from_position
from game_engine.endgame import is_game_over, add_to_history
from game_engine.hints import get_hints as _get_hints


class GameLogic:
    """Stateless фасад. Все данные передаются через параметры методов."""

    def handle_event(self, data: GameEvent, batyr_captured_this_turn: List[int] = None,
                     position_history: dict[str, int] = None) -> GameEventResult:
        """
        Единая точка входа.
        data.position — первое нажатие (подсказки)
        data.from_pos + data.to_pos — второе нажатие (ход)
        position_history — история позиций для проверки трёхкратного повтора
        """
        if batyr_captured_this_turn is None:
            batyr_captured_this_turn = []
        if position_history is None:
            position_history = {}

        if data.position is not None and data.to_pos is None:
            return _get_hints(
                cells=data.positions,
                current_color=data.mover_color,
                from_cell=data.position,
                batyr_captured_this_turn=batyr_captured_this_turn,
                chain_capture_cell=data.position_for_mandatory_capture
            )
        elif data.from_pos is not None and data.to_pos is not None:
            return process_move(
                cells=data.positions,
                current_color=data.mover_color,
                from_cell=data.from_pos,
                to_cell=data.to_pos,
                chain_capture_cell=data.position_for_mandatory_capture,
                batyr_captured_this_turn=batyr_captured_this_turn,
                position_history=position_history
            )
        else:
            return GameEventResult(message="Некорректные данные события")

    def get_hints(self, cells: dict, current_color: str, from_cell: int,
                  batyr_captured_this_turn: List[int] = None,
                  chain_capture_cell: int = None) -> GameEventResult:
        """Делегирует в функцию get_hints из game_engine.hints."""
        return _get_hints(cells, current_color, from_cell, batyr_captured_this_turn, chain_capture_cell)

    def has_mandatory_from_position(self, cells: dict, color: str, pos: int = None) -> bool:
        return has_mandatory_from_position(cells, color, pos)


# Глобальный singleton
logic = GameLogic()
