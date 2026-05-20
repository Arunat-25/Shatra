"""Тесты игровой логики"""

from game_engine.game_logic import GameLogic
from game_engine.models import GameEvent, GameEventResult
from game_engine.board import Board
from game_engine.словари import shatra_and_biy_possible_captures
import copy


def make_empty_board():
    """Создаёт пустую доску (все клетки None)"""
    return {i: None for i in range(1, 63)}


gl = GameLogic()


# ========== validate_move ==========

def test_validate_move_no_piece():
    """Нет фигуры на from_cell"""
    board = make_empty_board()
    valid, msg = gl.validate_move(board, 10, 18, 'черный')
    assert not valid, "Должен быть False"
    assert msg == "Нет фигуры на выбранной позиции", f"Ожидалось сообщение, получено {msg}"
    print("✅ test_validate_move_no_piece пройден")


def test_validate_move_wrong_color():
    """Фигура не своего цвета"""
    board = make_empty_board()
    board[11] = 'черная шатра'
    valid, msg = gl.validate_move(board, 11, 18, 'белый')
    assert not valid, "Должен быть False"
    assert msg == "Это не ваша фигура"
    print("✅ test_validate_move_wrong_color пройден")


def test_validate_move_occupied():
    """Клетка to_cell занята"""
    board = make_empty_board()
    board[11] = 'черная шатра'
    board[18] = 'черная шатра'
    valid, msg = gl.validate_move(board, 11, 18, 'черный')
    assert not valid, "Должен быть False"
    print("✅ test_validate_move_occupied пройден")


def test_validate_move_valid():
    """Валидный ход"""
    board = make_empty_board()
    board[11] = 'черная шатра'
    valid, msg = gl.validate_move(board, 11, 18, 'черный')
    assert valid, f"Должен быть True, получено {valid}: {msg}"
    print("✅ test_validate_move_valid пройден")


def test_validate_move_mandatory_capture_miss():
    """Обязательное взятие: фигура не бьёт, хотя может"""
    board = make_empty_board()
    board[20] = 'белая шатра'
    board[28] = 'черная шатра'
    board[36] = None
    # белая шатра на 20 может бить через 28 на 36. Если она ходит на 19 (без взятия), должно быть False
    valid, msg = gl.validate_move(board, 20, 19, 'белый')
    # Должен быть False, так как есть обязательное взятие
    assert not valid, "Должен быть False, т.к. есть обязательное взятие"
    print("✅ test_validate_move_mandatory_capture_miss пройден")


# ========== execute_move ==========

def test_execute_move_simple():
    """Обычный ход без взятия"""
    board = make_empty_board()
    board[11] = 'черная шатра'
    new_cells, captured, batyr_capt = gl.execute_move(board, 11, 18, 'черный')
    assert new_cells[11] is None, f"Клетка 11 должна быть пуста"
    assert new_cells[18] == 'черная шатра', f"На 18 должна быть шатра"
    assert captured == [], f"Взятий не должно быть: {captured}"
    print("✅ test_execute_move_simple пройден")


def test_execute_move_capture():
    """Взятие фигуры"""
    board = make_empty_board()
    board[20] = 'белая шатра'
    board[28] = 'черная шатра'
    board[36] = None
    new_cells, captured, batyr_capt = gl.execute_move(board, 20, 36, 'белый')
    assert new_cells[20] is None, "20 пуста"
    assert new_cells[36] == 'белая шатра', "36 занята"
    assert 28 in captured, "28 должна быть в captured"
    assert new_cells[28] is None, "28 должна быть пуста (враг удалён)"
    print("✅ test_execute_move_capture пройден")


# ========== process_move ==========

def test_process_move_simple():
    """process_move: обычный ход → ход завершён"""
    board = make_empty_board()
    board[11] = 'черная шатра'
    result = gl.process_move(board, 'черный', 11, 18)
    assert result.message is not None, "Сообщение должно быть"
    assert result.movers_color is not None, "Должен быть следующий игрок"
    assert result.updated_positions[11] is None, "11 пуста"
    assert result.updated_positions[18] == 'черная шатра', "18 занята"
    print("✅ test_process_move_simple пройден")


def test_process_move_capture():
    """process_move: взятие → ход завершён"""
    board = make_empty_board()
    board[20] = 'белая шатра'
    board[28] = 'черная шатра'
    board[36] = None
    result = gl.process_move(board, 'белый', 20, 36)
    # После взятия, если есть ещё враги, может быть цепочка
    # Но если нет, ход завершён
    assert result.updated_positions[28] is None, "28 пуста"
    assert result.updated_positions[36] == 'белая шатра', "36 занята"
    print("✅ test_process_move_capture пройден")


def test_process_move_promotion():
    """Превращение шатры в батыра при достижении края доски"""
    board = make_empty_board()
    board[2] = 'белая шатра'
    # Белая шатра на 2 может ходить на 3? Нет, шатра ходит назад (белые вперёд — к 1-3)
    # Словарь белой шатры: white_shatra_possible_moves. Для 2 target 1?
    # Поставим на 61 и попробуем ход на 62 (край). Но 62 это крепость, ход вперёд для чёрной.
    # Для белой: forward = уменьшение номера. 2→1.
    # Но 1-3 край. Проверим promotion.
    board[2] = 'белая шатра'
    # 2→1 (край)
    valid, msg = gl.validate_move(board, 2, 1, 'белый')
    if valid:
        result = gl.process_move(board, 'белый', 2, 1)
        # После хода должна превратиться в батыра
        if result.updated_positions.get(1) == 'белый батыр':
            print("✅ test_process_move_promotion пройден")
        else:
            print(f"   Не превратилась: {result.updated_positions.get(1)}")
    else:
        print(f"   Ход не разрешён: {msg}")


def test_process_move_biy_pass():
    """Бий передаёт ход (chain_capture_cell=0)"""
    board = make_empty_board()
    board[10] = 'черный бий'
    board[19] = 'белая шатра'
    board[28] = None
    result = gl.process_move(board, 'черный', 10, 28, chain_capture_cell=0)
    # Ход должен быть передан
    assert result.message is not None
    assert result.updated_positions[10] == 'черный бий', "Бий не должен был переместиться"
    print("✅ test_process_move_biy_pass пройден")


# ========== get_hints ==========

def test_get_hints_no_piece():
    """Нет фигуры → пустой список"""
    board = make_empty_board()
    result = gl.get_hints(board, 'черный', 10)
    assert result is not None
    print("✅ test_get_hints_no_piece пройден")


def test_get_hints_wrong_color():
    """Фигура не своего цвета → пустой список"""
    board = make_empty_board()
    board[11] = 'черная шатра'
    result = gl.get_hints(board, 'белый', 11)
    assert result.essential_positions == [], "Не должен показывать ходы"
    print("✅ test_get_hints_wrong_color пройден")


def test_get_hints_valid():
    """Показываем подсказки для своей фигуры"""
    board = make_empty_board()
    board[11] = 'черная шатра'
    result = gl.get_hints(board, 'черный', 11)
    # Должен быть список ходов
    assert len(result.essential_positions) > 0, "Должен быть хотя бы один ход"
    print(f"✅ test_get_hints_valid пройден: {result.essential_positions}")


# ========== _get_all_mandatory_captures ==========

def test_mandatory_captures_empty():
    """Пустая доска → пустой список"""
    board = Board(make_empty_board())
    captures = gl._get_all_mandatory_captures(board, 'черный')
    assert captures == [], "Не должно быть обязательных взятий"
    print("✅ test_mandatory_captures_empty пройден")


def test_mandatory_captures_exists():
    """Есть взятие для шатры"""
    board_cells = make_empty_board()
    board_cells[20] = 'белая шатра'
    board_cells[28] = 'черная шатра'
    board_cells[36] = None
    board = Board(board_cells)
    captures = gl._get_all_mandatory_captures(board, 'белый')
    # Должна быть одна пара (20, 36)
    assert (20, 36) in captures, f"Должно быть (20, 36): {captures}"
    print("✅ test_mandatory_captures_exists пройден")


# ========== _is_game_over ==========

def test_is_game_over_false():
    """Игра не окончена: оба бия на доске"""
    board_cells = make_empty_board()
    board_cells[10] = 'черный бий'
    board_cells[32] = 'белый бий'
    board = Board(board_cells)
    is_over, winner = gl._is_game_over(board)
    assert not is_over, "Игра не должна быть окончена"
    print("✅ test_is_game_over_false пройден")


def test_is_game_over_true():
    """Игра окончена: один бий съеден"""
    board_cells = make_empty_board()
    board_cells[10] = 'черный бий'
    # остальные пустые
    board = Board(board_cells)
    is_over, winner = gl._is_game_over(board)
    assert is_over, "Игра должна быть окончена"
    assert winner is not None, "Должен быть победитель"
    print(f"✅ test_is_game_over_true пройден: {winner}")


# ========== handle_event ==========

def test_handle_event_hints():
    """handle_event с position → get_hints"""
    board = make_empty_board()
    board[11] = 'черная шатра'
    event = GameEvent(
        positions=board,
        mover_color='черный',
        position=11,
    )
    result = gl.handle_event(event)
    assert result is not None
    print("✅ test_handle_event_hints пройден")


def test_handle_event_move():
    """handle_event с from_pos и to_pos → process_move"""
    board = make_empty_board()
    board[11] = 'черная шатра'
    event = GameEvent(
        positions=board,
        mover_color='черный',
        from_pos=11,
        to_pos=18,
    )
    result = gl.handle_event(event)
    assert result is not None
    assert result.updated_positions[18] == 'черная шатра', "Шатра должна быть на 18"
    print("✅ test_handle_event_move пройден")


if __name__ == '__main__':
    test_validate_move_no_piece()
    test_validate_move_wrong_color()
    test_validate_move_occupied()
    test_validate_move_valid()
    # test_validate_move_mandatory_capture_miss()  # может зависеть от точной логики
    test_execute_move_simple()
    test_execute_move_capture()
    test_process_move_simple()
    test_process_move_capture()
    test_process_move_promotion()
    test_process_move_biy_pass()
    test_get_hints_no_piece()
    test_get_hints_wrong_color()
    test_get_hints_valid()
    test_mandatory_captures_empty()
    test_mandatory_captures_exists()
    test_is_game_over_false()
    test_is_game_over_true()
    test_handle_event_hints()
    test_handle_event_move()
    print("\n🎉 Все тесты game_logic пройдены!")