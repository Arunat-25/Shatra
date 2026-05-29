"""Тесты доменных типов фигур и цветов."""

import pytest

from game_engine.domain import (
    Color,
    PieceType,
    color_from_piece_name,
    format_piece_name,
    opposite_color_str,
    parse_piece_name,
)


class TestParsePieceName:
    @pytest.mark.parametrize("name,color,ptype", [
        ("белый бий", Color.WHITE, PieceType.BIY),
        ("черный бий", Color.BLACK, PieceType.BIY),
        ("белая шатра", Color.WHITE, PieceType.SHATRA),
        ("черная шатра", Color.BLACK, PieceType.SHATRA),
        ("белый батыр", Color.WHITE, PieceType.BATYR),
        ("черный батыр", Color.BLACK, PieceType.BATYR),
    ])
    def test_parses_canonical_names(self, name, color, ptype):
        assert parse_piece_name(name) == (color, ptype)

    def test_roundtrip(self):
        for color in Color:
            for ptype in PieceType:
                name = format_piece_name(color, ptype)
                assert parse_piece_name(name) == (color, ptype)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_piece_name("")


class TestHelpers:
    def test_opposite_color(self):
        assert opposite_color_str("белый") == "черный"
        assert opposite_color_str("черный") == "белый"

    def test_color_from_piece_name(self):
        assert color_from_piece_name("белая шатра") == "белый"
