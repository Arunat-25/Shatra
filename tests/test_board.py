"""Тесты доски"""

from game_engine.board import Board


def make_default_cells():
    """Стандартная доска со всеми None"""
    return {i: None for i in range(1, 63)}


def make_initial_cells():
    """Начальная расстановка фигур"""
    cells = {i: None for i in range(1, 63)}
    for i in range(1, 10):
        cells[i] = "черная шатра"
    cells[10] = "черный бий"
    cells[11] = "черный батыр"
    cells[17] = "черный батыр"
    for i in range(54, 63):
        cells[i] = "белая шатра"
    cells[53] = "белый бий"
    cells[46] = "белый батыр"
    cells[52] = "белый батыр"
    return cells


def test_board_initialization():
    """Доска инициализируется 62 клетками"""
    cells = make_default_cells()
    b = Board(cells)
    assert len(b.cells) == 62, f"Ожидалось 62 клетки, получено {len(b.cells)}"
    print("✅ test_board_initialization пройден")


def test_board_has_pieces():
    """На доске есть фигуры в начальной позиции"""
    cells = make_initial_cells()
    b = Board(cells)
    black_pieces = [c for c in b.cells.values() if c and 'черный' in c]
    white_pieces = [c for c in b.cells.values() if c and 'белый' in c]
    assert len(black_pieces) > 0, "Должны быть чёрные фигуры"
    assert len(white_pieces) > 0, "Должны быть белые фигуры"
    print("✅ test_board_has_pieces пройден")


def test_get_piece_object():
    """get_piece_object возвращает объект фигуры"""
    cells = make_initial_cells()
    b = Board(cells)
    obj = b.get_piece_object(1)
    assert obj is not None, "На 1 должна быть фигура"
    assert obj.get_type() == 'шатра', f"Ожидалась шатра, получено {obj.get_type()}"
    assert obj.get_color() == 'черный'
    print("✅ test_get_piece_object пройден")


def test_move_piece():
    """Ход перемещает фигуру: старая клетка пуста, новая занята"""
    cells = make_initial_cells()
    b = Board(cells)
    from_cell = 1
    to_cell = 11
    b.move_piece(from_cell, to_cell)
    assert b.cells[from_cell] is None, f"Клетка {from_cell} должна быть пуста"
    assert b.cells[to_cell] is not None, f"Клетка {to_cell} должна быть занята"
    print("✅ test_move_piece пройден")


def test_remove_piece():
    """После удаления клетка пуста"""
    cells = make_initial_cells()
    b = Board(cells)
    b.remove_piece(1)
    assert b.cells[1] is None, "Клетка 1 должна быть пуста"
    print("✅ test_remove_piece пройден")


def test_copy_cells():
    """Бронированная копия не влияет на оригинал"""
    cells = make_initial_cells()
    b = Board(cells)
    cells_copy = b.copy_cells()
    cells_copy[1] = 'белая шатра'
    assert b.cells[1] != 'белая шатра', "Оригинал не должен измениться"
    print("✅ test_copy_cells пройден")


if __name__ == '__main__':
    test_board_initialization()
    test_board_has_pieces()
    test_get_piece_object()
    test_move_piece()
    test_remove_piece()
    test_copy_cells()
    print("\n🎉 Все тесты доски пройдены!")