"""Типизированный домен: цвет и тип фигуры.

Строки вида «белый бий» остаются форматом хранения/WS/Redis;
парсинг и сборка — только через эти функции.
"""

from __future__ import annotations

from enum import Enum


class Color(str, Enum):
    WHITE = "белый"
    BLACK = "черный"

    @classmethod
    def from_str(cls, value: str) -> Color:
        if value == cls.WHITE.value:
            return cls.WHITE
        if value == cls.BLACK.value:
            return cls.BLACK
        raise ValueError(f"Неизвестный цвет: {value!r}")

    def opposite(self) -> Color:
        return Color.BLACK if self is Color.WHITE else Color.WHITE


class PieceType(str, Enum):
    BIY = "бий"
    SHATRA = "шатра"
    BATYR = "батыр"

    @classmethod
    def from_str(cls, value: str) -> PieceType:
        for member in cls:
            if member.value in value:
                return member
        raise ValueError(f"Неизвестный тип фигуры: {value!r}")


def parse_piece_name(name: str) -> tuple[Color, PieceType]:
    """«белая шатра» → (Color.WHITE, PieceType.SHATRA)."""
    if not name:
        raise ValueError("Пустое имя фигуры")
    color = Color.WHITE if "бел" in name else Color.BLACK
    piece_type = PieceType.from_str(name)
    return color, piece_type


def format_piece_name(color: Color, piece_type: PieceType) -> str:
    """Собирает каноническое русское имя для доски."""
    if piece_type is PieceType.SHATRA:
        adj = "белая" if color is Color.WHITE else "черная"
        return f"{adj} шатра"
    adj = "белый" if color is Color.WHITE else "черный"
    return f"{adj} {piece_type.value}"


def color_from_piece_name(name: str) -> str:
    """Цвет из имени фигуры (для совместимости с существующим API)."""
    return parse_piece_name(name)[0].value


def opposite_color_str(color: str) -> str:
    return Color.from_str(color).opposite().value
