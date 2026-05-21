import uuid
from datetime import datetime
from fastapi import HTTPException
from backend.models import (
    Room, RoomType, RoomInfo, CreateRoomRequest,
    CreateRoomResponse, RoomListResponse
)

rooms: dict[str, Room] = {}


def create_room(request: CreateRoomRequest) -> CreateRoomResponse:
    room_id = uuid.uuid4().hex[:8]
    now = datetime.now()
    room = Room(
        room_id=room_id,
        type=request.type,
        created_at=now
    )
    rooms[room_id] = room
    link = f"/Frontend/Board.html?room={room_id}"
    return CreateRoomResponse(room_id=room_id, link=link, type=request.type)


def list_rooms() -> RoomListResponse:
    available = []
    for room in rooms.values():
        if room.type == "quick" and not room.player2_connected and not room.game_started:
            available.append(RoomInfo(
                room_id=room.room_id,
                type=room.type,
                created_at=room.created_at
            ))
    return RoomListResponse(rooms=available)


def join_room(room_id: str) -> dict:
    room = rooms.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    if room.player2_connected:
        raise HTTPException(status_code=400, detail="Комната уже заполнена")
    if room.game_started:
        raise HTTPException(status_code=400, detail="Игра уже началась")
    # Помечаем, что P2 присоединился — P1 увидит это через polling
    room.player2_connected = True
    return {"room_id": room_id, "joined": True}


