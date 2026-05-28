"""Тесты базового класса Piece"""

from game_engine.pieces.base import Piece
from game_engine.pieces.shatra import Shatra
from game_engine.pieces.biy import Biy
from game_engine.pieces.batyr import Batyr


def test_capture_own_piece_shatra():
    """Нельзя бить свою фигуру (шатра бьёт шатру)"""
    board = {20: 'белая шатра', 28: 'белая шатра', 36: None}
    shatra = Shatra('белый')
    result = shatra.can_capture(board, 20, 36)
    assert not result, f"Ожидался False, получен {result}"


def test_capture_own_piece_biy():
    """Нельзя бить свою фигуру (бий бьёт бия)"""
    board = {10: 'черный бий', 19: 'черный бий', 28: None}
    biy = Biy('черный')
    result = biy.can_capture(board, 10, 28)
    assert not result, f"Ожидался False, получен {result}"


def test_capture_own_piece_batyr():
    """Нельзя бить свою фигуру (батыр бьёт батыра)"""
    board = {20: 'белый батыр', 28: 'белый батыр', 36: None}
    batyr = Batyr('белый')
    result = batyr.can_capture(board, 20, 36)
    assert not result, f"Ожидался False, получен {result}"


def test_capture_enemy_piece():
    """Можно бить вражескую фигуру"""
    board = {20: 'белая шатра', 28: 'черная шатра', 36: None}
    shatra = Shatra('белый')
    result = shatra.can_capture(board, 20, 36)
    assert result, f"Ожидался True, получен {result}"


def test_get_color():
    """get_color возвращает правильный цвет"""
    s = Shatra('белый')
    assert s.get_color() == 'белый'
    b = Biy('черный')
    assert b.get_color() == 'черный'
    k = Batyr('белый')
    assert k.get_color() == 'белый'


def test_get_type():
    """get_type возвращает правильный тип фигуры"""
    assert Shatra('белый').get_type() == 'шатра'
    assert Biy('черный').get_type() == 'бий'
    assert Batyr('белый').get_type() == 'батыр'