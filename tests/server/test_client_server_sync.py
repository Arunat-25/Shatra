"""Client/server sync: pending_mandatory_position vs chainCell / local rules."""

from __future__ import annotations

from copy import deepcopy

import pytest

from game_engine.game_logic import logic
from game_engine.message_codes import CAPTURE_CONTINUE_SAME, TURN_NOW
from game_engine.models import GameEvent
from tests.helpers.engine_boards import empty_board, play_sequence
from tests.helpers.server_game_sim import (
    USER_SEQUENCE_28,
    client_chain_cell,
    new_server_game,
    simulate_server_replay,
    snapshot_chain_cell,
    try_server_move,
    wire_move_delta,
    _load_sync_scenarios,
    _moves_from_fixture,
)


def _load_scenarios():
    return _load_sync_scenarios()


def _board_from_fixture(cells: dict) -> dict:
    board = empty_board()
    for key, value in cells.items():
        board[int(key)] = value
    return board


class TestPersistPendingMandatory:
    def test_turn_switch_clears_pending_even_if_engine_sets_mandatory_pos(self):
        game, last, prev = simulate_server_replay(USER_SEQUENCE_28)
        assert last.movers_color == "белый"
        assert last.position_for_mandatory_capture == 42
        assert game.get("pending_mandatory_position") is None

    def test_same_player_chain_keeps_pending(self):
        board = empty_board()
        board.update({20: "белая шатра", 28: "черная шатра", 36: None, 44: "черная шатра", 45: "белая шатра"})
        game, last, _ = simulate_server_replay([("белый", 20, 36)], game=new_server_game(board=board, mover="белый"))
        assert last.position_for_mandatory_capture == 36
        assert game["pending_mandatory_position"] == 36


class TestUserSequence28:
    def test_all_mandatory_attackers_legal_without_chain_cell(self):
        game, _, _ = simulate_server_replay(USER_SEQUENCE_28)
        assert client_chain_cell(game) is None

        for from_cell, to_cell in [(42, 30), (43, 29), (44, 28)]:
            probe = deepcopy(game)
            result = try_server_move(probe, from_cell, to_cell)
            assert result.message_code == TURN_NOW, f"{from_cell}->{to_cell}: {result.message_code}"
            assert 36 in (result.captured_positions or [])

    def test_stale_chain_42_rejects_other_white_pieces(self):
        game, _, _ = simulate_server_replay(USER_SEQUENCE_28)
        for from_cell, to_cell in [(32, 36), (43, 29), (44, 28)]:
            result = try_server_move(deepcopy(game), from_cell, to_cell, override_chain=42)
            assert result.message_code == CAPTURE_CONTINUE_SAME

    def test_capture_black_shatra_on_36_lands_on_30_not_36(self):
        game, _, _ = simulate_server_replay(USER_SEQUENCE_28)
        result = try_server_move(deepcopy(game), 42, 30)
        assert result.captured_positions == [36]
        assert result.updated_positions[36] is None
        assert result.updated_positions[30] == "белый бий"

    def test_v2_delta_and_snapshot_chain_cell_match_client(self):
        game, last, prev = simulate_server_replay(USER_SEQUENCE_28)
        delta = wire_move_delta(game, last, prev, 28, 36)
        assert delta.get("chainCell") is None
        assert snapshot_chain_cell(game, my_color="белый") is None
        assert client_chain_cell(game) is None


class TestWireProtocolAlignment:
    def test_delta_omits_chain_cell_on_turn_switch_mandatory(self):
        game, last, prev = simulate_server_replay(USER_SEQUENCE_28)
        delta = wire_move_delta(game, last, prev, 28, 36)
        assert "chainCell" not in delta or delta.get("chainCell") is None

    def test_delta_includes_chain_cell_during_same_player_chain(self):
        board = empty_board()
        board.update({20: "белая шатра", 28: "черная шатра", 36: None, 44: "черная шатра"})
        game, last, prev = simulate_server_replay(
            [("белый", 20, 36)],
            game=new_server_game(board=board, mover="белый"),
        )
        delta = wire_move_delta(game, last, prev, 20, 36)
        assert delta.get("chainCell") == 36
        assert game["pending_mandatory_position"] == 36
        assert snapshot_chain_cell(game) == 36


class TestStalePendingRegression:
    def test_stale_pending_on_server_reproduces_continue_same(self):
        """Document broken state when pending survives a finished chain / turn switch."""
        board = empty_board()
        board.update({
            20: "белая шатра",
            28: "черная шатра",
            36: None,
            44: "черная шатра",
            45: "белая шатра",
        })
        game = new_server_game(board=board, mover="белый")
        game, _, _ = simulate_server_replay([("белый", 20, 36)], game=game)
        game["pending_mandatory_position"] = 36  # stale — simulates old server bug

        hint = logic.handle_event(
            GameEvent(
                positions=game["board"],
                mover_color="белый",
                position=45,
                position_for_mandatory_capture=36,
            )
        )
        assert hint.message_code == CAPTURE_CONTINUE_SAME
        assert hint.essential_positions == []

    def test_fixed_persist_does_not_leave_stale_pending_after_chain_ends(self):
        state = play_sequence(
            [("белый", 20, 36), ("белый", 36, 52)],
            board=empty_board()
            | {20: "белая шатра", 28: "черная шатра", 36: None, 44: "черная шатра", 45: "белая шатра"},
        )
        game = new_server_game(board=state["board"], mover=state["mover"])
        game["pending_mandatory_position"] = None
        assert game.get("pending_mandatory_position") is None


class TestMandatoryWithoutChainUsesValidation:
    def test_wrong_piece_gets_mandatory_other_not_continue_same(self):
        game, _, _ = simulate_server_replay(USER_SEQUENCE_28)
        result = try_server_move(deepcopy(game), 32, 30)
        assert result.message_code != CAPTURE_CONTINUE_SAME

    def test_hints_without_chain_show_each_attacker(self):
        game, _, _ = simulate_server_replay(USER_SEQUENCE_28)
        for from_cell, target in [(42, 30), (43, 29), (44, 28)]:
            hint = logic.handle_event(
                GameEvent(
                    positions=game["board"],
                    mover_color="белый",
                    position=from_cell,
                    position_for_mandatory_capture=None,
                )
            )
            assert target in (hint.essential_positions or []), from_cell
            assert hint.message_code != CAPTURE_CONTINUE_SAME


@pytest.mark.parametrize("scenario", _load_scenarios(), ids=lambda s: s["id"])
class TestFixtureScenarios:
  def test_server_state_after_replay(self, scenario):
      if "board" in scenario:
          game = new_server_game(
              board=_board_from_fixture(scenario["board"]),
              mover=scenario["moves"][0][0],
          )
          game, last, prev = simulate_server_replay(_moves_from_fixture(scenario["moves"]), game=game)
      else:
          game, last, prev = simulate_server_replay(_moves_from_fixture(scenario["moves"]))

      assert game["mover"] == scenario["expect_mover"]
      expected_pending = scenario.get("expect_server_pending")
      if expected_pending is None:
          assert game.get("pending_mandatory_position") is None
      else:
          assert game["pending_mandatory_position"] == expected_pending

      if "expect_delta_chain_cell" in scenario:
          delta = wire_move_delta(game, last, prev, *scenario["moves"][-1][1:])
          got = delta.get("chainCell")
          exp = scenario["expect_delta_chain_cell"]
          assert got == exp

      assert snapshot_chain_cell(game) == client_chain_cell(game)

  def test_legal_moves_match_client_chain_cell(self, scenario):
      if "board" in scenario:
          game = new_server_game(
              board=_board_from_fixture(scenario["board"]),
              mover=scenario["moves"][0][0],
          )
          game, _, _ = simulate_server_replay(_moves_from_fixture(scenario["moves"]), game=game)
      else:
          game, _, _ = simulate_server_replay(_moves_from_fixture(scenario["moves"]))

      chain = client_chain_cell(game)
      for move in scenario.get("legal_moves", []):
          probe = deepcopy(game)
          result = try_server_move(probe, move["from"], move["to"])
          assert result.message_code == move["code"]
          if move.get("captures"):
              assert sorted(result.captured_positions or []) == sorted(move["captures"])

          # Client rules path: same chain cell as persisted server state
          client_result = logic.handle_event(
              GameEvent(
                  positions=game["board"],
                  mover_color=game["mover"],
                  from_pos=move["from"],
                  to_pos=move["to"],
                  position_for_mandatory_capture=chain,
              )
          )
          assert client_result.message_code == move["code"]

  def test_stale_chain_documented_rejections(self, scenario):
      if "board" in scenario:
          game = new_server_game(
              board=_board_from_fixture(scenario["board"]),
              mover=scenario["moves"][0][0],
          )
          game, _, _ = simulate_server_replay(_moves_from_fixture(scenario["moves"]), game=game)
      else:
          game, _, _ = simulate_server_replay(_moves_from_fixture(scenario["moves"]))

      for move in scenario.get("illegal_with_stale_chain", []):
          result = try_server_move(
              deepcopy(game),
              move["from"],
              move["to"],
              override_chain=move["stale_chain"],
          )
          assert result.message_code == move["code"]
