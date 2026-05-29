from typing import List, Tuple, Optional

from game_engine.board import Board
from game_engine.dictionaries import (
    shatra_and_biy_possible_captures,
    batyr_moves_and_captures,
)


def _dbg(*_args, **_kwargs):
    """No-op. Оставлен, чтобы не трогать места вызова; отладочный лог удалён."""
    return None


def get_all_mandatory_captures(
    board: Board,
    color: str,
    batyr_captured_this_turn: List[int] = None
) -> List[Tuple[int, int]]:
    """Возвращает список (from_cell, to_cell) для всех обязательных взятий.
    
    Единая логика: для каждой фигуры перебираются все возможные цели из словарей,
    и проверяется piece.can_capture(). Это гарантирует полное совпадение с validate_move().
    """
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []

    mandatory = []
    cells = board.cells

    for pos, piece in board.get_all_pieces():
        if piece.get_color() != color:
            continue

        piece_type = piece.get_type()
        candidates = set()

        if piece_type in ["шатра", "бий"]:
            # Все цели из captures и moves
            for to_cell in shatra_and_biy_possible_captures.get(pos, {}):
                candidates.add(to_cell)

        elif piece_type == "батыр":
            for direction in batyr_moves_and_captures.get(pos, []):
                for target in direction:
                    candidates.add(target)

        # Проверяем каждую цель через can_capture (ту же функцию, что в validate_move)
        for to_cell in sorted(candidates):
            if piece.can_capture(cells, pos, to_cell, batyr_captured_this_turn):
                mandatory.append((pos, to_cell))

    return mandatory


def batyr_can_continue_capture(
    board: Board,
    from_cell: int,
    color: str,
    batyr_captured_this_turn: List[int] = None,
) -> bool:
    """Есть ли у батыра на from_cell продолжение цепочки взятий (пустая клетка приземления)."""
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []

    piece = board.get_piece_object(from_cell)
    if not piece or piece.get_type() != "батыр":
        return False

    cells = board.cells
    for start, target in get_all_mandatory_captures(board, color, batyr_captured_this_turn):
        if start == from_cell and piece.can_capture(cells, from_cell, target, batyr_captured_this_turn):
            return True
    return False


def find_captured_enemy(
    cells: dict,
    piece,
    from_cell: int,
    to_cell: int,
    batyr_captured_this_turn: List[int] = None
) -> Optional[int]:
    """Находит клетку вражеской фигуры, которая была взята при ходе from_cell -> to_cell."""
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []

    if piece.get_type() in ["шатра", "бий"]:
        return shatra_and_biy_possible_captures.get(from_cell, {}).get(to_cell)

    if piece.get_type() == "батыр":
        opponent_prefix = "чер" if piece.get_color() == "белый" else "бел"
        for direction in batyr_moves_and_captures.get(from_cell, []):
            if to_cell not in direction:
                continue
            for pos in direction:
                if pos == to_cell:
                    return None
                cell_content = cells.get(pos)
                # Пропускаем уже захваченные
                if cell_content and opponent_prefix in cell_content:
                    if pos not in batyr_captured_this_turn:
                        return pos
                    continue
                if cell_content is not None:
                    return None

    return None


def validate_move(
    cells: dict,
    from_cell: int,
    to_cell: int,
    current_color: str,
    batyr_captured_this_turn: List[int] = None,
    check_mandatory: bool = True,
    chain_capture_cell: int = None
) -> Tuple[bool, str]:
    """Проверяет возможность хода.

    Возвращает (valid, message). Для машинной обработки используйте validate_move_with_code().
    """
    valid, msg, _code = validate_move_with_code(
        cells=cells,
        from_cell=from_cell,
        to_cell=to_cell,
        current_color=current_color,
        batyr_captured_this_turn=batyr_captured_this_turn,
        check_mandatory=check_mandatory,
        chain_capture_cell=chain_capture_cell,
    )
    return valid, msg


def validate_move_with_code(
    cells: dict,
    from_cell: int,
    to_cell: int,
    current_color: str,
    batyr_captured_this_turn: List[int] = None,
    check_mandatory: bool = True,
    chain_capture_cell: int = None,
) -> Tuple[bool, str, str]:
    """Расширенная валидация: (valid, message, code)."""
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []

    board = Board(cells)

    # 1. Есть ли фигура на from_cell
    piece = board.get_piece_object(from_cell)
    if not piece:
        return False, "Нет фигуры на выбранной позиции", "NO_PIECE"

    # 2. Своего ли цвета?
    if piece.get_color() != current_color:
        return False, "Это не ваша фигура", "WRONG_COLOR"

    # 3. Свободна ли клетка назначения?
    if cells.get(to_cell) is not None:
        return False, "Клетка занята", "TARGET_OCCUPIED"

    # 4. Проверка обязательных взятий
    if check_mandatory:
        mandatory_captures = get_all_mandatory_captures(board, current_color, batyr_captured_this_turn)
        if mandatory_captures:
            # Есть ли среди атакующих не-бий (шатра/батыр)?
            has_non_biy_attacker = any(
                board.get_piece_object(f) and board.get_piece_object(f).get_type() != "бий"
                for f, _ in mandatory_captures
            )

            attacker_positions = {f for f, _ in mandatory_captures}

            if from_cell not in attacker_positions:
                if has_non_biy_attacker:
                    _dbg(
                        "H1",
                        "game_engine/validation.py:mandatory",
                        "reject: mandatory capture exists for other piece",
                        {
                            "from": from_cell,
                            "to": to_cell,
                            "color": current_color,
                            "mandatory": mandatory_captures,
                        },
                    )
                    return False, "Обязательное взятие!", "MANDATORY_CAPTURE_OTHER_PIECE"
                else:
                    # Только бии могут взять — бий не обязан брать, но обязан ходить
                    if piece.get_type() != "бий":
                        return False, "Бий обязан ходить!", "ONLY_BIY_CAN_CAPTURE"
            else:
                capture_targets = {t for f, t in mandatory_captures if f == from_cell}
                if to_cell not in capture_targets:
                    if piece.get_type() == "бий" and not has_non_biy_attacker:
                        pass  # бий может не брать, если только бии могут взять
                    else:
                        _dbg(
                            "H2",
                            "game_engine/validation.py:mandatory",
                            "reject: mandatory capture required from this piece",
                            {
                                "from": from_cell,
                                "to": to_cell,
                                "color": current_color,
                                "targets": sorted(list(capture_targets)),
                            },
                        )
                        return False, "Нужно бить!", "MANDATORY_CAPTURE_THIS_PIECE"

    # 5. Проверка через класс фигуры
    piece = board.get_piece_object(from_cell)
    if not piece:
        return False, "Ошибка определения фигуры", "INTERNAL_NO_PIECE"

    # 5a. Универсальная проверка: если это взятие (прыжок через клетку)
    if piece.get_type() in ["шатра", "бий"]:
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
        for direction in batyr_moves_and_captures.get(from_cell, []):
            if to_cell in direction:
                for cell in direction:
                    if cell == to_cell:
                        break
                    cell_piece = cells.get(cell)
                    if cell_piece and current_color in cell_piece:
                        return False, "Своя фигура на пути", "OWN_PIECE_BLOCKS_BATYR"

    # Пробуем взятие
    if piece.can_capture(cells, from_cell, to_cell, batyr_captured_this_turn):
        return True, "", "OK_CAPTURE"

    # Пробуем обычный ход
    if piece.can_move(cells, from_cell, to_cell):
        return True, "", "OK_MOVE"

    return False, "Недопустимый ход", "ILLEGAL_MOVE"