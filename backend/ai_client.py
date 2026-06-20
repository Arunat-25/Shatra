"""AI turn computation: gRPC shatra-ai microservice or in-process Python fallback."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import grpc

from backend.config import settings
from backend.observability.metrics import (
    record_ai_grpc_fallback,
    record_ai_grpc_latency,
    record_ai_shadow_mismatch,
)
from game_engine.game_logic import logic
from game_engine.models import GameEvent, GameEventResult

logger = logging.getLogger(__name__)

_grpc_channel: grpc.aio.Channel | None = None
_grpc_stub: Any = None


@dataclass(frozen=True)
class AiTurnOutcome:
    """Search + apply result for one AI ply."""

    result: GameEventResult
    from_pos: int
    to_pos: int
    engine: str  # "python" | "grpc"


def _normalize_board(board: dict) -> dict[int, str | None]:
    return {int(k): v for k, v in board.items()}


def _build_game_event(
    board: dict,
    ai_color: str,
    from_cell: int,
    to_cell: int,
    pending_mandatory: int | None,
) -> GameEvent:
    return GameEvent(
        positions=board,
        mover_color=ai_color,
        from_pos=from_cell,
        to_pos=to_cell,
        position_for_mandatory_capture=pending_mandatory,
    )


async def _get_grpc_stub():
    global _grpc_channel, _grpc_stub
    if _grpc_stub is not None:
        return _grpc_stub
    from backend.proto.shatra.ai.v1 import ai_pb2_grpc

    target = (settings.ai_service_url or "shatra-ai:50051").strip()
    _grpc_channel = grpc.aio.insecure_channel(target)
    _grpc_stub = ai_pb2_grpc.AiServiceStub(_grpc_channel)
    return _grpc_stub


def _proto_to_game_event_result(msg, from_pos: int, to_pos: int) -> GameEventResult:
    return GameEventResult(
        message_code=msg.message_code or "",
        movers_color=msg.movers_color or None,
        game_over=bool(msg.game_over),
        winner_color=msg.winner_color or None,
        updated_positions=_normalize_board(dict(msg.updated_positions)) if msg.updated_positions else None,
        captured_positions=list(msg.captured_positions),
        captured_pieces=list(msg.captured_pieces),
        position_for_mandatory_capture=(
            msg.position_for_mandatory_capture
            if msg.HasField("position_for_mandatory_capture")
            else None
        ),
        opportunity_pass_the_move=bool(msg.opportunity_pass_the_move),
    )


def _build_grpc_request(game: dict, ai_color: str) -> Any:
    from backend.proto.shatra.ai.v1 import ai_pb2

    board = _normalize_board(game.get("board") or {})
    req = ai_pb2.ComputeAiTurnRequest(
        board=board,
        mover_color=ai_color,
        depth=settings.ai_search_depth,
        time_ms=settings.ai_move_time_ms,
        pending_batyr_captures=list(game.get("pending_batyr_captures") or []),
        moves_with_two_biys=int(game.get("moves_with_two_biys") or 0),
    )
    pending = game.get("pending_mandatory_position")
    if pending is not None:
        req.pending_mandatory_position = int(pending)
    for key, count in (game.get("position_history") or {}).items():
        req.position_history[str(key)] = int(count)
    return req


async def _compute_grpc_turn(game: dict, ai_color: str) -> AiTurnOutcome | None:
    stub = await _get_grpc_stub()
    req = _build_grpc_request(game, ai_color)
    timeout = max(0.05, settings.ai_grpc_timeout_ms / 1000.0)
    started = time.perf_counter()
    try:
        resp = await stub.ComputeAiTurn(req, timeout=timeout)
    except grpc.aio.AioRpcError as exc:
        code = exc.code()
        if code == grpc.StatusCode.NOT_FOUND:
            return None
        if code in (
            grpc.StatusCode.UNAVAILABLE,
            grpc.StatusCode.DEADLINE_EXCEEDED,
            grpc.StatusCode.UNIMPLEMENTED,
            grpc.StatusCode.FAILED_PRECONDITION,
            grpc.StatusCode.INTERNAL,
        ):
            logger.warning("AI gRPC failed (%s), falling back to python", code)
            record_ai_grpc_fallback(code.name.lower())
            return await _compute_python_turn(game, ai_color)
        raise

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    record_ai_grpc_latency(elapsed_ms)

    if not resp.HasField("result"):
        return None

    move = resp.result
    outcome = AiTurnOutcome(
        result=_proto_to_game_event_result(move, move.from_pos, move.to_pos),
        from_pos=int(move.from_pos),
        to_pos=int(move.to_pos),
        engine="grpc",
    )
    if settings.ai_shadow_verify:
        await _shadow_verify_turn(game, ai_color, outcome)
    return outcome


async def _compute_python_turn(game: dict, ai_color: str) -> AiTurnOutcome | None:
    from backend.ai_trained import get_best_move as get_ai_move

    board = _normalize_board(game.get("board") or {})
    position_history = game.setdefault("position_history", {})
    loop = asyncio.get_running_loop()
    move = await loop.run_in_executor(
        None,
        lambda: get_ai_move(
            board,
            ai_color,
            settings.ai_search_depth,
            game.get("pending_batyr_captures"),
            game.get("pending_mandatory_position"),
            position_history,
        ),
    )
    if move is None:
        return None

    from_cell, to_cell = move
    result = logic.handle_event(
        _build_game_event(
            board,
            ai_color,
            from_cell,
            to_cell,
            game.get("pending_mandatory_position"),
        ),
        batyr_captured_this_turn=game.get("pending_batyr_captures"),
        position_history=position_history,
    )
    return AiTurnOutcome(result=result, from_pos=from_cell, to_pos=to_cell, engine="python")


async def _shadow_verify_turn(game: dict, ai_color: str, grpc_outcome: AiTurnOutcome) -> None:
    """Staging-only: compare gRPC apply with Python game_engine."""
    py = await _compute_python_turn(game, ai_color)
    if py is None:
        record_ai_shadow_mismatch("python_no_move")
        return
    g, p = grpc_outcome.result, py.result
    if g.updated_positions != p.updated_positions or g.movers_color != p.movers_color:
        logger.warning(
            "AI shadow mismatch: grpc %s->%s desk=%s mover=%s vs python desk=%s mover=%s",
            grpc_outcome.from_pos,
            grpc_outcome.to_pos,
            g.updated_positions,
            g.movers_color,
            p.updated_positions,
            p.movers_color,
        )
        record_ai_shadow_mismatch("desk_or_mover")


async def compute_ai_turn_async(game: dict, ai_color: str) -> AiTurnOutcome | None:
    """Compute one AI ply (search + apply). Uses grpc when configured, else python."""
    engine = (settings.ai_engine or "python").strip().lower()
    if engine == "grpc":
        return await _compute_grpc_turn(game, ai_color)
    return await _compute_python_turn(game, ai_color)


async def close_ai_grpc() -> None:
    global _grpc_channel, _grpc_stub
    if _grpc_channel is not None:
        await _grpc_channel.close()
    _grpc_channel = None
    _grpc_stub = None
