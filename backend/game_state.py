"""Схема состояния игры в Redis (источник правды для game:{room_id})."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_board_keys(board: dict) -> dict[int, str | None]:
    out: dict[int, str | None] = {}
    for key, value in (board or {}).items():
        out[int(key)] = value
    return out


class GameState(BaseModel):
    """Состояние партии. extra='allow' — для полей, добавленных в рантайме до миграции."""

    model_config = ConfigDict(extra="allow")

    board: dict[int, str | None]
    mover: str = "белый"
    players: dict[str, str] = Field(default_factory=dict)
    pending_batyr_captures: list[str] = Field(default_factory=list)
    moves_made: int = 0
    move_history: list[dict[str, Any]] = Field(default_factory=list)
    game_over: bool = False
    winner: Optional[str] = None
    reason: Optional[str] = None
    draw_offer_from: Optional[str] = None
    pending_mandatory_position: Optional[int] = None
    position_history: dict[str, int] = Field(default_factory=dict)
    moves_with_two_biys: int = 0
    ply: int = 0

    @field_validator("board", mode="before")
    @classmethod
    def _board_int_keys(cls, value: dict) -> dict[int, str | None]:
        return _normalize_board_keys(value)

    @classmethod
    def from_storage(cls, data: dict | None) -> Optional["GameState"]:
        if not data:
            return None
        return cls.model_validate(data)

    def to_storage(self) -> dict:
        return self.model_dump(mode="python")

    @classmethod
    def new(cls, board: dict[int, str | None]) -> "GameState":
        return cls(board=_normalize_board_keys(board))
