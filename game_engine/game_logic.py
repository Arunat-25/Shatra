from game_engine.models import GameEvent, GameEventResult
from game_engine.board import Board
from typing import List, Tuple, Optional
import copy

history_of_positions: dict[str, int] = {}


class GameLogic:
    def __init__(self):
        self.pending_batyr_captures: List[int] = []

    def handle_event(self, data: GameEvent) -> GameEventResult:
        if data.position is not None and data.to_pos is None:
            return self._get_hints_result(
                positions=data.positions,
                mover_color=data.mover_color,
                from_pos=data.position
            )
        elif data.from_pos is not None and data.to_pos is not None:
            return self._process_move(data)
        else:
            return GameEventResult(message="Некорректные данные события")

    def _get_hints_result(self, positions: dict, mover_color: str, from_pos: int) -> GameEventResult:
        board = Board(positions)
        mandatory = self._get_all_mandatory_captures(board, mover_color)
        allowed = [to for f, to in mandatory if f == from_pos]
        return GameEventResult(
            essential_positions=allowed,
            captured_pieces=self.pending_batyr_captures.copy()
        )

    def _process_move(self, data: GameEvent) -> GameEventResult:
        working_positions = copy.deepcopy(data.positions)
        board = Board(working_positions)
        mover = data.mover_color

        is_over, winner = self._is_game_over(board)
        if is_over:
            return GameEventResult(
                message=f"Игра окончена: {winner}",
                movers_color=None,
                updated_positions=data.positions,
                game_over=True,
                winner=winner
            )

        if data.position_for_mandatory_capture is not None:
            if data.position_for_mandatory_capture == 0:
                next_mover = "черный" if mover == "белый" else "белый"
                self.pending_batyr_captures.clear()
                self._add_to_history(working_positions)
                is_over, winner = self._is_game_over(board)
                data.positions.clear()
                data.positions.update(working_positions)
                return GameEventResult(
                    message=f"Ход передан. Теперь ходит {next_mover}",
                    movers_color=next_mover,
                    updated_positions=data.positions,
                    game_over=is_over,
                    winner=winner
                )
            if data.from_pos != data.position_for_mandatory_capture:
                return GameEventResult(
                    message="Продолжайте взятие той же фигурой!",
                    movers_color=mover,
                    updated_positions=data.positions
                )

        mandatory = self._get_all_mandatory_captures(board, mover)
        from_positions = {f for f, _ in mandatory}

        if mandatory:
            if data.from_pos not in from_positions:
                return GameEventResult(
                    message="Обязательное взятие!",
                    movers_color=mover,
                    updated_positions=data.positions
                )
            allowed_targets = {t for f, t in mandatory if f == data.from_pos}
            if data.to_pos not in allowed_targets:
                return GameEventResult(
                    message="Нужно бить!",
                    movers_color=mover,
                    updated_positions=data.positions
                )

        piece_obj = board.get_piece_object(data.from_pos)
        if not piece_obj:
            return GameEventResult(
                message="Нет фигуры на выбранной позиции",
                movers_color=mover,
                updated_positions=data.positions
            )

        captured_list = []
        success = False

        if piece_obj.can_capture(working_positions, data.from_pos, data.to_pos, self.pending_batyr_captures):
            enemy_pos = self._find_captured_enemy(board, piece_obj, data.from_pos, data.to_pos)
            board.move_piece(data.from_pos, data.to_pos)
            if enemy_pos:
                board.remove_piece(enemy_pos)
                captured_list.append(enemy_pos)
                if piece_obj.get_type() == "батыр":
                    self.pending_batyr_captures.append(enemy_pos)
            success = True
        elif piece_obj.can_move(working_positions, data.from_pos, data.to_pos):
            board.move_piece(data.from_pos, data.to_pos)
            if piece_obj.get_type() == "батыр":
                self.pending_batyr_captures.clear()
            success = True

        if not success:
            return GameEventResult(
                message="Недопустимый ход",
                movers_color=mover,
                updated_positions=data.positions
            )

        opportunity_pass = False
        next_mandatory = self._get_all_mandatory_captures(board, mover)
        can_continue_capture = any(f == data.to_pos for f, _ in next_mandatory)

        if piece_obj.get_type() == "бий" and captured_list:
            opportunity_pass = True

        if can_continue_capture and not opportunity_pass:
            data.positions.clear()
            data.positions.update(working_positions)
            return GameEventResult(
                message="Продолжайте взятие!",
                movers_color=mover,
                updated_positions=data.positions,
                captured_positions=captured_list,
                opportunity_pass_the_move=False
            )

        next_mover = "черный" if mover == "белый" else "белый"
        self.pending_batyr_captures.clear()
        self._add_to_history(working_positions)
        
        data.positions.clear()
        data.positions.update(working_positions)

        is_over, winner = self._is_game_over(board)
        
        return GameEventResult(
            message=f"Успешно! Теперь ходит {next_mover}",
            movers_color=next_mover,
            updated_positions=data.positions,
            captured_positions=captured_list,
            game_over=is_over,
            winner=winner,
            opportunity_pass_the_move=opportunity_pass
        )

    def _has_mandatory_from_position(self, positions: dict, color: str, pos: int) -> bool:
        board = Board(positions)
        mandatory = self._get_all_mandatory_captures(board, color)
        return any(f == pos for f, _ in mandatory)

    def _is_game_over(self, board: Board) -> tuple[bool, Optional[str]]:
        biy_count = 0
        last_biy_color = None
        for pos, piece_name in board.positions.items():
            if piece_name and "бий" in piece_name:
                biy_count += 1
                last_biy_color = "белый" if "бел" in piece_name else "черный"
        if biy_count == 1:
            return True, f"{last_biy_color.capitalize()} бий победил!"
        pos_key = str(sorted(board.positions.items()))
        if history_of_positions.get(pos_key, 0) >= 3:
            return True, "Ничья! Позиция повторилась 3 раза."
        return False, None

    def _get_all_mandatory_captures(self, board: Board, color: str) -> List[Tuple[int, int]]:
        mandatory = []
        opposite = "черный" if color == "белый" else "белый"
        for pos, piece_obj in board.get_all_pieces():
            if piece_obj.get_color() != color:
                continue
            if piece_obj.get_type() in ["шатра", "бий"]:
                from game_engine.словари import shatra_and_biy_possible_captures
                captures_map = shatra_and_biy_possible_captures.get(pos, {})
                for to_pos, enemy_pos in captures_map.items():
                    enemy_name = board.positions.get(enemy_pos)
                    if (enemy_name and opposite in enemy_name and 
                        board.positions.get(to_pos) is None):
                        mandatory.append((pos, to_pos))
            elif piece_obj.get_type() == "батыр":
                from game_engine.словари import batyr_moves_and_captures
                for direction in batyr_moves_and_captures.get(pos, []):
                    enemy_found = False
                    for idx, cell in enumerate(direction[:-1]):
                        next_cell = direction[idx + 1]
                        cell_piece = board.positions.get(cell)
                        if cell_piece is None:
                            if enemy_found:
                                mandatory.append((pos, cell))
                            continue
                        if color in cell_piece:
                            break
                        if opposite in cell_piece and board.positions.get(next_cell) is None:
                            enemy_found = True
                            mandatory.append((pos, next_cell))
        return mandatory

    def _find_captured_enemy(self, board: Board, piece_obj, from_pos: int, to_pos: int) -> Optional[int]:
        if piece_obj.get_type() in ["шатра", "бий"]:
            from game_engine.словари import shatra_and_biy_possible_captures
            return shatra_and_biy_possible_captures.get(from_pos, {}).get(to_pos)
        if piece_obj.get_type() == "батыр":
            return self.pending_batyr_captures[-1] if self.pending_batyr_captures else None
        return None

    def _add_to_history(self, positions: dict):
        pos_key = str(sorted(positions.items()))
        history_of_positions[pos_key] = history_of_positions.get(pos_key, 0) + 1

    def reset(self):
        self.pending_batyr_captures.clear()
        history_of_positions.clear()