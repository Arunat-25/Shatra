from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime
from fastapi import WebSocket

RoomType = Literal["quick", "friend", "ai"]


class Room(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    room_id: str
    type: RoomType
    created_at: datetime
    player1_connected: bool = False
    player2_connected: bool = False
    player1_ws: Optional[WebSocket] = None
    player2_ws: Optional[WebSocket] = None
    game_started: bool = False


class CreateRoomRequest(BaseModel):
    type: RoomType = "quick"


class CreateRoomResponse(BaseModel):
    room_id: str
    type: RoomType


class RoomInfo(BaseModel):
    room_id: str
    type: RoomType
    created_at: datetime


class RoomListResponse(BaseModel):
    rooms: list[RoomInfo]