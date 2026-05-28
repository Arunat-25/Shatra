"""Реванш: смена цветов и сброс состояния."""

from backend.game_helpers import opposite_color


def swap_player_colors_for_rematch(players: dict) -> dict:
    """Логика из game_session._start_rematch — меняем цвета местами."""
    for cid in list(players.keys()):
        players[cid] = opposite_color(players[cid])
    return players


class TestRematchColorSwap:
    def test_swaps_both_players(self):
        players = {"p1": "белый", "p2": "черный"}
        swap_player_colors_for_rematch(players)
        assert players == {"p1": "черный", "p2": "белый"}

    def test_double_swap_returns_original(self):
        players = {"p1": "белый", "p2": "черный"}
        swap_player_colors_for_rematch(players)
        swap_player_colors_for_rematch(players)
        assert players == {"p1": "белый", "p2": "черный"}
