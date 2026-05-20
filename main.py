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
    # Все клетки пустые по умолчанию
    for i in range(1, 63):
        board[i] = None
    
    # Чёрные шатры только в крепости (1-9)
    for i in range(1, 10):
        board[i] = "черная шатра"
    board[10] = "черный бий"
    
    # Чёрные батыры на 11 и 17
    board[11] = "черный батыр"
    board[17] = "черный батыр"
    
    # Белые шатры только в крепости (54-62)
    for i in range(54, 63):
        board[i] = "белая шатра"
    board[53] = "белый бий"
    
    # Белые батыры на 46 и 52
    board[46] = "белый батыр"
    board[52] = "белый батыр"
    
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
                "players": {},
                "pending_batyr_captures": []
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

            result: GameEventResult = game["logic"].handle_event(
                event, batyr_captured_this_turn=game["pending_batyr_captures"]
            )

            # Запоминаем кто ходил до обработки
            prev_mover = game["mover"]
            
            if result.updated_positions:
                game["board"] = result.updated_positions
            
            # Обновляем pending_batyr_captures
            # Сначала проверяем смену хода — если ход перешёл, очищаем
            if result.movers_color and result.movers_color != prev_mover:
                game["pending_batyr_captures"] = []
            elif result.captured_pieces:
                game["pending_batyr_captures"] = result.captured_pieces
            
            if result.movers_color:
                game["mover"] = result.movers_color

            response = {
                "message": result.message,
                "movers_color": result.movers_color,
                "desk": board_to_json(game["board"]),
                "game_over": result.game_over,
                "winner": result.winner,
                "position_for_mandatory_capture": result.position_for_mandatory_capture,
                "opportunity_pass_the_move": result.opportunity_pass_the_move,
                "essential_positions": result.essential_positions,
                "captured_pieces": result.captured_pieces,
                "captured_positions": result.captured_positions
            }
            
            # Если ход перешёл к другому игроку, очищаем position_for_mandatory_capture
            if result.movers_color and result.movers_color != prev_mover:
                response["position_for_mandatory_capture"] = None

            await manager.send_to_room(room_id, response)
            
    except WebSocketDisconnect:
        await manager.disconnect(room_id, websocket)