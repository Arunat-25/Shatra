from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime

RoomType = Literal["quick", "friend", "ai"]


import time


class Room(BaseModel):
    room_id: str
    type: RoomType
    created_at: datetime
    player1_connected: bool = False
    player2_connected: bool = False
    game_started: bool = False
    time_control: Optional[int] = None  # базовое время на игрока (сек), None = без таймера
    timer_player1: Optional[float] = None  # оставшееся время P1 (сек)
    timer_player2: Optional[float] = None  # оставшееся время P2 (сек)
    increment: Optional[int] = None  # добавка времени за ход (сек)
    last_tick: Optional[float] = None  # timestamp последнего тика таймера
    player1_client_id: Optional[str] = None  # UUID анонимного игрока 1
    player2_client_id: Optional[str] = None  # UUID анонимного игрока 2

    def correct_timers_after_restart(self):
        """Корректирует таймеры после рестарта сервера (Redis уцелел, in-memory тикеры умерли)."""
        if self.last_tick is not None and self.game_started:
            elapsed = time.time() - self.last_tick
            if self.timer_player1 is not None:
                self.timer_player1 = max(0, self.timer_player1 - elapsed)
            if self.timer_player2 is not None:
                self.timer_player2 = max(0, self.timer_player2 - elapsed)


class CreateRoomRequest(BaseModel):
    type: RoomType = "quick"
    time_control: Optional[int] = None  # секунд на игрока
    increment: Optional[int] = None  # добавка времени за ход (сек)


class CreateRoomResponse(BaseModel):
    room_id: str
    type: RoomType


class RoomInfo(BaseModel):
    room_id: str
    type: RoomType
    created_at: datetime


class RoomListResponse(BaseModel):
    rooms: list[RoomInfo]