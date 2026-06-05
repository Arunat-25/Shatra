"""Self-play helpers and max-plies draw."""
from unittest.mock import patch

from backend.ai_weights import EvalWeights
from scripts.ai_selfplay_common import MAX_PLIES_DEFAULT, GameResult, play_game


def test_max_plies_declares_draw():
    weights = EvalWeights()
    with patch("scripts.ai_selfplay_common._bot_move", return_value=(45, 37)):
        with patch("scripts.ai_selfplay_common.logic.handle_event") as mock_ev:
            mock_ev.return_value.game_over = False
            mock_ev.return_value.updated_positions = {i: None for i in range(1, 63)}
            mock_ev.return_value.movers_color = "черный"
            mock_ev.return_value.draw_reason = None
            mock_ev.return_value.captured_pieces = []
            mock_ev.return_value.position_for_mandatory_capture = None
            result = play_game(weights, max_plies=5)
    assert result.outcome == "draw"
    assert result.draw_reason == "max_moves"
    assert result.plies == 5


def test_default_max_plies_is_1000():
    assert MAX_PLIES_DEFAULT == 1000
