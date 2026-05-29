"""Устаревшие TypedDict-заглушки WS. Актуальная схема игры — backend.game_state.GameState."""

from typing import TypedDict, Optional

from backend.game_state import GameState  # noqa: F401 — re-export


class WSMessage(TypedDict, total=False):
    """WS-сообщение от сервера к клиенту."""
    message: str
    movers_color: str
    desk: dict[str, str | None]
    game_over: bool
    winner: str
    position_for_mandatory_capture: int | None
    opportunity_pass_the_move: bool
    essential_positions: list[int]
    captured_pieces: list[int]
    captured_positions: list[int]
    status: str
    time_control: int | None
    increment: int | None
    time: dict[str, float]
    type: str


class ClientMessage(TypedDict, total=False):
    """WS-сообщение от клиента к серверу."""
    board: dict[str, str | None]
    movers_color: str
    move_from: str | None
    move_to: str | None
    position: str | None
    position_for_mandatory_capture: int | None
    type: str
