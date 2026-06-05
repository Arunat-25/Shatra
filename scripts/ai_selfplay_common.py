"""Shared self-play loop for AI training."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from backend.ai import get_best_move as easy_move
from backend.ai_trained import get_best_move as strong_move
from backend.ai_weights import EvalWeights, use_weights
from backend.board_utils import get_starting_board
from game_engine.board import Board
from game_engine.endgame import _only_two_biys_left
from game_engine.game_logic import logic
from game_engine.models import GameEvent

MAX_PLIES_DEFAULT = 1000
GameOutcome = Literal["white", "black", "draw"]


@dataclass
class GameResult:
    outcome: GameOutcome
    plies: int
    draw_reason: Optional[str] = None


def _bot_move(
    board: dict,
    color: str,
    *,
    strong: bool,
    weights: EvalWeights | None,
    depth: int,
    pending_batyr: list | None,
    chain_cell: int | None,
):
    if strong and weights is not None:
        with use_weights(weights):
            return strong_move(
                board,
                color,
                depth=depth,
                batyr_captured_this_turn=pending_batyr,
                chain_capture_cell=chain_cell,
            )
    return easy_move(
        board,
        color,
        depth=depth,
        batyr_captured_this_turn=pending_batyr,
        chain_capture_cell=chain_cell,
    )


def play_game(
    candidate_weights: EvalWeights,
    *,
    candidate_color: str = "белый",
    max_plies: int = MAX_PLIES_DEFAULT,
    easy_depth: int = 3,
    strong_depth: int = 5,
    candidate_starts: bool = True,
) -> GameResult:
    """
    Candidate (strong + weights) vs baseline (easy, default weights).
    candidate_color: which color the candidate plays.
    """
    board = get_starting_board()
    mover = "белый" if candidate_starts else "черный"
    position_history: dict = {}
    moves_with_two_biys = 0
    pending_batyr: list = []
    chain_cell: int | None = None
    plies = 0

    def candidate_plays(color: str) -> bool:
        return color == candidate_color

    while plies < max_plies:
        is_candidate = candidate_plays(mover)
        move = _bot_move(
            board,
            mover,
            strong=is_candidate,
            weights=candidate_weights if is_candidate else None,
            depth=strong_depth if is_candidate else easy_depth,
            pending_batyr=pending_batyr or None,
            chain_cell=chain_cell,
        )
        if move is None:
            winner = "черный" if mover == "белый" else "белый"
            outcome: GameOutcome = "white" if winner == "белый" else "black"
            return GameResult(outcome=outcome, plies=plies, draw_reason="no_legal_move")

        from_cell, to_cell = move
        result = logic.handle_event(
            GameEvent(
                positions=board,
                mover_color=mover,
                from_pos=from_cell,
                to_pos=to_cell,
                position_for_mandatory_capture=chain_cell,
            ),
            batyr_captured_this_turn=pending_batyr,
            position_history=position_history,
            moves_with_two_biys=moves_with_two_biys,
        )
        plies += 1

        if result.game_over:
            if result.winner_color:
                outcome = "white" if result.winner_color == "белый" else "black"
            else:
                outcome = "draw"
            return GameResult(
                outcome=outcome,
                plies=plies,
                draw_reason=result.draw_reason,
            )

        if not result.updated_positions:
            return GameResult(outcome="draw", plies=plies, draw_reason="stale_move")

        board = result.updated_positions
        if result.draw_reason:
            return GameResult(outcome="draw", plies=plies, draw_reason=result.draw_reason)

        if _only_two_biys_left(Board(board)):
            moves_with_two_biys += 1
        else:
            moves_with_two_biys = 0

        pending_batyr = list(result.captured_pieces or [])
        chain_cell = result.position_for_mandatory_capture
        if result.movers_color:
            mover = result.movers_color
        else:
            mover = "черный" if mover == "белый" else "белый"

    return GameResult(outcome="draw", plies=plies, draw_reason="max_moves")


def candidate_score(result: GameResult, candidate_color: str) -> float:
    if result.outcome == "draw":
        return 0.5
    if result.outcome == "white":
        return 1.0 if candidate_color == "белый" else 0.0
    return 1.0 if candidate_color == "черный" else 0.0
