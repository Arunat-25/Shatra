from game_engine.models import MoveData, MoveResult
from game_engine.board import Board
from typing import List, Tuple, Optional
import copy

# Глобальная история для правила 3-кратного повторения позиции
history_of_positions: dict[str, int] = {}


class GameLogic:
    def __init__(self):
        # Временный список фигур, съеденных батыром в текущем ходе (для цепных взятий)
        self.pending_batyr_captures: List[int] = []

    def process_move(self, data: MoveData) -> MoveResult:
        """Основной метод обработки события. Возвращает обновленное состояние или подсказки"""
        print(f"🎮 ХОД: {data.from_pos} → {data.to_pos}, игрок: {data.mover_color}")
        print(f"🔍 Фигура на {data.from_pos}: {data.positions.get(data.from_pos)}")
        print(f"🔍 Фигура на {data.to_pos}: {data.positions.get(data.to_pos)}")
        # Копируем доску, чтобы не мутировать исходный словарь из запросаируем доску, чтобы не мутировать исходный словарь из запроса
        current_positions = copy.deepcopy(data.positions)
        board = Board(current_positions)
        mover = data.mover_color

        # 1. Проверка, не закончена ли игра до хода
        is_over, winner = self._is_game_over(board)
        if is_over:
            return MoveResult(
                message=f"Игра окончена: {winner}",
                movers_color=None,
                updated_positions=current_positions,
                game_over=True,
                winner=winner
            )

        # 2. Логика продолжения взятия (chain capture)
        if data.position_for_mandatory_capture is not None:
            if data.position_for_mandatory_capture == 0:
                # Специальный ход "0" для бия: передача хода
                next_mover = "черный" if mover == "белый" else "белый"
                self.pending_batyr_captures.clear()
                self._add_to_history(current_positions)
                is_over, winner = self._is_game_over(board)
                return MoveResult(
                    message=f"Ход передан. Теперь ходит {next_mover}",
                    movers_color=next_mover,
                    updated_positions=current_positions,
                    game_over=is_over,
                    winner=winner
                )
            
            if data.from_pos != data.position_for_mandatory_capture:
                return MoveResult(
                    message="Продолжайте взятие той же фигурой!",
                    movers_color=mover,
                    updated_positions=current_positions
                )

        # 3. Проверка обязательных взятий
        mandatory = self._get_all_mandatory_captures(board, mover)
        from_positions = {f for f, _ in mandatory}

        if mandatory:
            if data.from_pos not in from_positions:
                return MoveResult(
                    message="Обязательное взятие!",
                    movers_color=mover,
                    updated_positions=current_positions
                )
            allowed_targets = {t for f, t in mandatory if f == data.from_pos}
            if data.to_pos not in allowed_targets:
                return MoveResult(
                    message="Нужно бить!",
                    movers_color=mover,
                    updated_positions=current_positions
                )

        # 4. Выполнение хода
        piece_obj = board.get_piece_object(data.from_pos)
        if not piece_obj:
            return MoveResult(
                message="Нет фигуры на выбранной позиции",
                movers_color=mover,
                updated_positions=current_positions
            )

        captured_list = []
        success = False

        # Попытка взятия
        if piece_obj.can_capture(current_positions, data.from_pos, data.to_pos, self.pending_batyr_captures):
            enemy_pos = self._find_captured_enemy(board, piece_obj, data.from_pos, data.to_pos)
            board.move_piece(data.from_pos, data.to_pos)
            
            if enemy_pos:
                board.remove_piece(enemy_pos)
                captured_list.append(enemy_pos)
                if piece_obj.get_type() == "батыр":
                    self.pending_batyr_captures.append(enemy_pos)
            success = True
            
        # Попытка обычного хода
        elif piece_obj.can_move(current_positions, data.from_pos, data.to_pos):
            board.move_piece(data.from_pos, data.to_pos)
            if piece_obj.get_type() == "батыр":
                self.pending_batyr_captures.clear()
            success = True

        if not success:
            return MoveResult(
                message="Недопустимый ход",
                movers_color=mover,
                updated_positions=current_positions
            )

        # 5. Пост-обработка хода
        opportunity_pass = False
        next_mandatory = self._get_all_mandatory_captures(board, mover)
        can_continue_capture = any(f == data.to_pos for f, _ in next_mandatory)

        # Правило для бия: после взятия может передать ход, даже если есть продолжение
        if piece_obj.get_type() == "бий" and captured_list:
            opportunity_pass = True

        # Если есть обязательное продолжение и бий не передаёт ход → продолжаем
        if can_continue_capture and not opportunity_pass:
            return MoveResult(
                message="Продолжайте взятие!",
                movers_color=mover,
                updated_positions=current_positions,
                captured_positions=captured_list,
                opportunity_pass_the_move=False
            )

        # Смена хода
        next_mover = "черный" if mover == "белый" else "белый"
        self.pending_batyr_captures.clear()
        self._add_to_history(current_positions)

        is_over, winner = self._is_game_over(board)
        
        return MoveResult(
            message=f"Успешно! Теперь ходит {next_mover}",
            movers_color=next_mover,
            updated_positions=current_positions,
            captured_positions=captured_list,
            game_over=is_over,
            winner=winner,
            opportunity_pass_the_move=opportunity_pass
        )

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def get_hints(self, positions: dict, mover_color: str, from_pos: int, 
                  mandatory_pos: int | None = None) -> dict:
        """Возвращает подсказки для фронтенда (подсветка обязательных ходов)"""
        board = Board(positions)
        mandatory = self._get_all_mandatory_captures(board, mover_color)
        allowed = [to for f, to in mandatory if f == from_pos]
        
        return {
            "essential_positions": allowed,
            "captured_pieces": self.pending_batyr_captures.copy()
        }

    def _has_mandatory_from_position(self, positions: dict, color: str, pos: int) -> bool:
        """Проверяет, есть ли обязательное взятие с конкретной позиции"""
        board = Board(positions)
        mandatory = self._get_all_mandatory_captures(board, color)
        return any(f == pos for f, _ in mandatory)

    def _is_game_over(self, board: Board) -> tuple[bool, str | None]:
        """Проверка условий конца игры: 1 бий остался или 3-кратное повторение"""
        # 1. Подсчёт биев
        biy_count = 0
        last_biy_color = None
        
        for pos, piece_name in board.positions.items():
            if piece_name and "бий" in piece_name:
                biy_count += 1
                last_biy_color = "белый" if "бел" in piece_name else "черный"
                
        if biy_count == 1:
            return True, f"{last_biy_color.capitalize()} бий победил!"
        
        # 2. Проверка истории позиций
        pos_key = str(sorted(board.positions.items()))
        if history_of_positions.get(pos_key, 0) >= 3:
            return True, "Ничья! Позиция повторилась 3 раза."
            
        return False, None

    def _get_all_mandatory_captures(self, board: Board, color: str) -> List[Tuple[int, int]]:
        """Возвращает список всех обязательных взятий: [(from_pos, to_pos), ...]"""
        mandatory = []
        opposite = "черный" if color == "белый" else "белый"
        
        for pos, piece_obj in board.get_all_pieces():
            if piece_obj.get_color() != color:
                continue
                
            # Для шатры и бия проверяем словарь взятий
            if piece_obj.get_type() in ["шатра", "бий"]:
                from game_engine.словари import shatra_and_biy_possible_captures
                captures_map = shatra_and_biy_possible_captures.get(pos, {})
                for to_pos, enemy_pos in captures_map.items():
                    enemy_name = board.positions.get(enemy_pos)
                    if (enemy_name and opposite in enemy_name and 
                        board.positions.get(to_pos) is None):
                        mandatory.append((pos, to_pos))
                        
            # Для батыра перебираем направления
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
                            break  # Своя фигура блокирует
                            
                        if opposite in cell_piece and board.positions.get(next_cell) is None:
                            enemy_found = True
                            mandatory.append((pos, next_cell))
                            
        return mandatory

    def _find_captured_enemy(self, board: Board, piece_obj, from_pos: int, to_pos: int) -> int | None:
        """Определяет позицию съеденной фигуры для обновления состояния"""
        if piece_obj.get_type() in ["шатра", "бий"]:
            from game_engine.словари import shatra_and_biy_possible_captures
            return shatra_and_biy_possible_captures.get(from_pos, {}).get(to_pos)
            
        if piece_obj.get_type() == "батыр":
            # Для батыра съеденная фигура уже добавлена в pending_batyr_captures
            # Возвращаем последнюю добавленную, если она ещё на доске (виртуально)
            return self.pending_batyr_captures[-1] if self.pending_batyr_captures else None
            
        return None

    def _add_to_history(self, positions: dict):
        """Добавляет текущую позицию в историю для проверки ничьей"""
        pos_key = str(sorted(positions.items()))
        history_of_positions[pos_key] = history_of_positions.get(pos_key, 0) + 1

    def reset(self):
        """Сброс состояния для новой игры"""
        self.pending_batyr_captures.clear()
        history_of_positions.clear()