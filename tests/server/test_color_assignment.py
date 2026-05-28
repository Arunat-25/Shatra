"""Назначение цветов при создании комнаты и подключении по WS."""

import pytest

from backend.game_helpers import (
    assign_player_color,
    get_ai_color,
    opposite_color,
    resolve_creator_color,
)


class TestOppositeColor:
    def test_white_to_black(self):
        assert opposite_color("белый") == "черный"

    def test_black_to_white(self):
        assert opposite_color("черный") == "белый"


class TestResolveCreatorColor:
    def test_preference_white(self):
        assert resolve_creator_color("белый", "any-room") == "белый"

    def test_preference_black(self):
        assert resolve_creator_color("черный", "any-room") == "черный"

    def test_random_is_deterministic_per_room(self):
        a = resolve_creator_color("random", "room-aaa")
        b = resolve_creator_color("random", "room-aaa")
        c = resolve_creator_color("random", "room-bbb")
        assert a == b
        assert a in ("белый", "черный")
        assert c in ("белый", "черный")


class TestAssignPlayerColor:
    def test_creator_joins_first_gets_preferred_white(self, sample_room_data):
        players = {}
        color = assign_player_color(sample_room_data, "creator-1", players)
        assert color == "белый"

    def test_creator_prefers_black(self, sample_room_data):
        sample_room_data["creator_color_preference"] = "черный"
        players = {}
        color = assign_player_color(sample_room_data, "creator-1", players)
        assert color == "черный"

    def test_joiner_gets_opposite_of_creator(self, sample_room_data):
        players = {"creator-1": "белый"}
        color = assign_player_color(sample_room_data, "joiner-2", players)
        assert color == "черный"

    def test_creator_joins_second_fixes_early_joiner(self, sample_room_data):
        """Создатель за чёрных: ранний joiner мог получить чёрный — при входе создателя цвета правятся."""
        sample_room_data["creator_color_preference"] = "черный"
        players = {"early-joiner": "черный"}
        color = assign_player_color(sample_room_data, "creator-1", players)
        assert color == "черный"
        assert players["early-joiner"] == "белый"

    def test_joiner_before_creator_gets_opposite_of_reserved_creator_color(self, sample_room_data):
        sample_room_data["creator_color_preference"] = "random"
        reserved = resolve_creator_color("random", sample_room_data["room_id"])
        players = {}
        joiner_color = assign_player_color(sample_room_data, "joiner-x", players)
        assert joiner_color == opposite_color(reserved)


class TestAiColor:
    def test_human_white_means_ai_black(self):
        assert get_ai_color({"players": {"p1": "белый"}}) == "черный"

    def test_human_black_means_ai_white(self):
        assert get_ai_color({"players": {"p1": "черный"}}) == "белый"

    def test_empty_players_defaults_black_ai(self):
        assert get_ai_color({"players": {}}) == "черный"
