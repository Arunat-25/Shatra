from typing import List, Tuple, Optional
import copy

from game_engine.board import Board
from game_engine.models import GameEventResult
from game_engine.endgame import is_game_over, _count_biys
from game_engine.validation import (
    get_all_mandatory_captures,
    batyr_can_continue_capture,
    find_captured_enemy,
    validate_move,
)
from game_engine.dictionaries import (
    shatra_and_biy_possible_captures,
)

def _dbg(*_args, **_kwargs):
    """No-op. Оставлен, чтобы не трогать места вызова; отладочный лог удалён."""
    return None

# Позиции превращения шатры в батыра
PROMOTION_FOR_WHITE = {1, 2, 3}
PROMOTION_FOR_BLACK = {60, 61, 62}


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


def execute_move(
    cells: dict,
    from_cell: int,
    to_cell: int,
    current_color: str,
    batyr_captured_this_turn: List[int] = None
) -> Tuple[dict, List[int], List[int]]:
    """Выполняет ход: перемещает фигуру и обрабатывает взятие."""
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []

    new_cells = copy.deepcopy(cells)
    board = Board(new_cells)
    captured_positions = []
    new_batyr_captures = copy.copy(batyr_captured_this_turn)

    piece = board.get_piece_object(from_cell)

    if piece and piece.can_capture(cells, from_cell, to_cell, batyr_captured_this_turn):
        enemy_cell = find_captured_enemy(cells, piece, from_cell, to_cell, batyr_captured_this_turn)
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


def process_move(
    cells: dict,
    current_color: str,
    from_cell: int,
    to_cell: int,
    chain_capture_cell: int = None,
    batyr_captured_this_turn: List[int] = None,
    position_history: dict = None,
    moves_with_two_biys: int = 0
) -> GameEventResult:
    """Обрабатывает ход: валидация, выполнение, проверка окончания."""
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []
    if position_history is None:
        position_history = {}

    current_batyr_captures = copy.copy(batyr_captured_this_turn)
    board_copy = copy.deepcopy(cells)

    # 1. Проверка конца игры перед ходом
    board_obj = Board(board_copy)
    over, winner = is_game_over(board_obj, position_history, moves_with_two_biys)
    if over:
        return GameEventResult(
            message=winner or "Ничья",
            movers_color=None,
            updated_positions=cells,
            game_over=True,
            winner=winner
        )

    # 2. Обработка передачи хода (бий нажал "передать ход")
    if chain_capture_cell == 0:
        over, winner = is_game_over(Board(board_copy), position_history, moves_with_two_biys)
        return _finish_move(
            positions=board_copy,
            mover_color=current_color,
            message="Ход передан.",
            history=True,
            clear_pending=True,
            game_over=over,
            winner=winner
        )

    # 3. Проверка обязательного взятия той же фигурой
    if chain_capture_cell is not None and chain_capture_cell != 0:
        return _process_chain_capture(
            board_copy, cells, current_color, from_cell, to_cell,
            chain_capture_cell, current_batyr_captures, position_history, moves_with_two_biys
        )

    # 4. Валидация хода (если не было цепочки)
    if chain_capture_cell is None or chain_capture_cell == 0:
        valid, error_msg = validate_move(
            board_copy, from_cell, to_cell, current_color, current_batyr_captures
        )
        if not valid:
            _dbg("H6", "game_engine/moves.py:validate", "move rejected", {
                "color": current_color, "from": from_cell, "to": to_cell, "msg": error_msg,
                "chain": chain_capture_cell, "batyr_caps": current_batyr_captures,
            })
            return GameEventResult(
                message=error_msg,
                movers_color=current_color,
                updated_positions=cells
            )

    # 5. Выполнение хода
    new_cells, captured_positions, new_batyr_captures = execute_move(
        board_copy, from_cell, to_cell, current_color, current_batyr_captures
    )
    _dbg("H6", "game_engine/moves.py:execute", "after execute_move", {
        "color": current_color, "from": from_cell, "to": to_cell,
        "captured": captured_positions, "batyr_caps": new_batyr_captures,
    })

    piece = Board(board_copy).get_piece_object(from_cell)
    # Если from_cell уже пуста после execute_move (фигура переместилась),
    # читаем тип из to_cell
    if piece is None:
        piece = Board(board_copy).get_piece_object(to_cell)
    piece_kind = piece.get_type() if piece else ""

    # 5b. Превращение шатры в батыра при достижении края доски
    if piece_kind == "шатра":
        if _promote_shatra(new_cells, to_cell, current_color):
            piece_kind = "батыр"
            return _finish_move(
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
    over, winner = is_game_over(next_board, position_history, moves_with_two_biys)
    if over:
        return GameEventResult(
            message=winner or "Ничья",
            movers_color=None,
            updated_positions=new_cells,
            game_over=True,
            winner=winner,
            captured_positions=captured_positions
        )

    # 6. Определяем, нужно ли продолжать взятие
    next_mandatory_captures = get_all_mandatory_captures(next_board, current_color, new_batyr_captures)
    has_captured = len(captured_positions) > 0

    can_continue_chain = False
    if has_captured:
        if piece_kind in ["шатра", "бий"]:
            for to_cell_next, enemy_cell_next in shatra_and_biy_possible_captures.get(to_cell, {}).items():
                enemy_piece = new_cells.get(enemy_cell_next)
                target_free = new_cells.get(to_cell_next) is None
                if enemy_piece and target_free:
                    enemy_prefix = "бел" if current_color == "черный" else "чер"
                    if enemy_prefix in enemy_piece:
                        can_continue_chain = True
                        break
        else:
            can_continue_chain = batyr_can_continue_capture(
                next_board, to_cell, current_color, new_batyr_captures
            )

    can_pass_turn = False
    if piece_kind == "бий" and has_captured:
        can_pass_turn = True

    if can_continue_chain:
        _dbg("H6", "game_engine/moves.py:chain", "continue chain", {
            "piece_kind": piece_kind, "from": from_cell, "to": to_cell, "captured": captured_positions,
        })
        return GameEventResult(
            message="Продолжайте взятие!",
            movers_color=current_color,
            updated_positions=new_cells,
            captured_positions=captured_positions,
            opportunity_pass_the_move=can_pass_turn,
            position_for_mandatory_capture=to_cell,
            captured_pieces=new_batyr_captures
        )

    # Если взятие завершилось — ход передаётся сопернику.
    if has_captured and not can_continue_chain:
        _dbg("H6", "game_engine/moves.py:chain", "capture ended; turn passes", {
            "piece_kind": piece_kind, "from": from_cell, "to": to_cell, "captured": captured_positions,
        })
        next_player = _opponent(current_color)
        over, winner = is_game_over(next_board, position_history, moves_with_two_biys)
        return _finish_move(
            positions=new_cells,
            mover_color=current_color,
            message=f"Теперь ходит {next_player}",
            history=True,
            clear_pending=True,
            game_over=over,
            winner=winner,
            captured_positions=captured_positions,
            captured_pieces=new_batyr_captures
        )

    # 8. Ход завершён — передаём ход
    next_player = _opponent(current_color)
    over, winner = is_game_over(next_board, position_history, moves_with_two_biys)

    chain_capture_pos = None
    if next_player and not over:
        mandatory_captures = get_all_mandatory_captures(Board(new_cells), next_player)
        if mandatory_captures:
            chain_capture_pos = mandatory_captures[0][0]
    _dbg("H6", "game_engine/moves.py:finish", "finish move", {
        "next_player": next_player, "over": over, "mandatory_pos": chain_capture_pos,
        "captured": captured_positions,
    })

    return _finish_move(
        positions=new_cells,
        mover_color=current_color,
        message=f"Теперь ходит {next_player}",
        history=True,
        clear_pending=True,
        game_over=over,
        winner=winner,
        captured_positions=captured_positions,
        opportunity_pass=can_pass_turn,
        mandatory_pos=chain_capture_pos
    )


def _process_chain_capture(
    board_copy, cells, current_color, from_cell, to_cell,
    chain_capture_cell, current_batyr_captures, position_history: dict = None, moves_with_two_biys: int = 0
) -> GameEventResult:
    """Обрабатывает продолжение цепочки взятий."""
    if from_cell != chain_capture_cell:
        return GameEventResult(
            message="Продолжайте взятие той же фигурой!",
            movers_color=current_color,
            updated_positions=cells
        )
    piece = Board(board_copy).get_piece_object(from_cell)
    if piece and piece.get_type() in ["шатра", "бий"]:
        return _process_chain_shatra_biy(
            board_copy,
            cells,
            current_color,
            from_cell,
            to_cell,
            current_batyr_captures,
            piece,
            position_history=position_history,
            moves_with_two_biys=moves_with_two_biys,
        )
    elif piece and piece.get_type() == "батыр":
        return _process_chain_batyr(
            board_copy,
            cells,
            current_color,
            from_cell,
            to_cell,
            current_batyr_captures,
            piece,
            position_history=position_history,
            moves_with_two_biys=moves_with_two_biys,
        )
    else:
        return GameEventResult(
            message="Неизвестная фигура",
            movers_color=current_color,
            updated_positions=cells
        )


def _process_chain_shatra_biy(
    board_copy, cells, current_color, from_cell, to_cell,
    current_batyr_captures, piece, position_history: dict = None, moves_with_two_biys: int = 0
) -> GameEventResult:
    """Обрабатывает цепочку взятий для шатры/бия."""

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

    # Если был взят бий соперника — игра завершается сразу, даже если есть продолжение цепочки.
    over, winner = is_game_over(board, position_history, moves_with_two_biys)
    if over:
        return GameEventResult(
            message=winner or "Ничья",
            movers_color=None,
            updated_positions=board.copy_cells(),
            game_over=True,
            winner=winner,
            captured_positions=captured_positions,
            captured_pieces=new_batyr_captures,
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

    next_player = _opponent(current_color)
    return _finish_move(
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


def _process_chain_batyr(
    board_copy, cells, current_color, from_cell, to_cell,
    current_batyr_captures, piece, position_history: dict = None, moves_with_two_biys: int = 0
) -> GameEventResult:
    """Обрабатывает цепочку взятий для батыра."""
    # Проверяем, что это именно взятие, а не обычный ход
    if not piece.can_capture(board_copy, from_cell, to_cell, current_batyr_captures):
        return GameEventResult(
            message="Нужно бить! Продолжите взятие.",
            movers_color=current_color,
            updated_positions=cells
        )

    # Для батыра используем общий механизм execute_move
    new_cells, captured_positions, new_batyr_captures = execute_move(
        board_copy, from_cell, to_cell, current_color, current_batyr_captures
    )
    board = Board(new_cells)

    over, winner = is_game_over(board, position_history, moves_with_two_biys)
    if over:
        return GameEventResult(
            message=winner or "Ничья",
            movers_color=None,
            updated_positions=new_cells,
            game_over=True,
            winner=winner,
            captured_positions=captured_positions
        )

    # Проверяем, может ли батыр продолжить (только на свободные клетки)
    can_continue = batyr_can_continue_capture(
        board, to_cell, current_color, new_batyr_captures
    )

    if can_continue:
        return GameEventResult(
            message="Продолжайте взятие!",
            movers_color=current_color,
            updated_positions=new_cells,
            captured_positions=captured_positions,
            opportunity_pass_the_move=False,
            position_for_mandatory_capture=to_cell,
            captured_pieces=new_batyr_captures
        )

    next_player = _opponent(current_color)
    return _finish_move(
        positions=new_cells,
        mover_color=current_color,
        message=f"Теперь ходит {next_player}",
        history=True,
        clear_pending=True,
        game_over=False,
        winner=None,
        captured_positions=captured_positions,
        captured_pieces=new_batyr_captures
    )


def _finish_move(
    positions: dict,
    mover_color: str,
    message: str = "",
    history: bool = False,
    clear_pending: bool = False,
    game_over: bool = False,
    winner: str = None,
    captured_positions: List[int] = None,
    opportunity_pass: bool = False,
    mandatory_pos: int = None,
    captured_pieces: List[int] = None
) -> GameEventResult:
    """Завершает ход: переключает игрока и возвращает результат."""
    next_mover = "черный" if mover_color == "белый" else "белый"

    return GameEventResult(
        message=message,
        movers_color=next_mover,
        updated_positions=positions,
        captured_positions=captured_positions or [],
        game_over=game_over,
        winner=winner,
        opportunity_pass_the_move=opportunity_pass,
        position_for_mandatory_capture=mandatory_pos,
        captured_pieces=captured_pieces or []
    )


def _opponent(color: str) -> str:
    return "черный" if color == "белый" else "белый"


def has_mandatory_from_position(cells: dict, color: str, pos: int = None) -> bool:
    """Проверяет, есть ли обязательное взятие из указанной позиции."""
    board = Board(cells)
    mandatory = get_all_mandatory_captures(board, color)
    if pos is not None:
        return any(f == pos for f, _ in mandatory)
    return len(mandatory) > 0