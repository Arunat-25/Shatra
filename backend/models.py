import time
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

RoomType = Literal["public", "private", "ai"]


class Room(BaseModel):
    room_id: str
    type: RoomType
    created_at: datetime
    game_started: bool = False
    time_control: Optional[int] = None  # базовое время на игрока (сек), None = без таймера
    timer_white: Optional[float] = None  # оставшееся время белых (сек)
    timer_black: Optional[float] = None  # оставшееся время чёрных (сек)
    increment: Optional[int] = None  # добавка времени за ход (сек)
    last_tick: Optional[float] = None  # timestamp последнего тика таймера
    players: dict[str, str] = {}  # client_id → "белый"/"черный"
    creator_client_id: Optional[str] = None  # кто создал комнату
    creator_color_preference: str = "random"  # "белый" | "черный" | "random"

    def correct_timers_after_restart(self):
        """Корректирует таймеры после рестарта сервера (Redis уцелел, in-memory тикеры умерли)."""
        if self.last_tick is not None and self.game_started:
            elapsed = time.time() - self.last_tick
            if self.timer_white is not None:
                self.timer_white = max(0, self.timer_white - elapsed)
            if self.timer_black is not None:
                self.timer_black = max(0, self.timer_black - elapsed)


ColorPreference = Literal["белый", "черный", "random"]


class CreateRoomRequest(BaseModel):
    type: RoomType = "public"
    time_control: Optional[int] = None  # секунд на игрока
    increment: Optional[int] = None  # добавка времени за ход (сек)
    color_preference: ColorPreference = "random"
    creator_client_id: Optional[str] = None


class CreateRoomResponse(BaseModel):
    room_id: str
    type: RoomType


class RoomInfo(BaseModel):
    room_id: str
    type: RoomType
    created_at: datetime
    time_control: Optional[int] = None
    increment: int = 0


class RoomListResponse(BaseModel):
    rooms: list[RoomInfo]