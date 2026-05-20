"""Тесты шатры"""

from game_engine.pieces.shatra import Shatra


# ---------- can_move ----------

def test_can_move_forward_black():
    """Чёрная шатра может ходить вперёд"""
    board = {i: None for i in range(1, 63)}
    board[11] = 'черная шатра'
    s = Shatra('черный')
    assert s.can_move(board, 11, 18), "11→18 должен быть разрешён"
    print("✅ test_can_move_forward_black пройден")


def test_can_move_forward_white():
    """Белая шатра может ходить вперёд"""
    board = {i: None for i in range(1, 63)}
    board[52] = 'белая шатра'
    s = Shatra('белый')
    assert s.can_move(board, 52, 45), "52→45 должен быть разрешён"
    print("✅ test_can_move_forward_white пройден")


def test_can_move_side():
    """Шатра может ходить в сторону"""
    board = {i: None for i in range(1, 63)}
    board[11] = 'черная шатра'
    s = Shatra('черный')
    assert s.can_move(board, 11, 12), "11→12 должен быть разрешён"
    print("✅ test_can_move_side пройден")


def test_can_move_occupied():
    """Нельзя ходить на занятую клетку"""
    board = {i: None for i in range(1, 63)}
    board[11] = 'черная шатра'
    board[18] = 'черная шатра'
    s = Shatra('черный')
    assert not s.can_move(board, 11, 18), "11→18 на занятую должен быть запрещён"
    print("✅ test_can_move_occupied пройден")


def test_can_move_backward_black():
    """Чёрная шатра не может ходить назад (11→4 против направления)"""
    board = {i: None for i in range(1, 63)}
    board[11] = 'черная шатра'
    s = Shatra('черный')
    assert not s.can_move(board, 11, 4), "11→4 назад должен быть запрещён"
    print("✅ test_can_move_backward_black пройден")


def test_can_move_backward_white():
    """Белая шатра не может ходить назад (52→59 назад)"""
    board = {i: None for i in range(1, 63)}
    board[52] = 'белая шатра'
    s = Shatra('белый')
    assert not s.can_move(board, 52, 59), "52→59 назад должен быть запрещён"
    print("✅ test_can_move_backward_white пройден")


# ---------- выход из крепости ----------

def test_black_exit_fortress():
    """Чёрная шатра 9 может выйти на 11"""
    board = {i: None for i in range(1, 63)}
    board[9] = 'черная шатра'
    s = Shatra('черный')
    assert s.can_move(board, 9, 11), "9→11 должен быть разрешён"
    print("✅ test_black_exit_fortress пройден")


def test_white_exit_fortress():
    """Белая шатра 54 может выйти на 52"""
    board = {i: None for i in range(1, 63)}
    board[54] = 'белая шатра'
    s = Shatra('белый')
    assert s.can_move(board, 54, 52), "54→52 должен быть разрешён"
    print("✅ test_white_exit_fortress пройден")


# ---------- очерёдность ----------

def test_black_priority_blocked():
    """Чёрная 8 не может выйти, пока на 9 есть шатра"""
    board = {i: None for i in range(1, 63)}
    board[9] = 'черная шатра'
    board[8] = 'черная шатра'
    s = Shatra('черный')
    assert not s.can_move(board, 8, 11), "8→11 блокируется 9"
    print("✅ test_black_priority_blocked пройден")


def test_black_priority_allowed():
    """Чёрная 8 может выйти, если на 9 пусто"""
    board = {i: None for i in range(1, 63)}
    board[9] = None
    board[8] = 'черная шатра'
    s = Shatra('черный')
    assert s.can_move(board, 8, 11), "8→11 должен быть разрешён, если 9 пусто"
    print("✅ test_black_priority_allowed пройден")


def test_white_priority_blocked():
    """Белая 55 не может выйти, пока на 54 есть шатра"""
    board = {i: None for i in range(1, 63)}
    board[54] = 'белая шатра'
    board[55] = 'белая шатра'
    s = Shatra('белый')
    assert not s.can_move(board, 55, 32), "55→32 блокируется 54"
    print("✅ test_white_priority_blocked пройден")


def test_white_priority_allowed():
    """Белая 55 может выйти, если на 54 пусто"""
    board = {i: None for i in range(1, 63)}
    board[54] = None
    board[55] = 'белая шатра'
    s = Shatra('белый')
    assert s.can_move(board, 55, 32), "55→32 должен быть разрешён, если 54 пусто"
    print("✅ test_white_priority_allowed пройден")


# ---------- can_capture ----------

def test_capture_enemy():
    """Шатра может бить вражескую фигуру"""
    board = {i: None for i in range(1, 63)}
    board[20] = 'белая шатра'
    board[28] = 'черная шатра'
    board[36] = None
    s = Shatra('белый')
    assert s.can_capture(board, 20, 36), "20→36 (через 28) должен быть True"
    print("✅ test_capture_enemy пройден")


def test_capture_no_enemy():
    """Нет вражеской фигуры для взятия"""
    board = {i: None for i in range(1, 63)}
    board[20] = 'белая шатра'
    board[36] = None
    s = Shatra('белый')
    assert not s.can_capture(board, 20, 36), "20→36, нет врага на 28"
    print("✅ test_capture_no_enemy пройден")


def test_capture_target_occupied():
    """Нельзя бить, если клетка назначения занята"""
    board = {i: None for i in range(1, 63)}
    board[20] = 'белая шатра'
    board[28] = 'черная шатра'
    board[36] = 'белая шатра'
    s = Shatra('белый')
    assert not s.can_capture(board, 20, 36), "20→36, 36 занята"
    print("✅ test_capture_target_occupied пройден")


def test_capture_forbidden_own_fortress_white():
    """Шатра с большого поля не может бить в свою крепость (50→55 через 53)"""
    board = {i: None for i in range(1, 63)}
    board[50] = 'белая шатра'
    board[53] = 'черная шатра'
    board[55] = None
    s = Shatra('белый')
    assert not s.can_capture(board, 50, 55), "50→55 запрещён (бить в свою крепость)"
    print("✅ test_capture_forbidden_own_fortress_white пройден")


def test_capture_forbidden_own_fortress_black():
    """Чёрная шатра с большого поля не может бить в свою крепость (14→8 через 10)"""
    board = {i: None for i in range(1, 63)}
    board[14] = 'черная шатра'
    board[10] = 'белая шатра'
    board[8] = None
    s = Shatra('черный')
    assert not s.can_capture(board, 14, 8), "14→8 запрещён (бить в свою крепость)"
    print("✅ test_capture_forbidden_own_fortress_black пройден")


def test_capture_not_in_own_fortress():
    """Шатра может бить, если target не в своей крепости (11→25 через 18)"""
    board = {i: None for i in range(1, 63)}
    board[11] = 'черная шатра'
    board[18] = 'белая шатра'
    board[25] = None
    s = Shatra('черный')
    assert s.can_capture(board, 11, 25), "11→25 (через 18) должен быть True"
    print("✅ test_capture_not_in_own_fortress пройден")


if __name__ == '__main__':
    test_can_move_forward_black()
    test_can_move_forward_white()
    test_can_move_side()
    test_can_move_occupied()
    test_can_move_backward_black()
    test_can_move_backward_white()
    test_black_exit_fortress()
    test_white_exit_fortress()
    test_black_priority_blocked()
    test_black_priority_allowed()
    test_white_priority_blocked()
    test_white_priority_allowed()
    test_capture_enemy()
    test_capture_no_enemy()
    test_capture_target_occupied()
    test_capture_forbidden_own_fortress_white()
    test_capture_forbidden_own_fortress_black()
    test_capture_not_in_own_fortress()
    print("\n🎉 Все тесты шатры пройдены!")