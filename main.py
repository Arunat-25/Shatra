from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uuid

from game_engine.models import GameEvent, GameEventResult
from game_engine.game_logic import GameLogic

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def board_to_json(board_dict: dict) -> dict:
    return {str(k): v for k, v in board_dict.items()}


def boards_keys_to_int(board: dict) -> dict:
    return {int(k) if isinstance(k, str) else k: v for k, v in board.items()}


def change_position_name_from_frontend(position: str | int) -> int:
    if isinstance(position, int):
        return position
    if isinstance(position, str):
        return int(position.replace("position", ""))
    return int(position)


def get_starting_board():
    board = {}
    for i in range(1, 10): board[i] = "черная шатра"
    board[10] = "черный бий"
    for i in range(11, 25): board[i] = "черная шатра"
    board[25] = "черный батыр"
    
    for i in range(39, 53): board[i] = "белая шатра"
    board[53] = "белый бий"
    for i in range(54, 63): board[i] = "белая шатра"
    board[38] = "белый батыр"
    
    for i in range(27, 38): board[i] = None
    return board


games: dict[str, dict] = {}


class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket) -> bool:
        if room_id not in self.rooms:
            self.rooms[room_id] = []
            start_board = get_starting_board()
            games[room_id] = {
                "logic": GameLogic(),
                "board": start_board, 
                "mover": "белый",
                "players": {}
            }
        if len(self.rooms[room_id]) < 2:
            await websocket.accept()
            self.rooms[room_id].append(websocket)
            return True
        return False

    async def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.rooms and websocket in self.rooms[room_id]:
            self.rooms[room_id].remove(websocket)
            if not self.rooms[room_id]:
                self.rooms.pop(room_id, None)
                games.pop(room_id, None)

    async def send_to_room(self, room_id: str, data: dict):
        for ws in self.rooms.get(room_id, []):
            await ws.send_json(data)


manager = ConnectionManager()


@app.get("/")
async def get_room_link():
    room_id = uuid.uuid4().hex[:8]
    return {"room_link": f"ws://localhost:8000/ws/{room_id}/"}


@app.websocket("/ws/{room_id}/")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    if not await manager.connect(room_id, websocket):
        await websocket.close(code=1008)
        return

    game = games[room_id]
    player_index = len(game["players"])
    my_color = "белый" if player_index == 0 else "черный"
    game["players"][websocket] = my_color

    await websocket.send_json({
        "players_color": my_color,
        "movers_color": game["mover"],
        "desk": game["board"]
    })

    try:
        while True:
            data = await websocket.receive_json()

            event = GameEvent(
                positions=boards_keys_to_int(data["board"]),
                mover_color=data["movers_color"],
                from_pos=change_position_name_from_frontend(data["move_from"]) if data.get("move_from") else None,
                to_pos=change_position_name_from_frontend(data["move_to"]) if data.get("move_to") else None,
                position=change_position_name_from_frontend(data["position"]) if data.get("position") else None,
                position_for_mandatory_capture=data.get("position_for_mandatory_capture")
            )

            result: GameEventResult = game["logic"].handle_event(event)

            if result.updated_positions:
                game["board"] = result.updated_positions
            if result.movers_color:
                game["mover"] = result.movers_color

            response = {
                "message": result.message,
                "movers_color": result.movers_color,
                "desk": board_to_json(game["board"]),
                "game_over": result.game_over,
                "winner": result.winner,
                "position_for_mandatory_capture": None,
                "opportunity_pass_the_move": result.opportunity_pass_the_move,
                "essential_positions": result.essential_positions,
                "captured_pieces": result.captured_pieces,
                "captured_positions": result.captured_positions
            }
            
            if not result.game_over and result.movers_color and event.to_pos is not None:
                if game["logic"]._has_mandatory_from_position(game["board"], result.movers_color, event.to_pos):
                    response["position_for_mandatory_capture"] = event.to_pos

            await manager.send_to_room(room_id, response)
            
    except WebSocketDisconnect:
        await manager.disconnect(room_id, websocket)