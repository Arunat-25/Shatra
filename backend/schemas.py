from typing import TypedDict, Optional


class GameState(TypedDict, total=False):
    """Состояние игровой сессии для games[room_id]."""
    logic: object  # GameLogic instance
    board: dict[int, str | None]  # int -> piece_name
    mover: str  # "белый" or "черный"
    players: dict
    pending_batyr_captures: list[int]
    moves_made: int
    game_over: bool


class WSMessage(TypedDict, total=False):
    """Типизированное WS-сообщение от сервера к клиенту."""
    message: str
    movers_color: str
    desk: dict[str, str | None]  # ключи-строки
    game_over: bool
    winner: str
    position_for_mandatory_capture: int | None
    opportunity_pass_the_move: bool
    essential_positions: list[int]
    captured_pieces: list[int]
    captured_positions: list[int]
    status: str  # "game_started", "waiting", etc.
    time_control: int | None
    increment: int | None
    time: dict[str, float]
    type: str  # "timer_tick"


class ClientMessage(TypedDict, total=False):
    """Типизированное WS-сообщение от клиента к серверу."""
    board: dict[str, str | None]
    movers_color: str
    move_from: str | None
    move_to: str | None
    position: str | None
    position_for_mandatory_capture: int | None