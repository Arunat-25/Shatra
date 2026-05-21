from fastapi import WebSocket
from game_engine.game_logic import GameLogic
from backend.room_manager import rooms
from backend.board_utils import keys_int_to_str, get_starting_board

games: dict[str, dict] = {}


class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket, player_id: int | None = None) -> bool:
        await websocket.accept()
        room = rooms.get(room_id)
        if not room:
            await websocket.close(code=1008)
            return False

        if room_id not in self.connections:
            self.connections[room_id] = []

        # Если игра уже началась — используем player_id для корректного сопоставления
        if room.game_started:
            if player_id == 1:
                room.player1_ws = websocket
                room.player1_connected = True
            elif player_id == 2:
                room.player2_ws = websocket
                room.player2_connected = True
            else:
                await websocket.close(code=1008)
                return False
            self.connections[room_id].append(websocket)
            return True

        # Если player2_connected уже true (P2 нажал "Присоединиться" через REST)
        if room.player2_connected and not room.player2_ws and not room.game_started:
            room.player2_ws = websocket
            room.player2_connected = True
            self.connections[room_id].append(websocket)
            return True

        # Первый WebSocket — P1
        if room.player1_ws is None:
            room.player1_ws = websocket
            room.player1_connected = True
            self.connections[room_id].append(websocket)
            return True

        # Второй WebSocket — P2
        if room.player2_ws is None:
            room.player2_ws = websocket
            room.player2_connected = True
            self.connections[room_id].append(websocket)
            return True

        await websocket.close(code=1008)
        return False

    async def disconnect(self, room_id: str, websocket: WebSocket):
        room = rooms.get(room_id)
        if room:
            if room.player1_ws == websocket:
                room.player1_ws = None
            if room.player2_ws == websocket:
                room.player2_ws = None

        if room_id in self.connections and websocket in self.connections[room_id]:
            self.connections[room_id].remove(websocket)
            if not self.connections[room_id]:
                self.connections.pop(room_id, None)

    async def send_to_room(self, room_id: str, data: dict):
        for ws in self.connections.get(room_id, []):
            try:
                await ws.send_json(data)
            except Exception:
                pass

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


async def handle_player2_join(room_id: str, room):
    await init_game(room_id)
    game = games[room_id]

    await manager.send_to_room(room_id, {
        "status": "game_started",
        "movers_color": game["mover"],
        "desk": keys_int_to_str(game["board"])
    })

    room.game_started = True