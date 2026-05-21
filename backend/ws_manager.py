import asyncio
from fastapi import WebSocket
from game_engine.game_logic import GameLogic
from backend.models import Room
from backend.room_manager import rooms
from backend.board_utils import board_to_json, get_starting_board

games: dict[str, dict] = {}


class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket) -> bool:
        await websocket.accept()

        room = rooms.get(room_id)
        if not room:
            await websocket.close(code=1008)
            return False

        if room_id not in self.connections:
            self.connections[room_id] = []

        if not room.player1_connected:
            room.player1_connected = True
            room.player1_ws = websocket
            self.connections[room_id].append(websocket)
            return True

        if not room.player2_connected:
            room.player2_connected = True
            room.player2_ws = websocket
            self.connections[room_id].append(websocket)
            return True

        await websocket.close(code=1008)
        return False

    async def disconnect(self, room_id: str, websocket: WebSocket):
        room = rooms.get(room_id)
        if room:
            if room.player1_ws == websocket:
                room.player1_connected = False
                room.player1_ws = None
            elif room.player2_ws == websocket:
                room.player2_connected = False
                room.player2_ws = None

        if room_id in self.connections and websocket in self.connections[room_id]:
            self.connections[room_id].remove(websocket)
            if not self.connections[room_id]:
                self.connections.pop(room_id, None)
                games.pop(room_id, None)
                rooms.pop(room_id, None)

    async def send_to_room(self, room_id: str, data: dict):
        for ws in self.connections.get(room_id, []):
            await ws.send_json(data)

    async def send_to_player(self, websocket: WebSocket, data: dict):
        await websocket.send_json(data)


manager = ConnectionManager()


async def init_game(room_id: str):
    start_board = get_starting_board()
    games[room_id] = {
        "logic": GameLogic(),
        "board": start_board,
        "mover": "белый",
        "players": {},
        "pending_batyr_captures": []
    }


async def handle_player1_waiting(room_id: str, websocket: WebSocket, room: Room):
    await manager.send_to_player(websocket, {
        "status": "waiting",
        "link": room_id
    })
    try:
        while not room.player2_connected:
            await asyncio.sleep(0.5)
    except Exception:
        await manager.disconnect(room_id, websocket)
        return

    game = games[room_id]
    await manager.send_to_player(room.player1_ws, {
        "players_color": "белый",
        "movers_color": game["mover"],
        "desk": board_to_json(game["board"])
    })
    await manager.send_to_player(room.player2_ws, {
        "players_color": "черный",
        "movers_color": game["mover"],
        "desk": board_to_json(game["board"])
    })
    room.game_started = True


async def handle_player2_join(room_id: str, room: Room):
    await init_game(room_id)
    game = games[room_id]
    await manager.send_to_player(room.player1_ws, {
        "players_color": "белый",
        "movers_color": game["mover"],
        "desk": board_to_json(game["board"])
    })
    await manager.send_to_player(room.player2_ws, {
        "players_color": "черный",
        "movers_color": game["mover"],
        "desk": board_to_json(game["board"])
    })
    room.game_started = True