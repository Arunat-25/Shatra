"""Тесты бия"""

from game_engine.pieces.biy import Biy


# ---------- can_move ----------

def test_biy_can_move_one_cell():
    """Бий может ходить на 1 соседнюю клетку"""
    board = {i: None for i in range(1, 63)}
    board[10] = 'черный бий'
    b = Biy('черный')
    assert b.can_move(board, 10, 19), "10→19 должен быть разрешён"
    assert b.can_move(board, 10, 11), "10→11 должен быть разрешён"
    assert b.can_move(board, 10, 20), "10→20 должен быть разрешён"
    print("✅ test_biy_can_move_one_cell пройден")


def test_biy_can_move_if_empty():
    """Бий может ходить на пустую клетку (10→28 разрешён словарём)"""
    board = {i: None for i in range(1, 63)}
    board[10] = 'черный бий'
    b = Biy('черный')
    assert b.can_move(board, 10, 28), "10→28 должен быть разрешён"
    assert b.can_move(board, 10, 15), "10→15 должен быть разрешён"
    print("✅ test_biy_can_move_if_empty пройден")


def test_biy_cannot_move_occupied():
    """Бий не может ходить на занятую клетку"""
    board = {i: None for i in range(1, 63)}
    board[10] = 'черный бий'
    board[19] = 'черная шатра'
    b = Biy('черный')
    assert not b.can_move(board, 10, 19), "10→19 на занятую запрещён"
    print("✅ test_biy_cannot_move_occupied пройден")


# ---------- can_capture ----------

def test_biy_capture_enemy():
    """Бий может бить вражескую фигуру (10→19 через 13)"""
    board = {i: None for i in range(1, 63)}
    board[10] = 'черный бий'
    board[13] = 'белая шатра'
    board[19] = None
    b = Biy('черный')
    assert b.can_capture(board, 10, 19), "10→19 (через 13) должен быть True"
    print("✅ test_biy_capture_enemy пройден")


def test_biy_capture_no_enemy():
    """Бий не может бить, если нет врага между"""
    board = {i: None for i in range(1, 63)}
    board[10] = 'черный бий'
    board[19] = None
    b = Biy('черный')
    assert not b.can_capture(board, 10, 19), "10→19 без врага должен быть False"
    print("✅ test_biy_capture_no_enemy пройден")


def test_biy_capture_no_enemy():
    """Бий не может бить, если нет врага между"""
    board = {i: None for i in range(1, 63)}
    board[10] = 'черный бий'
    board[28] = None
    b = Biy('черный')
    assert not b.can_capture(board, 10, 28), "10→28 без врага должен быть False"
    print("✅ test_biy_capture_no_enemy пройден")


def test_biy_capture_target_occupied():
    """Бий не может бить, если target занята"""
    board = {i: None for i in range(1, 63)}
    board[10] = 'черный бий'
    board[13] = 'белая шатра'
    board[19] = 'черная шатра'
    b = Biy('черный')
    assert not b.can_capture(board, 10, 19), "10→19 target занята, должен быть False"
    print("✅ test_biy_capture_target_occupied пройден")


# ---------- вход в крепость ----------

def test_biy_enter_fortress_no_shatra():
    """Бий может войти в крепость, если нет своих шатр (10→7)"""
    board = {i: None for i in range(1, 63)}
    board[10] = 'черный бий'
    b = Biy('черный')
    assert b.can_move(board, 10, 7), "10→7 разрешён, в крепости нет шатр"
    print("✅ test_biy_enter_fortress_no_shatra пройден")


def test_biy_enter_fortress_with_shatra_black():
    """Чёрный бий не может войти в крепость, если там есть своя шатра"""
    board = {i: None for i in range(1, 63)}
    board[10] = 'черный бий'
    board[2] = 'черная шатра'
    b = Biy('черный')
    assert not b.can_move(board, 10, 7), "10→7 запрещён, в крепости есть шатра"
    print("✅ test_biy_enter_fortress_with_shatra_black пройден")


def test_biy_enter_fortress_with_shatra_white():
    """Белый бий не может войти в крепость, если там есть своя шатра"""
    board = {i: None for i in range(1, 63)}
    board[53] = 'белый бий'
    board[60] = 'белая шатра'
    b = Biy('белый')
    assert not b.can_move(board, 53, 54), "53→54 запрещён, в крепости есть шатра"
    print("✅ test_biy_enter_fortress_with_shatra_white пройден")


if __name__ == '__main__':
    test_biy_can_move_one_cell()
    test_biy_can_move_if_empty()
    test_biy_cannot_move_occupied()
    test_biy_capture_enemy()
    test_biy_capture_no_enemy()
    test_biy_capture_target_occupied()
    test_biy_enter_fortress_no_shatra()
    test_biy_enter_fortress_with_shatra_black()
    test_biy_enter_fortress_with_shatra_white()
    print("\n🎉 Все тесты бия пройдены!")