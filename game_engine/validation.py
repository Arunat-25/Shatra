from typing import List, Tuple, Optional
from game_engine.board import Board
from game_engine.dictionaries import (
    shatra_and_biy_possible_captures,
    batyr_moves_and_captures,
)


def get_all_mandatory_captures(
    board: Board,
    color: str,
    batyr_captured_this_turn: List[int] = None
) -> List[Tuple[int, int]]:
    """Возвращает список (from_cell, to_cell) для всех обязательных взятий."""
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []

    mandatory = []
    opponent_prefix = "чер" if color == "белый" else "бел"

    for pos, piece in board.get_all_pieces():
        if piece.get_color() != color:
            continue

        piece_type = piece.get_type()

        if piece_type in ["шатра", "бий"]:
            possible_captures = shatra_and_biy_possible_captures.get(pos, {})
            for to_cell, enemy_cell in possible_captures.items():
                enemy_piece = board.cells.get(enemy_cell)
                if (enemy_piece and opponent_prefix in enemy_piece and
                        board.cells.get(to_cell) is None):
                    if piece._can_enter_fortress(board.cells, pos, to_cell):
                        mandatory.append((pos, to_cell))

        elif piece_type == "батыр":
            for direction in batyr_moves_and_captures.get(pos, []):
                enemy_found = False
                for cell in direction:
                    cell_piece = board.cells.get(cell)

                    if cell in batyr_captured_this_turn:
                        continue

                    # Своя фигура — преграда
                    if cell_piece:
                        cell_prefix = "бел" if "бел" in cell_piece else ("чер" if "чер" in cell_piece else "")
                        if cell_prefix and color.startswith(cell_prefix):
                            break

                        # Враг найден
                        if opponent_prefix in cell_piece:
                            if cell not in batyr_captured_this_turn:
                                enemy_found = True
                                # Добавляем только пустые клетки за этим врагом (до следующего врага)
                                for next_cell in direction[direction.index(cell) + 1:]:
                                    next_piece = board.cells.get(next_cell)
                                    if next_piece is None:
                                        mandatory.append((pos, next_cell))
                                    elif opponent_prefix in next_piece:
                                        # Следующий враг сразу — не добавляем клетки за ним
                                        break
                                    else:
                                        break  # своя — конец
                                break
                            continue

                    # Пустая клетка после врага (но не за несколькими врагами подряд)
                    if enemy_found:
                        if cell_piece is None:
                            mandatory.append((pos, cell))
                        elif opponent_prefix in cell_piece:
                            # Второй враг подряд — не добавляем клетки за ним
                            break

    return mandatory


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
    """Проверяет возможность хода."""
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []

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
        mandatory_captures = get_all_mandatory_captures(board, current_color, batyr_captured_this_turn)
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
                        return False, "Своя фигура на пути"

    # Пробуем взятие
    if piece.can_capture(cells, from_cell, to_cell, batyr_captured_this_turn):
        return True, ""

    # Пробуем обычный ход
    if piece.can_move(cells, from_cell, to_cell):
        return True, ""

    return False, "Недопустимый ход"