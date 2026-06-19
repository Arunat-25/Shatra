"""
Хитрые и неочевидные сценарии: регрессии, которые легко пропустить при рефакторинге.
"""

import pytest
from unittest.mock import AsyncMock, patch

from backend.board_utils import (
    change_position_name_from_frontend,
    keys_int_to_str,
    keys_str_to_int,
    get_starting_board,
)
from backend.game_helpers import (
    assign_player_color,
    build_move_response,
    build_move_delta_response,
    is_rejected_move,
    parse_client_event,
    resolve_creator_color,
    update_captures,
    apply_increment,
    apply_move_result,
    _norm_board_keys,
)
from game_engine.game_logic import logic
from game_engine.message_codes import MOVE_NO_PIECE, MOVE_TARGET_OCCUPIED, MOVE_WRONG_COLOR, TURN_NOW
from game_engine.models import GameEvent, GameEventResult


class TestBoardKeyNormalization:
    """Смешанные str/int ключи доски — ложное «доска изменилась» или пропуск хода."""

    def test_norm_board_treats_str_and_int_as_same_cell(self):
        a = {11: "черная шатра", "12": None}
        b = {11: "черная шатра", 12: None}
        assert _norm_board_keys(a) == _norm_board_keys(b)

    def test_keys_roundtrip_preserves_positions(self, starting_board):
        as_str = keys_int_to_str(starting_board)
        back = keys_str_to_int(as_str)
        assert back[10] == "черный бий"
        assert back[53] == "белый бий"

    def test_parse_board_with_string_cell_keys(self):
        data = {
            "board": {"11": "черная шатра", "18": None},
            "movers_color": "черный",
            "move_from": "position11",
            "move_to": "position18",
        }
        event, f, t = parse_client_event(data)
        assert event.positions[11] == "черная шатра"
        assert f == 11 and t == 18

    @pytest.mark.parametrize("raw,expected", [
        ("position0", 0),
        (0, 0),
        ("position62", 62),
    ])
    def test_position_label_parsing(self, raw, expected):
        assert change_position_name_from_frontend(raw) == expected


class TestMoveHistoryResponse:
    """Клиент не должен получать мусор в move_history."""

    def test_strips_entries_without_from_to(self, starting_board):
        game = {
            "board": starting_board,
            "move_history": [
                {"move_number": 1, "desk": keys_int_to_str(starting_board)},
                {
                    "move_number": 2,
                    "from_pos": 12,
                    "to_pos": 20,
                    "desk": keys_int_to_str(starting_board),
                },
            ],
        }
        result = GameEventResult(message_code="", movers_color="белый")
        resp = build_move_response(game, result, "черный")
        assert len(resp["move_history"]) == 1
        assert resp["move_history"][0]["from_pos"] == 12

    def test_drops_consecutive_duplicate_desks(self, starting_board):
        desk = keys_int_to_str(starting_board)
        game = {
            "board": starting_board,
            "move_history": [
                {"from_pos": 1, "to_pos": 2, "desk": desk},
                {"from_pos": 3, "to_pos": 4, "desk": desk},
                {"from_pos": 5, "to_pos": 6, "desk": {"10": "черный бий"}},
            ],
        }
        result = GameEventResult(message_code="", movers_color="белый")
        resp = build_move_response(game, result, "черный")
        assert len(resp["move_history"]) == 2
        assert resp["move_history"][0]["move_number"] == 1
        assert resp["move_history"][1]["move_number"] == 2

    def test_includes_hint_position_when_provided(self, starting_board):
        game = {"board": starting_board, "move_history": []}
        result = GameEventResult(
            message_code=TURN_NOW,
            movers_color="белый",
            essential_positions=[46, 48],
        )
        resp = build_move_response(game, result, "белый", hint_position=53)
        assert resp["hint_position"] == 53
        assert resp["essential_positions"] == [46, 48]
        assert "desk" in resp

    def test_omits_hint_position_for_normal_moves(self, starting_board):
        game = {"board": starting_board, "move_history": []}
        result = GameEventResult(message_code=TURN_NOW, movers_color="черный")
        resp = build_move_response(game, result, "белый", 53, 46)
        assert "hint_position" not in resp

    def test_clears_mandatory_capture_flag_after_turn_switch(self, starting_board):
        game = {"board": starting_board, "move_history": []}
        result = GameEventResult(
            message_code=TURN_NOW,
            movers_color="черный",
            updated_positions=starting_board,
            position_for_mandatory_capture=11,
        )
        resp = build_move_response(game, result, "белый", 45, 37)
        assert resp["position_for_mandatory_capture"] is None


class TestMoveDeltaResponse:
    """Normal move broadcasts omit full desk (Stage 5)."""

    def test_delta_omits_desk_and_history(self, starting_board):
        board = dict(starting_board)
        board[45] = None
        board[37] = "белый бий"
        game = {
            "board": board,
            "move_history": [{"from_pos": 1, "to_pos": 2, "desk": keys_int_to_str(board)}],
            "ply": 1,
        }
        result = GameEventResult(
            message_code=TURN_NOW,
            movers_color="черный",
            captured_positions=[28],
        )
        resp = build_move_delta_response(game, result, "белый", 45, 37)
        assert "desk" not in resp
        assert "move_history" not in resp
        assert resp["from_pos"] == 45
        assert resp["to_pos"] == 37
        assert resp["mover"] == "белый"
        assert resp["ply"] == 1
        assert resp["captured_positions"] == [28]


class TestUpdateCaptures:
    def test_turn_switch_clears_pending_batyr_captures(self):
        game = {"mover": "белый", "pending_batyr_captures": ["черный батыр"]}
        result = GameEventResult(movers_color="черный", updated_positions={})
        update_captures(game, result)
        assert game["pending_batyr_captures"] == []

    def test_capture_chain_stores_pending_pieces(self):
        game = {"mover": "белый", "pending_batyr_captures": []}
        result = GameEventResult(
            movers_color="белый",
            captured_pieces=["черная шатра"],
            position_for_mandatory_capture=20,
        )
        update_captures(game, result)
        assert game["pending_batyr_captures"] == ["черная шатра"]

    def test_no_mandatory_and_no_capture_clears_pending(self):
        game = {"mover": "белый", "pending_batyr_captures": ["x"]}
        result = GameEventResult(movers_color="белый")
        update_captures(game, result)
        assert game["pending_batyr_captures"] == []


class TestRejectedMoveEdgeCases:
    def test_same_board_with_error_message_is_rejected(self):
        board = {11: "черная шатра"}
        result = GameEventResult(
            message_code=MOVE_WRONG_COLOR,
            movers_color="черный",
            updated_positions=dict(board),
        )
        assert is_rejected_move(result, board, 11, 18) is True

    def test_game_over_with_unchanged_board_not_counted_as_rejected(self):
        board = {11: "черная шатра"}
        result = GameEventResult(
            message_code=TURN_NOW,
            game_over=True,
            winner_color="белый",
            updated_positions=dict(board),
        )
        assert is_rejected_move(result, board, 11, 18) is False

    def test_wrong_mover_color_from_client_should_fail_engine(self, starting_board):
        """Клиент шлёт movers_color не тому, чей ход на сервере — движок отклоняет."""
        result = logic.handle_event(
            GameEvent(
                positions=dict(starting_board),
                mover_color="черный",
                from_pos=39,
                to_pos=46,
            )
        )
        assert result.message_code == MOVE_WRONG_COLOR
        assert is_rejected_move(
            result,
            _norm_board_keys(starting_board),
            39,
            46,
        )


class TestColorAssignmentTricks:
    def test_random_preference_unknown_string_still_deterministic(self):
        a = resolve_creator_color("random", "stable-id-42")
        b = resolve_creator_color("anything-weird", "stable-id-42")
        assert a == b
        assert a in ("белый", "черный")

    def test_room_without_creator_id_joiner_uses_reserved_color(self, sample_room_data):
        sample_room_data["creator_client_id"] = None
        sample_room_data["creator_color_preference"] = "белый"
        players = {}
        color = assign_player_color(sample_room_data, "guest", players)
        assert color == "черный"

    def test_creator_reconnect_fixes_joiner_color(self, sample_room_data):
        sample_room_data["creator_color_preference"] = "черный"
        players = {"early": "черный"}
        assign_player_color(sample_room_data, "creator-1", players)
        assert players["early"] == "белый"


class TestApplyIncrement:
    @pytest.mark.asyncio
    async def test_increment_only_for_side_that_just_moved(self, sample_room_data):
        sample_room_data["increment"] = 5
        sample_room_data["timer_white"] = 100.0
        sample_room_data["timer_black"] = 100.0

        await apply_increment(sample_room_data, "белый")
        assert sample_room_data["timer_white"] == 105.0
        assert sample_room_data["timer_black"] == 100.0

    @pytest.mark.asyncio
    async def test_no_increment_without_time_control(self, sample_room_data):
        sample_room_data["time_control"] = None
        sample_room_data["increment"] = 5
        sample_room_data["timer_white"] = 100.0

        await apply_increment(sample_room_data, "белый")
        assert sample_room_data["timer_white"] == 100.0


@pytest.mark.asyncio
class TestApplyMoveResultEdgeCases:
    async def test_game_over_clears_rematch_ready_in_pvp(self, starting_board):
        game = {
            "board": dict(starting_board),
            "mover": "белый",
            "move_history": [],
        }
        result = GameEventResult(game_over=True, winner_color="белый", updated_positions=dict(starting_board))
        room = {"type": "public", "rematch_ready": ["p1", "p2"]}

        with patch("backend.game_helpers.set_game", new_callable=AsyncMock):
            with patch("backend.game_helpers.get_room", new_callable=AsyncMock, return_value=room):
                with patch("backend.game_helpers.set_room", new_callable=AsyncMock) as set_room:
                    await apply_move_result("r", game, result, "белый", 12, 20)
        set_room.assert_called_once()
        assert room["rematch_ready"] == []

    async def test_ai_game_over_does_not_touch_rematch_list(self, starting_board):
        game = {"board": dict(starting_board), "mover": "белый", "move_history": []}
        result = GameEventResult(game_over=True, winner_color="белый", updated_positions=dict(starting_board))
        room = {"type": "ai", "rematch_ready": []}

        with patch("backend.game_helpers.set_game", new_callable=AsyncMock):
            with patch("backend.game_helpers.get_room", new_callable=AsyncMock, return_value=room):
                with patch("backend.game_helpers.set_room", new_callable=AsyncMock) as set_room:
                    await apply_move_result("r", game, result, "белый", 12, 20)
        set_room.assert_not_called()


class TestEngineTrickyMoves:
    def test_cannot_move_when_not_your_turn(self, starting_board):
        board = dict(starting_board)
        result = logic.handle_event(
            GameEvent(positions=board, mover_color="черный", from_pos=12, to_pos=20)
        )
        assert result.message_code
        assert result.movers_color != "черный" or result.updated_positions == board

    def test_cannot_move_empty_square(self, starting_board):
        board = dict(starting_board)
        result = logic.handle_event(
            GameEvent(positions=board, mover_color="белый", from_pos=30, to_pos=38)
        )
        assert result.message_code == MOVE_NO_PIECE

    def test_pass_zero_zero_does_not_false_reject_as_illegal_move(self, starting_board):
        board = dict(starting_board)
        result = GameEventResult(
            message_code="",
            movers_color="черный",
            updated_positions=board,
            opportunity_pass_the_move=True,
        )
        assert is_rejected_move(result, _norm_board_keys(board), 0, 0) is False

    def test_essential_positions_hint_not_treated_as_rejected(self, starting_board):
        board = dict(starting_board)
        result = GameEventResult(
            message_code="",
            movers_color="белый",
            updated_positions=board,
            essential_positions=[53],
        )
        assert is_rejected_move(result, _norm_board_keys(board), 53, 46) is False


class TestParseClientEventValidation:
    def test_missing_board_raises(self):
        with pytest.raises(ValueError, match="missing_board"):
            parse_client_event({"movers_color": "белый"})

    def test_missing_mover_color_raises(self):
        with pytest.raises(ValueError, match="missing_mover"):
            parse_client_event({"board": {}})
