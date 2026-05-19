from game_engine.models import GameEvent, GameEventResult
from game_engine.board import Board
from typing import List, Tuple, Optional
import copy

history_of_positions: dict[str, int] = {}


class GameLogic:
    def __init__(self):
        pass  # Состояние теперь передаётся через параметры

    def handle_event(self, data: GameEvent, pending_batyr_captures: List[int] = None) -> GameEventResult:
        """
        Единая точка входа.
        data.position — первое нажатие (подсказки)
        data.from_pos + data.to_pos — второе нажатие (ход)
        """
        if pending_batyr_captures is None:
            pending_batyr_captures = []
            
        if data.position is not None and data.to_pos is None:
            return self.get_hints(
                positions=data.positions,
                mover_color=data.mover_color,
                from_pos=data.position,
                pending_batyr_captures=pending_batyr_captures,
                position_for_mandatory_capture=data.position_for_mandatory_capture
            )
        elif data.from_pos is not None and data.to_pos is not None:
            return self.process_move(
                positions=data.positions,
                mover_color=data.mover_color,
                from_pos=data.from_pos,
                to_pos=data.to_pos,
                position_for_mandatory_capture=data.position_for_mandatory_capture,
                pending_batyr_captures=pending_batyr_captures
            )
        else:
            return GameEventResult(message="Некорректные данные события")

    def validate_move(
        self,
        positions: dict,
        from_pos: int,
        to_pos: int,
        mover_color: str,
        pending_batyr_captures: List[int] = None,
        check_mandatory: bool = True,
        position_for_mandatory_capture: int = None
    ) -> Tuple[bool, str]:
        """
        Проверяет, возможен ли ход по правилам.
        НЕ меняет состояние.
        Возвращает (True, "") или (False, "причина").
        """
        if pending_batyr_captures is None:
            pending_batyr_captures = []
            
        board = Board(positions)
        opposite = "черный" if mover_color == "белый" else "белый"
        
        board = Board(positions)
        
        # 1. Есть ли фигура на from_pos
        piece_obj = board.get_piece_object(from_pos)
        if not piece_obj:
            return False, "Нет фигуры на выбранной позиции"
        
        # 2. Своего ли цвета?
        if piece_obj.get_color() != mover_color:
            return False, "Это не ваша фигура"
        
        # 3. Свободна ли клетка назначения?
        if positions.get(to_pos) is not None:
            return False, "Клетка занята"
        
        # 4. Проверка обязательных взятий
        if check_mandatory:
            mandatory = self._get_all_mandatory_captures(board, mover_color, pending_batyr_captures)
            if mandatory:
                # Проверяем, есть ли бий среди фигур, которые могут бить
                biy_can_capture = any(
                    board.get_piece_object(f) and board.get_piece_object(f).get_type() == "бий"
                    for f, _ in mandatory
                )
                
                from_positions = {f for f, _ in mandatory}
                
                if from_pos not in from_positions:
                    # Фигура не может бить
                    if biy_can_capture:
                        # Бий может бить — можно ходить только бием
                        if piece_obj.get_type() != "бий":
                            return False, "Бий обязан ходить!"
                        # Бий может сделать любой ход (бить или нет)
                    else:
                        return False, "Обязательное взятие!"
                else:
                    # Фигура может бить
                    allowed_targets = {t for f, t in mandatory if f == from_pos}
                    if to_pos not in allowed_targets:
                        # Если это бий — может сделать ход без взятия
                        if piece_obj.get_type() == "бий":
                            pass  # бий может не брать, просто ходить
                        else:
                            return False, "Нужно бить!"
        
        # 5. Проверка через класс фигуры
        piece_obj = board.get_piece_object(from_pos)
        if not piece_obj:
            return False, "Ошибка определения фигуры"
        
        # 5a. Универсальная проверка: если это взятие (прыжок через клетку),
        # убеждаемся, что перепрыгиваем через врага, а не через свою фигуру.
        # Если промежуточная клетка пуста или там своя фигура — это не взятие,
        # может быть обычный ход (проверка can_move решит).
        if piece_obj.get_type() in ["шатра", "бий"]:
            from game_engine.словари import shatra_and_biy_possible_captures
            captures_map = shatra_and_biy_possible_captures.get(from_pos, {})
            if to_pos in captures_map:
                enemy_pos = captures_map[to_pos]
                enemy_name = positions.get(enemy_pos)
                if not enemy_name:
                    pass  # Нет фигуры на промежуточной — обычный ход
                elif mover_color in enemy_name:
                    pass  # Своя фигура на промежуточной — не взятие, может быть ход
                else:
                    # Враг на промежуточной — это взятие, can_capture решит
                    pass
        
        # 5b. Для батыра: проверяем, что не бьём свою фигуру
        if piece_obj.get_type() == "батыр":
            from game_engine.словари import batyr_moves_and_captures
            for direction in batyr_moves_and_captures.get(from_pos, []):
                if to_pos in direction:
                    for pos in direction:
                        if pos == to_pos:
                            break
                        cell = positions.get(pos)
                        if cell and mover_color in cell:
                            # Своя фигура на пути — ход невозможен
                            return False, "Своя фигура на пути"
        
        # Пробуем взятие
        if piece_obj.can_capture(positions, from_pos, to_pos, pending_batyr_captures):
            return True, ""
        
        # Пробуем обычный ход
        if piece_obj.can_move(positions, from_pos, to_pos):
            return True, ""
        
        return False, "Недопустимый ход"

    def execute_move(
        self,
        positions: dict,
        from_pos: int,
        to_pos: int,
        mover_color: str,
        pending_batyr_captures: List[int] = None
    ) -> Tuple[dict, List[int], List[int]]:
        """
        Выполняет ход на доске.
        Возвращает (новая_доска, список_съеденных_позиций, обновлённый_pending)
        НЕ проверяет правила (перед вызовом нужен validate_move).
        """
        if pending_batyr_captures is None:
            pending_batyr_captures = []
        
        new_positions = copy.deepcopy(positions)
        board = Board(new_positions)
        captured_list = []
        new_pending = copy.copy(pending_batyr_captures)
        
        piece_obj = board.get_piece_object(from_pos)
        
        # Проверяем, это взятие?
        if piece_obj and piece_obj.can_capture(positions, from_pos, to_pos, pending_batyr_captures):
            # Находим врага
            enemy_pos = self._find_captured_enemy(positions, piece_obj, from_pos, to_pos, pending_batyr_captures)
            board.move_piece(from_pos, to_pos)
            if enemy_pos:
                board.remove_piece(enemy_pos)
                captured_list.append(enemy_pos)
                if piece_obj.get_type() == "батыр":
                    new_pending.append(enemy_pos)
            return board.copy_positions(), captured_list, new_pending
        else:
            # Обычный ход
            board.move_piece(from_pos, to_pos)
            if piece_obj and piece_obj.get_type() == "батыр":
                new_pending.clear()
            return board.copy_positions(), captured_list, new_pending

    def get_hints(
        self,
        positions: dict,
        mover_color: str,
        from_pos: int,
        pending_batyr_captures: List[int] = None,
        position_for_mandatory_capture: int = None
    ) -> GameEventResult:
        """
        Возвращает все возможные ходы из позиции.
        """
        if pending_batyr_captures is None:
            pending_batyr_captures = []
        
        board = Board(positions)
        piece_obj = board.get_piece_object(from_pos)
        if not piece_obj or piece_obj.get_color() != mover_color:
            return GameEventResult(essential_positions=[], captured_pieces=pending_batyr_captures.copy())
        if not piece_obj:
            return GameEventResult(essential_positions=[], captured_pieces=pending_batyr_captures.copy())
        
        # Если есть position_for_mandatory_capture — показываем только взятия этой фигурой
        if position_for_mandatory_capture and position_for_mandatory_capture != 0:
            if from_pos != position_for_mandatory_capture:
                return GameEventResult(essential_positions=[], captured_pieces=pending_batyr_captures.copy())
            # Показываем только взятия
            allowed = []
            if piece_obj.get_type() in ["шатра", "бий"]:
                from game_engine.словари import shatra_and_biy_possible_captures
                opp_prefix = "чер" if mover_color == "белый" else "бел"
                for to_cell, enemy_cell in shatra_and_biy_possible_captures.get(from_pos, {}).items():
                    enemy_name = positions.get(enemy_cell)
                    target_free = positions.get(to_cell) is None
                    if enemy_name and target_free and opp_prefix in enemy_name:
                        allowed.append(to_cell)
            return GameEventResult(
                essential_positions=allowed,
                captured_pieces=pending_batyr_captures.copy()
            )
        
        # Проверяем обязательные взятия
        mandatory = self._get_all_mandatory_captures(board, mover_color, pending_batyr_captures)
        mandatory_from = {f for f, _ in mandatory}
        
        if from_pos in mandatory_from:
            # Если это бий — может и бить, и ходить
            if piece_obj.get_type() == "бий":
                allowed = []
                # Все взятия бием
                for f, t in mandatory:
                    if f == from_pos:
                        allowed.append(t)
                
                # Если бий взял (есть pending_batyr_captures) — показывает только взятия для продолжения
                # Если бий может взять в начале хода — показывает и взятия, и обычные ходы
                if not pending_batyr_captures:
                    from game_engine.словари import black_biy_possible_moves, white_biy_possible_moves
                    moves_dict = black_biy_possible_moves if mover_color == "черный" else white_biy_possible_moves
                    for target in moves_dict.get(from_pos, []):
                        valid, _ = self.validate_move(
                            positions, from_pos, target, mover_color,
                            pending_batyr_captures, check_mandatory=False
                        )
                        if valid:
                            allowed.append(target)
                return GameEventResult(
                    essential_positions=allowed,
                    captured_pieces=pending_batyr_captures.copy()
                )
            # Иначе фигура обязана бить — только цели для взятия
            allowed = [t for f, t in mandatory if f == from_pos]
            return GameEventResult(
                essential_positions=allowed,
                captured_pieces=pending_batyr_captures.copy()
            )
        
        # Если есть обязательные взятия другими фигурами — эта фигура не может ходить
        if mandatory:
            return GameEventResult(essential_positions=[], captured_pieces=pending_batyr_captures.copy())
        
        # Нет обязательных взятий — собираем все возможные ходы
        possible_moves = []
        
        piece_type = piece_obj.get_type()
        
        if piece_type == "шатра":
            from game_engine.словари import black_shatra_possible_moves, white_shatra_possible_moves, shatra_and_biy_possible_captures
            moves_dict = black_shatra_possible_moves if mover_color == "черный" else white_shatra_possible_moves
            
            # Обычные ходы
            for target in moves_dict.get(from_pos, []):
                valid, _ = self.validate_move(
                    positions, from_pos, target, mover_color,
                    pending_batyr_captures, check_mandatory=False
                )
                if valid:
                    possible_moves.append(target)
            
            # Взятия (если есть возможность)
            captures_map = shatra_and_biy_possible_captures.get(from_pos, {})
            for target, enemy_pos in captures_map.items():
                valid, _ = self.validate_move(
                    positions, from_pos, target, mover_color,
                    pending_batyr_captures, check_mandatory=False
                )
                if valid:
                    possible_moves.append(target)
                    
        elif piece_type == "бий":
            from game_engine.словари import black_biy_possible_moves, white_biy_possible_moves, shatra_and_biy_possible_captures
            moves_dict = black_biy_possible_moves if mover_color == "черный" else white_biy_possible_moves
            
            # Обычные ходы
            for target in moves_dict.get(from_pos, []):
                valid, _ = self.validate_move(
                    positions, from_pos, target, mover_color,
                    pending_batyr_captures, check_mandatory=False
                )
                if valid:
                    possible_moves.append(target)
            
            # Взятия
            captures_map = shatra_and_biy_possible_captures.get(from_pos, {})
            for target, enemy_pos in captures_map.items():
                valid, _ = self.validate_move(
                    positions, from_pos, target, mover_color,
                    pending_batyr_captures, check_mandatory=False
                )
                if valid:
                    possible_moves.append(target)
                    
        elif piece_type == "батыр":
            from game_engine.словари import batyr_moves_and_captures
            for direction in batyr_moves_and_captures.get(from_pos, []):
                for target in direction:
                    valid, _ = self.validate_move(
                        positions, from_pos, target, mover_color,
                        pending_batyr_captures, check_mandatory=False
                    )
                    if valid:
                        possible_moves.append(target)
        
        return GameEventResult(
            essential_positions=possible_moves,
            captured_pieces=pending_batyr_captures.copy()
        )

    def process_move(
        self,
        positions: dict,
        mover_color: str,
        from_pos: int,
        to_pos: int,
        position_for_mandatory_capture: int = None,
        pending_batyr_captures: List[int] = None
    ) -> GameEventResult:
        """
        Обрабатывает ход: проверка + выполнение + анализ результата.
        """
        if pending_batyr_captures is None:
            pending_batyr_captures = []
        
        # Копируем pending, чтобы не менять оригинал до успеха
        current_pending = copy.copy(pending_batyr_captures)
        working_positions = copy.deepcopy(positions)
        
        # 1. Проверка конца игры
        board = Board(working_positions)
        is_over, winner = self._is_game_over(board)
        if is_over:
            return GameEventResult(
                message=f"Игра окончена: {winner}",
                movers_color=None,
                updated_positions=positions,
                game_over=True,
                winner=winner
            )
        
        # 2. Обработка передачи хода (бий нажал "передать ход")
        if position_for_mandatory_capture == 0:
            # Создаём Board для проверки конца игры
            is_over, winner = self._is_game_over(Board(working_positions))
            return self._finish_move(
                positions=working_positions,
                mover_color=mover_color,
                message="Ход передан.",
                history=True,
                clear_pending=True,
                game_over=is_over,
                winner=winner
            )
        
        # 3. Проверка обязательного взятия той же фигурой
        if position_for_mandatory_capture is not None and position_for_mandatory_capture != 0:
            if from_pos != position_for_mandatory_capture:
                return GameEventResult(
                    message="Продолжайте взятие той же фигурой!",
                    movers_color=mover_color,
                    updated_positions=positions
                )
            # Если это продолжение после взятия — выполняем сразу, минуя validate_move
            piece = Board(working_positions).get_piece_object(from_pos)
            if piece and piece.get_type() in ["шатра", "бий"]:
                from game_engine.словари import shatra_and_biy_possible_captures
                captures = shatra_and_biy_possible_captures.get(from_pos, {})
                if to_pos not in captures:
                    return GameEventResult(
                        message="Нужно бить!",
                        movers_color=mover_color,
                        updated_positions=positions
                    )
                enemy_pos = captures[to_pos]
                enemy_name = working_positions.get(enemy_pos)
                opp_prefix = "чер" if mover_color == "белый" else "бел"
                if not enemy_name or opp_prefix not in enemy_name:
                    return GameEventResult(
                        message="Нет фигуры для взятия",
                        movers_color=mover_color,
                        updated_positions=positions
                    )
                if working_positions.get(to_pos) is not None:
                    return GameEventResult(
                        message="Клетка занята",
                        movers_color=mover_color,
                        updated_positions=positions
                    )
                # Всё ок — это взятие! Выполняем его вручную
                new_positions = copy.deepcopy(positions)
                board = Board(new_positions)
                enemy_pos = captures[to_pos]
                board.move_piece(from_pos, to_pos)
                board.remove_piece(enemy_pos)
                captured_list = [enemy_pos]
                new_pending = copy.copy(current_pending)
                
                # Определяем тип фигуры для продолжения
                piece_type = "бий" if piece and piece.get_type() == "бий" else "шатра"
                
                # Проверка конца игры
                next_board = board
                is_over, winner = self._is_game_over(next_board)
                if is_over:
                    return GameEventResult(
                        message=f"Игра окончена: {winner}",
                        movers_color=None,
                        updated_positions=board.copy_positions(),
                        game_over=True,
                        winner=winner,
                        captured_positions=captured_list
                    )
                
                # Проверяем, может ли фигура продолжить взятие
                can_continue_capture = False
                new_board_dict = board.copy_positions()
                for to_cell, enemy_cell in shatra_and_biy_possible_captures.get(to_pos, {}).items():
                    enemy_name = new_board_dict.get(enemy_cell)
                    target_free = new_board_dict.get(to_cell) is None
                    if enemy_name and target_free:
                        opp_prefix = "бел" if mover_color == "черный" else "чер"
                        if opp_prefix in enemy_name:
                            can_continue_capture = True
                            break
                
                opportunity_pass = piece_type == "бий"
                
                if can_continue_capture:
                    return GameEventResult(
                        message="Продолжайте взятие!",
                        movers_color=mover_color,
                        updated_positions=board.copy_positions(),
                        captured_positions=captured_list,
                        opportunity_pass_the_move=opportunity_pass,
                        position_for_mandatory_capture=to_pos,
                        captured_pieces=new_pending
                    )
                
                # Ход завершён
                next_mover = "черный" if mover_color == "белый" else "белый"
                return self._finish_move(
                    positions=board.copy_positions(),
                    mover_color=mover_color,
                    message=f"Теперь ходит {next_mover}",
                    history=True,
                    clear_pending=True,
                    game_over=False,
                    winner=None,
                    captured_positions=captured_list,
                    opportunity_pass=opportunity_pass
                )
        
        # 4. Валидация хода (если не было position_for_mandatory_capture)
        if position_for_mandatory_capture is None or position_for_mandatory_capture == 0:
            valid, error_msg = self.validate_move(
                working_positions, from_pos, to_pos, mover_color, current_pending
            )
            if not valid:
                return GameEventResult(
                    message=error_msg,
                    movers_color=mover_color,
                    updated_positions=positions
                )
        
        # 5. Выполнение хода
        new_positions, captured_list, new_pending = self.execute_move(
            working_positions, from_pos, to_pos, mover_color, current_pending
        )
        
        # Определяем тип фигуры
        piece_obj = Board(working_positions).get_piece_object(from_pos)
        piece_type = piece_obj.get_type() if piece_obj else ""
        
        # 5a. Проверка конца игры после выполнения хода (съели бия?)
        next_board = Board(new_positions)
        is_over, winner = self._is_game_over(next_board)
        if is_over:
            return GameEventResult(
                message=f"Игра окончена: {winner}",
                movers_color=None,
                updated_positions=new_positions,
                game_over=True,
                winner=winner,
                captured_positions=captured_list
            )
        
        # 6. Определяем, нужно ли продолжать взятие
        next_board = Board(new_positions)
        next_mandatory = self._get_all_mandatory_captures(next_board, mover_color, new_pending)
        was_capture = len(captured_list) > 0
        
        # Проверяем, может ли фигура продолжить взятие
        can_continue_capture = False
        if was_capture:
            # Для шатры и бия: проверяем взятия через словарь
            if piece_type in ["шатра", "бий"]:
                from game_engine.словари import shatra_and_biy_possible_captures
                for to_cell, enemy_cell in shatra_and_biy_possible_captures.get(to_pos, {}).items():
                    enemy_name = new_positions.get(enemy_cell)
                    target_free = new_positions.get(to_cell) is None
                    if enemy_name and target_free:
                        # Проверяем, что это враг, а не своя фигура
                        opp_prefix = "бел" if mover_color == "черный" else "чер"
                        if opp_prefix in enemy_name:
                            can_continue_capture = True
                            break
            else:
                # Для батыра — используем стандартную проверку
                can_continue_capture = any(f == to_pos for f, _ in next_mandatory)
        
        opportunity_pass = False
        if piece_type == "бий" and captured_list:
            opportunity_pass = True
        
        # 7. Если нужно продолжать взятие
        if can_continue_capture:
            return GameEventResult(
                message="Продолжайте взятие!",
                movers_color=mover_color,
                updated_positions=new_positions,
                captured_positions=captured_list,
                opportunity_pass_the_move=opportunity_pass,
                position_for_mandatory_capture=to_pos,
                captured_pieces=new_pending
            )
        
        # Даже если не можем продолжить, но был захват бием — устанавливаем position_for_mandatory_capture чтобы показать возможность передачи хода
        # (бий взял, больше бить некого — даём кнопку передать ход)
        if piece_type == "бий" and was_capture:
            return GameEventResult(
                message="Продолжайте взятие или передайте ход!",
                movers_color=mover_color,
                updated_positions=new_positions,
                captured_positions=captured_list,
                opportunity_pass_the_move=True,
                position_for_mandatory_capture=to_pos,
                captured_pieces=new_pending
            )
        
        # 8. Ход завершён — передаём ход
        next_mover = "черный" if mover_color == "белый" else "белый"
        
        # Проверка конца игры на новой доске
        is_over, winner = self._is_game_over(next_board)
        
        # Проверяем, есть ли у следующего игрока обязательное взятие с этой позиции
        mandatory_pos = None
        if next_mover and not is_over:
            if self.has_mandatory_from_position(new_positions, next_mover):
                mandatory_pos = to_pos
        
        return self._finish_move(
            positions=new_positions,
            mover_color=mover_color,
            message=f"Теперь ходит {next_mover}",
            history=True,
            clear_pending=True,
            game_over=is_over,
            winner=winner,
            captured_positions=captured_list,
            opportunity_pass=opportunity_pass,
            mandatory_pos=mandatory_pos
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
        """Вспомогательный метод для формирования результата."""
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

    def has_mandatory_from_position(self, positions: dict, color: str, pos: int = None) -> bool:
        """
        Проверяет, есть ли у игрока обязательные взятия.
        Если pos указан — только с этой позиции.
        """
        board = Board(positions)
        mandatory = self._get_all_mandatory_captures(board, color)
        if pos is not None:
            return any(f == pos for f, _ in mandatory)
        return len(mandatory) > 0

    def _is_game_over(self, board: Board) -> Tuple[bool, Optional[str]]:
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

    def _get_all_mandatory_captures(
        self,
        board: Board,
        color: str,
        pending_batyr_captures: List[int] = None
    ) -> List[Tuple[int, int]]:
        """
        Собирает все обязательные взятия для цвета.
        Учитывается pending_batyr_captures для цепочек.
        """
        if pending_batyr_captures is None:
            pending_batyr_captures = []
            
        mandatory = []
        opposite = "черный" if color == "белый" else "белый"
        opposite_prefix = "чер" if color == "белый" else "бел"
        
        for pos, piece_obj in board.get_all_pieces():
            if piece_obj.get_color() != color:
                continue
                
            piece_type = piece_obj.get_type()
            
            if piece_type in ["шатра", "бий"]:
                from game_engine.словари import shatra_and_biy_possible_captures
                captures_map = shatra_and_biy_possible_captures.get(pos, {})
                for to_pos, enemy_pos in captures_map.items():
                    enemy_name = board.positions.get(enemy_pos)
                    if (enemy_name and opposite_prefix in enemy_name and 
                        board.positions.get(to_pos) is None):
                        # Проверка крепости для шатры (нельзя бить в свою крепость)
                        piece = piece_obj
                        if piece._can_enter_fortress(board.positions, pos, to_pos):
                            mandatory.append((pos, to_pos))
                            
            elif piece_type == "батыр":
                from game_engine.словари import batyr_moves_and_captures
                for direction in batyr_moves_and_captures.get(pos, []):
                    enemy_found = False
                    for idx, cell in enumerate(direction[:-1]):
                        next_cell = direction[idx + 1]
                        cell_piece = board.positions.get(cell)
                        
                        # Пропускаем уже съеденных в этом ходу (pending)
                        if cell in pending_batyr_captures:
                            continue
                            
                        if cell_piece is None:
                            if enemy_found:
                                mandatory.append((pos, cell))
                            continue
                            
                        # Проверяем, не своя ли фигура на пути
                        cell_prefix = "бел" if "бел" in (cell_piece or "") else ("чер" if "чер" in (cell_piece or "") else "")
                        if cell_prefix and color.startswith(cell_prefix):
                            break
                            
                        if opposite_prefix in (cell_piece or "") and board.positions.get(next_cell) is None:
                            # Проверка, что не бьём уже съеденного
                            if cell not in pending_batyr_captures:
                                enemy_found = True
                                mandatory.append((pos, next_cell))
                                
        return mandatory

    def _find_captured_enemy(
        self,
        positions: dict,
        piece_obj,
        from_pos: int,
        to_pos: int,
        pending_batyr_captures: List[int] = None
    ) -> Optional[int]:
        """Находит позицию врага, который будет съеден при взятии."""
        if pending_batyr_captures is None:
            pending_batyr_captures = []
            
        if piece_obj.get_type() in ["шатра", "бий"]:
            from game_engine.словари import shatra_and_biy_possible_captures
            return shatra_and_biy_possible_captures.get(from_pos, {}).get(to_pos)
        if piece_obj.get_type() == "батыр":
            # Для батыра: последняя съеденная фигура (она на пути к to_pos)
            # Позиция врага — это последняя непроходная клетка перед to_pos
            if pending_batyr_captures:
                return pending_batyr_captures[-1]
            
            # Если pending пуст — ищем первую вражескую фигуру на пути
            from game_engine.словари import batyr_moves_and_captures
            for direction in batyr_moves_and_captures.get(from_pos, []):
                for pos in direction:
                    if pos == to_pos:
                        return None
                    cell = positions.get(pos)
                    if cell and "белый" != cell and "черный" != cell:
                        # Это вражеская фигура
                        if positions.get(pos) and piece_obj.get_color() not in positions[pos]:
                            return pos
                    if cell is not None:
                        break
                        
        return None

    def _add_to_history(self, positions: dict):
        pos_key = str(sorted(positions.items()))
        history_of_positions[pos_key] = history_of_positions.get(pos_key, 0) + 1

    def reset(self):
        history_of_positions.clear()