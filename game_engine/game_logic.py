from game_engine.models import GameEvent, GameEventResult
from game_engine.board import Board
from typing import List, Tuple, Optional
import copy

position_history: dict[str, int] = {}

PROMOTION_FOR_WHITE = {1, 2, 3}     # белая шатра → батыр  
PROMOTION_FOR_BLACK = {60, 61, 62}  # чёрная шатра → батыр


def _promote_shatra(cells: dict, cell: int, color: str) -> bool:
    """Превращает шатру в батыра, если фигура дошла до края доски.
       Возвращает True, если превращение произошло."""
    cell_name = cells.get(cell)
    if not cell_name or "шатра" not in cell_name:
        return False
    if color == "белый" and cell in PROMOTION_FOR_WHITE:
        cells[cell] = "белый батыр"
        return True
    if color == "черный" and cell in PROMOTION_FOR_BLACK:
        cells[cell] = "черный батыр"
        return True
    return False


class GameLogic:
    def __init__(self):
        pass

    def handle_event(self, data: GameEvent, batyr_captured_this_turn: List[int] = None) -> GameEventResult:
        """
        Единая точка входа.
        data.position — первое нажатие (подсказки)
        data.from_pos + data.to_pos — второе нажатие (ход)
        """
        if batyr_captured_this_turn is None:
            batyr_captured_this_turn = []

        if data.position is not None and data.to_pos is None:
            return self.get_hints(
                cells=data.positions,
                current_color=data.mover_color,
                from_cell=data.position,
                batyr_captured_this_turn=batyr_captured_this_turn,
                chain_capture_cell=data.position_for_mandatory_capture
            )
        elif data.from_pos is not None and data.to_pos is not None:
            return self.process_move(
                cells=data.positions,
                current_color=data.mover_color,
                from_cell=data.from_pos,
                to_cell=data.to_pos,
                chain_capture_cell=data.position_for_mandatory_capture,
                batyr_captured_this_turn=batyr_captured_this_turn
            )
        else:
            return GameEventResult(message="Некорректные данные события")

    def validate_move(
        self,
        cells: dict,
        from_cell: int,
        to_cell: int,
        current_color: str,
        batyr_captured_this_turn: List[int] = None,
        check_mandatory: bool = True,
        chain_capture_cell: int = None
    ) -> Tuple[bool, str]:
        if batyr_captured_this_turn is None:
            batyr_captured_this_turn = []

        board = Board(cells)
        opponent = "черный" if current_color == "белый" else "белый"
        board = Board(cells)

        # 1. Есть ли фигура на from_cell
        piece = board.get_piece_object(from_cell)
        if not piece:
            return False, "Нет фигуры на выбранной позиции"

        # 2. Своего ли цвета?
        if piece.get_color() != current_color:
            return False, "Это не ваша фигура"

        # 3. Свободна ли клетка назначения?
        if cells.get(to_cell) is not None:
            return False, "Клетка занята"

        # 4. Проверка обязательных взятий
        if check_mandatory:
            mandatory_captures = self._get_all_mandatory_captures(board, current_color, batyr_captured_this_turn)
            if mandatory_captures:
                biy_can_capture_any = any(
                    board.get_piece_object(f) and board.get_piece_object(f).get_type() == "бий"
                    for f, _ in mandatory_captures
                )

                attacker_positions = {f for f, _ in mandatory_captures}

                if from_cell not in attacker_positions:
                    if biy_can_capture_any:
                        if piece.get_type() != "бий":
                            return False, "Бий обязан ходить!"
                    else:
                        return False, "Обязательное взятие!"
                else:
                    capture_targets = {t for f, t in mandatory_captures if f == from_cell}
                    if to_cell not in capture_targets:
                        if piece.get_type() == "бий":
                            pass
                        else:
                            return False, "Нужно бить!"

        # 5. Проверка через класс фигуры
        piece = board.get_piece_object(from_cell)
        if not piece:
            return False, "Ошибка определения фигуры"

        # 5a. Универсальная проверка: если это взятие (прыжок через клетку)
        if piece.get_type() in ["шатра", "бий"]:
            from game_engine.словари import shatra_and_biy_possible_captures
            possible_captures = shatra_and_biy_possible_captures.get(from_cell, {})
            if to_cell in possible_captures:
                enemy_cell = possible_captures[to_cell]
                enemy_piece = cells.get(enemy_cell)
                if not enemy_piece:
                    pass
                elif current_color in enemy_piece:
                    pass
                else:
                    pass

        # 5b. Для батыра: проверяем, что не бьём свою фигуру
        if piece.get_type() == "батыр":
            from game_engine.словари import batyr_moves_and_captures
            for direction in batyr_moves_and_captures.get(from_cell, []):
                if to_cell in direction:
                    for cell in direction:
                        if cell == to_cell:
                            break
                        cell_piece = cells.get(cell)
                        if cell_piece and current_color in cell_piece:
                            return False, "Своя фигура на пути"

        # Пробуем взятие
        if piece.can_capture(cells, from_cell, to_cell, batyr_captured_this_turn):
            return True, ""

        # Пробуем обычный ход
        if piece.can_move(cells, from_cell, to_cell):
            return True, ""

        return False, "Недопустимый ход"

    def execute_move(
        self,
        cells: dict,
        from_cell: int,
        to_cell: int,
        current_color: str,
        batyr_captured_this_turn: List[int] = None
    ) -> Tuple[dict, List[int], List[int]]:
        if batyr_captured_this_turn is None:
            batyr_captured_this_turn = []

        new_cells = copy.deepcopy(cells)
        board = Board(new_cells)
        captured_positions = []
        new_batyr_captures = copy.copy(batyr_captured_this_turn)

        piece = board.get_piece_object(from_cell)

        if piece and piece.can_capture(cells, from_cell, to_cell, batyr_captured_this_turn):
            enemy_cell = self._find_captured_enemy(cells, piece, from_cell, to_cell, batyr_captured_this_turn)
            board.move_piece(from_cell, to_cell)
            if enemy_cell:
                board.remove_piece(enemy_cell)
                captured_positions.append(enemy_cell)
                if piece.get_type() == "батыр":
                    new_batyr_captures.append(enemy_cell)
            return board.copy_cells(), captured_positions, new_batyr_captures
        else:
            board.move_piece(from_cell, to_cell)
            if piece and piece.get_type() == "батыр":
                new_batyr_captures.clear()
            return board.copy_cells(), captured_positions, new_batyr_captures

    def get_hints(
        self,
        cells: dict,
        current_color: str,
        from_cell: int,
        batyr_captured_this_turn: List[int] = None,
        chain_capture_cell: int = None
    ) -> GameEventResult:
        if batyr_captured_this_turn is None:
            batyr_captured_this_turn = []

        board = Board(cells)
        piece = board.get_piece_object(from_cell)
        if not piece or piece.get_color() != current_color:
            return GameEventResult(essential_positions=[], captured_pieces=batyr_captured_this_turn.copy())
        if not piece:
            return GameEventResult(essential_positions=[], captured_pieces=batyr_captured_this_turn.copy())

        # Если есть цепочка — показываем только взятия этой фигурой
        if chain_capture_cell and chain_capture_cell != 0:
            if from_cell != chain_capture_cell:
                return GameEventResult(essential_positions=[], captured_pieces=batyr_captured_this_turn.copy())
            allowed = []
            if piece.get_type() in ["шатра", "бий"]:
                from game_engine.словари import shatra_and_biy_possible_captures
                enemy_prefix = "чер" if current_color == "белый" else "бел"
                for to_cell, enemy_cell in shatra_and_biy_possible_captures.get(from_cell, {}).items():
                    enemy_piece = cells.get(enemy_cell)
                    target_free = cells.get(to_cell) is None
                    if enemy_piece and target_free and enemy_prefix in enemy_piece:
                        allowed.append(to_cell)
            return GameEventResult(
                essential_positions=allowed,
                captured_pieces=batyr_captured_this_turn.copy()
            )

        # Проверяем обязательные взятия
        mandatory_captures = self._get_all_mandatory_captures(board, current_color, batyr_captured_this_turn)
        mandatory_from = {f for f, _ in mandatory_captures}

        if from_cell in mandatory_from:
            if piece.get_type() == "бий":
                allowed = []
                for f, t in mandatory_captures:
                    if f == from_cell:
                        allowed.append(t)

                if not batyr_captured_this_turn:
                    from game_engine.словари import black_biy_possible_moves, white_biy_possible_moves
                    moves = black_biy_possible_moves if current_color == "черный" else white_biy_possible_moves
                    for target in moves.get(from_cell, []):
                        valid, _ = self.validate_move(
                            cells, from_cell, target, current_color,
                            batyr_captured_this_turn, check_mandatory=False
                        )
                        if valid:
                            allowed.append(target)
                return GameEventResult(
                    essential_positions=allowed,
                    captured_pieces=batyr_captured_this_turn.copy()
                )
            allowed = [t for f, t in mandatory_captures if f == from_cell]
            return GameEventResult(
                essential_positions=allowed,
                captured_pieces=batyr_captured_this_turn.copy()
            )

        if mandatory_captures:
            return GameEventResult(essential_positions=[], captured_pieces=batyr_captured_this_turn.copy())

        # Нет обязательных взятий — собираем все возможные ходы
        possible_moves = []
        piece_type = piece.get_type()

        if piece_type == "шатра":
            from game_engine.словари import black_shatra_possible_moves, white_shatra_possible_moves, shatra_and_biy_possible_captures
            moves = black_shatra_possible_moves if current_color == "черный" else white_shatra_possible_moves

            for target in moves.get(from_cell, []):
                valid, _ = self.validate_move(
                    cells, from_cell, target, current_color,
                    batyr_captured_this_turn, check_mandatory=False
                )
                if valid:
                    possible_moves.append(target)

            for target in shatra_and_biy_possible_captures.get(from_cell, {}):
                valid, _ = self.validate_move(
                    cells, from_cell, target, current_color,
                    batyr_captured_this_turn, check_mandatory=False
                )
                if valid:
                    possible_moves.append(target)

        elif piece_type == "бий":
            from game_engine.словари import black_biy_possible_moves, white_biy_possible_moves, shatra_and_biy_possible_captures
            moves = black_biy_possible_moves if current_color == "черный" else white_biy_possible_moves

            for target in moves.get(from_cell, []):
                valid, _ = self.validate_move(
                    cells, from_cell, target, current_color,
                    batyr_captured_this_turn, check_mandatory=False
                )
                if valid:
                    possible_moves.append(target)

            for target in shatra_and_biy_possible_captures.get(from_cell, {}):
                valid, _ = self.validate_move(
                    cells, from_cell, target, current_color,
                    batyr_captured_this_turn, check_mandatory=False
                )
                if valid:
                    possible_moves.append(target)

        elif piece_type == "батыр":
            from game_engine.словари import batyr_moves_and_captures
            for direction in batyr_moves_and_captures.get(from_cell, []):
                for target in direction:
                    valid, _ = self.validate_move(
                        cells, from_cell, target, current_color,
                        batyr_captured_this_turn, check_mandatory=False
                    )
                    if valid:
                        possible_moves.append(target)

        return GameEventResult(
            essential_positions=possible_moves,
            captured_pieces=batyr_captured_this_turn.copy()
        )

    def process_move(
        self,
        cells: dict,
        current_color: str,
        from_cell: int,
        to_cell: int,
        chain_capture_cell: int = None,
        batyr_captured_this_turn: List[int] = None
    ) -> GameEventResult:
        if batyr_captured_this_turn is None:
            batyr_captured_this_turn = []

        current_batyr_captures = copy.copy(batyr_captured_this_turn)
        board_copy = copy.deepcopy(cells)

        # 1. Проверка конца игры
        board = Board(board_copy)
        is_over, winner = self._is_game_over(board)
        if is_over:
            return GameEventResult(
                message=f"Игра окончена: {winner}",
                movers_color=None,
                updated_positions=cells,
                game_over=True,
                winner=winner
            )

        # 2. Обработка передачи хода (бий нажал "передать ход")
        if chain_capture_cell == 0:
            is_over, winner = self._is_game_over(Board(board_copy))
            return self._finish_move(
                positions=board_copy,
                mover_color=current_color,
                message="Ход передан.",
                history=True,
                clear_pending=True,
                game_over=is_over,
                winner=winner
            )

        # 3. Проверка обязательного взятия той же фигурой
        if chain_capture_cell is not None and chain_capture_cell != 0:
            if from_cell != chain_capture_cell:
                return GameEventResult(
                    message="Продолжайте взятие той же фигурой!",
                    movers_color=current_color,
                    updated_positions=cells
                )
            piece = Board(board_copy).get_piece_object(from_cell)
            if piece and piece.get_type() in ["шатра", "бий"]:
                from game_engine.словари import shatra_and_biy_possible_captures
                possible_captures = shatra_and_biy_possible_captures.get(from_cell, {})
                if to_cell not in possible_captures:
                    return GameEventResult(
                        message="Нужно бить!",
                        movers_color=current_color,
                        updated_positions=cells
                    )
                enemy_cell = possible_captures[to_cell]
                enemy_piece = board_copy.get(enemy_cell)
                enemy_prefix = "чер" if current_color == "белый" else "бел"
                if not enemy_piece or enemy_prefix not in enemy_piece:
                    return GameEventResult(
                        message="Нет фигуры для взятия",
                        movers_color=current_color,
                        updated_positions=cells
                    )
                if board_copy.get(to_cell) is not None:
                    return GameEventResult(
                        message="Клетка занята",
                        movers_color=current_color,
                        updated_positions=cells
                    )

                # Выполняем взятие вручную
                new_cells = copy.deepcopy(cells)
                board = Board(new_cells)
                board.move_piece(from_cell, to_cell)
                board.remove_piece(enemy_cell)
                captured_positions = [enemy_cell]
                new_batyr_captures = copy.copy(current_batyr_captures)
                piece_kind = "бий" if piece.get_type() == "бий" else "шатра"

                next_board = board
                is_over, winner = self._is_game_over(next_board)
                if is_over:
                    return GameEventResult(
                        message=f"Игра окончена: {winner}",
                        movers_color=None,
                        updated_positions=board.copy_cells(),
                        game_over=True,
                        winner=winner,
                        captured_positions=captured_positions
                    )

                # Проверяем, может ли фигура продолжить
                can_continue_chain = False
                board_dict = board.copy_cells()
                for to_cell_next, enemy_cell_next in shatra_and_biy_possible_captures.get(to_cell, {}).items():
                    enemy_name = board_dict.get(enemy_cell_next)
                    target_free = board_dict.get(to_cell_next) is None
                    if enemy_name and target_free:
                        enemy_prefix = "бел" if current_color == "черный" else "чер"
                        if enemy_prefix in enemy_name:
                            can_continue_chain = True
                            break

                can_pass_turn = piece_kind == "бий"

                if can_continue_chain:
                    return GameEventResult(
                        message="Продолжайте взятие!",
                        movers_color=current_color,
                        updated_positions=board.copy_cells(),
                        captured_positions=captured_positions,
                        opportunity_pass_the_move=can_pass_turn,
                        position_for_mandatory_capture=to_cell,
                        captured_pieces=new_batyr_captures
                    )

                next_player = "черный" if current_color == "белый" else "белый"
                return self._finish_move(
                    positions=board.copy_cells(),
                    mover_color=current_color,
                    message=f"Теперь ходит {next_player}",
                    history=True,
                    clear_pending=True,
                    game_over=False,
                    winner=None,
                    captured_positions=captured_positions,
                    opportunity_pass=can_pass_turn
                )

        # 4. Валидация хода (если не было цепочки)
        if chain_capture_cell is None or chain_capture_cell == 0:
            valid, error_msg = self.validate_move(
                board_copy, from_cell, to_cell, current_color, current_batyr_captures
            )
            if not valid:
                return GameEventResult(
                    message=error_msg,
                    movers_color=current_color,
                    updated_positions=cells
                )

        # 5. Выполнение хода
        new_cells, captured_positions, new_batyr_captures = self.execute_move(
            board_copy, from_cell, to_cell, current_color, current_batyr_captures
        )

        piece = Board(board_copy).get_piece_object(from_cell)
        piece_kind = piece.get_type() if piece else ""

        # 5b. Превращение шатры в батыра при достижении края доски.
        # Если шатра дошла до края (после хода или после взятия), она превращается в батыра,
        # после чего ход завершается — цепочка не продолжается.
        if piece_kind == "шатра":
            if _promote_shatra(new_cells, to_cell, current_color):
                piece_kind = "батыр"
                return self._finish_move(
                    positions=new_cells,
                    mover_color=current_color,
                    message=f"{current_color.capitalize()} шатра стала батыром!",
                    history=True,
                    clear_pending=True,
                    game_over=False,
                    winner=None,
                    captured_positions=captured_positions
                )

        # 5a. Проверка конца игры (съели бия?)
        next_board = Board(new_cells)
        is_over, winner = self._is_game_over(next_board)
        if is_over:
            return GameEventResult(
                message=f"Игра окончена: {winner}",
                movers_color=None,
                updated_positions=new_cells,
                game_over=True,
                winner=winner,
                captured_positions=captured_positions
            )

        # 6. Определяем, нужно ли продолжать взятие
        next_mandatory_captures = self._get_all_mandatory_captures(next_board, current_color, new_batyr_captures)
        has_captured = len(captured_positions) > 0

        can_continue_chain = False
        if has_captured:
            if piece_kind in ["шатра", "бий"]:
                from game_engine.словари import shatra_and_biy_possible_captures
                for to_cell_next, enemy_cell_next in shatra_and_biy_possible_captures.get(to_cell, {}).items():
                    enemy_piece = new_cells.get(enemy_cell_next)
                    target_free = new_cells.get(to_cell_next) is None
                    if enemy_piece and target_free:
                        enemy_prefix = "бел" if current_color == "черный" else "чер"
                        if enemy_prefix in enemy_piece:
                            can_continue_chain = True
                            break
            else:
                can_continue_chain = any(f == to_cell for f, _ in next_mandatory_captures)

        can_pass_turn = False
        if piece_kind == "бий" and has_captured:
            can_pass_turn = True

        if can_continue_chain:
            return GameEventResult(
                message="Продолжайте взятие!",
                movers_color=current_color,
                updated_positions=new_cells,
                captured_positions=captured_positions,
                opportunity_pass_the_move=can_pass_turn,
                position_for_mandatory_capture=to_cell,
                captured_pieces=new_batyr_captures
            )

        # Если бий взял, больше некого бить — даём кнопку передать ход
        if piece_kind == "бий" and has_captured:
            return GameEventResult(
                message="Продолжайте взятие или передайте ход!",
                movers_color=current_color,
                updated_positions=new_cells,
                captured_positions=captured_positions,
                opportunity_pass_the_move=True,
                position_for_mandatory_capture=to_cell,
                captured_pieces=new_batyr_captures
            )

        # 8. Ход завершён — передаём ход
        next_player = "черный" if current_color == "белый" else "белый"
        is_over, winner = self._is_game_over(next_board)

        chain_capture_pos = None
        if next_player and not is_over:
            if self.has_mandatory_from_position(new_cells, next_player):
                chain_capture_pos = to_cell

        return self._finish_move(
            positions=new_cells,
            mover_color=current_color,
            message=f"Теперь ходит {next_player}",
            history=True,
            clear_pending=True,
            game_over=is_over,
            winner=winner,
            captured_positions=captured_positions,
            opportunity_pass=can_pass_turn,
            mandatory_pos=chain_capture_pos
        )

    def _finish_move(
        self,
        positions: dict,
        mover_color: str,
        message: str = "",
        history: bool = False,
        clear_pending: bool = False,
        game_over: bool = False,
        winner: str = None,
        captured_positions: List[int] = None,
        opportunity_pass: bool = False,
        mandatory_pos: int = None
    ) -> GameEventResult:
        next_mover = "черный" if mover_color == "белый" else "белый"

        if history:
            self._add_to_history(positions)

        return GameEventResult(
            message=message,
            movers_color=next_mover,
            updated_positions=positions,
            captured_positions=captured_positions or [],
            game_over=game_over,
            winner=winner,
            opportunity_pass_the_move=opportunity_pass,
            position_for_mandatory_capture=mandatory_pos
        )

    def has_mandatory_from_position(self, cells: dict, color: str, pos: int = None) -> bool:
        board = Board(cells)
        mandatory = self._get_all_mandatory_captures(board, color)
        if pos is not None:
            return any(f == pos for f, _ in mandatory)
        return len(mandatory) > 0

    def _is_game_over(self, board: Board) -> Tuple[bool, Optional[str]]:
        biy_count = 0
        last_biy_color = None
        for pos, piece_name in board.cells.items():
            if piece_name and "бий" in piece_name:
                biy_count += 1
                last_biy_color = "белый" if "бел" in piece_name else "черный"
        if biy_count == 1:
            return True, f"{last_biy_color.capitalize()} бий победил!"
        pos_key = str(sorted(board.cells.items()))
        if position_history.get(pos_key, 0) >= 3:
            return True, "Ничья! Позиция повторилась 3 раза."
        return False, None

    def _get_all_mandatory_captures(
        self,
        board: Board,
        color: str,
        batyr_captured_this_turn: List[int] = None
    ) -> List[Tuple[int, int]]:
        if batyr_captured_this_turn is None:
            batyr_captured_this_turn = []

        mandatory = []
        opponent = "черный" if color == "белый" else "белый"
        opponent_prefix = "чер" if color == "белый" else "бел"

        for pos, piece in board.get_all_pieces():
            if piece.get_color() != color:
                continue

            piece_type = piece.get_type()

            if piece_type in ["шатра", "бий"]:
                from game_engine.словари import shatra_and_biy_possible_captures
                possible_captures = shatra_and_biy_possible_captures.get(pos, {})
                for to_cell, enemy_cell in possible_captures.items():
                    enemy_piece = board.cells.get(enemy_cell)
                    if (enemy_piece and opponent_prefix in enemy_piece and
                            board.cells.get(to_cell) is None):
                        if piece._can_enter_fortress(board.cells, pos, to_cell):
                            mandatory.append((pos, to_cell))

            elif piece_type == "батыр":
                from game_engine.словари import batyr_moves_and_captures
                for direction in batyr_moves_and_captures.get(pos, []):
                    enemy_found = False
                    for idx, cell in enumerate(direction[:-1]):
                        next_cell = direction[idx + 1]
                        cell_piece = board.cells.get(cell)

                        if cell in batyr_captured_this_turn:
                            continue

                        if cell_piece is None:
                            if enemy_found:
                                mandatory.append((pos, cell))
                            continue

                        cell_prefix = "бел" if "бел" in (cell_piece or "") else ("чер" if "чер" in (cell_piece or "") else "")
                        if cell_prefix and color.startswith(cell_prefix):
                            break

                        if opponent_prefix in (cell_piece or "") and board.cells.get(next_cell) is None:
                            if cell not in batyr_captured_this_turn:
                                enemy_found = True
                                mandatory.append((pos, next_cell))

        return mandatory

    def _find_captured_enemy(
        self,
        cells: dict,
        piece,
        from_cell: int,
        to_cell: int,
        batyr_captured_this_turn: List[int] = None
    ) -> Optional[int]:
        if batyr_captured_this_turn is None:
            batyr_captured_this_turn = []

        if piece.get_type() in ["шатра", "бий"]:
            from game_engine.словари import shatra_and_biy_possible_captures
            return shatra_and_biy_possible_captures.get(from_cell, {}).get(to_cell)

        if piece.get_type() == "батыр":
            if batyr_captured_this_turn:
                return batyr_captured_this_turn[-1]

            from game_engine.словари import batyr_moves_and_captures
            for direction in batyr_moves_and_captures.get(from_cell, []):
                for pos in direction:
                    if pos == to_cell:
                        return None
                    cell = cells.get(pos)
                    if cell and "белый" != cell and "черный" != cell:
                        if cells.get(pos) and piece.get_color() not in cells[pos]:
                            return pos
                    if cell is not None:
                        break

        return None

    def _add_to_history(self, positions: dict):
        pos_key = str(sorted(positions.items()))
        position_history[pos_key] = position_history.get(pos_key, 0) + 1

    def reset(self):
        position_history.clear()