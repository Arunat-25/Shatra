from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from logic import game_logic, get_mandatory_capture_for_one_position2, mandatory_captures, send_captured_pieces
import uuid

app = FastAPI()


last_room_id = 1
@app.get("/")
async def get_room_link():
    global last_room_id
    room_id = last_room_id
    last_room_id += 1
    return {"room_link": f"ws://localhost:8001/ws/{room_id}/"}


def change(position):
    if len(position) == 10:
        return int(position[-2]+position[-1])
    return int(position[-1])

def boards_keys_to_int(board):
    new_board = {}
    for i in board:
        new_board[int(i)] = board[i]
    return new_board

class ConnectionManager:
    def __init__(self):
        self.rooms: dict[int, list[WebSocket]] = {}

    async def connect(self, room_id: int, websocket: WebSocket):
        if not room_id in self.rooms:
            self.rooms[room_id] = []
        if len(self.rooms[room_id]) < 2:
            await websocket.accept()
            self.rooms[room_id].append(websocket)
            return True
        else:
            await websocket.close(code=1008)
            return False

    async def disconnect(self, room_id: int, websocket: WebSocket):
        self.rooms[room_id].remove(websocket)

    async def send_to_room(self, room_id, data):
        for websocket in self.rooms[room_id]:
            await websocket.send_json(data)


manager = ConnectionManager()

@app.websocket("/ws/{room_id}/")
async def check_and_return_board(websocket: WebSocket, room_id: int):

    is_connected = await manager.connect(room_id, websocket)
    if is_connected:
        if manager.rooms[room_id].index(websocket) == 0:
            await websocket.send_json({"players_color": "белый", "movers_color": "белый"})
        else:
            await websocket.send_json({"players_color": "черный", "movers_color": "белый"})

        try:
            while True:
                data = await websocket.receive_json()
                print(data)

                if len(data) != 4:
                    changed_board = game_logic(boards_keys_to_int(data["board"]),
                                               data["movers_color"],
                                               change(data["move_from"]),
                                               change(data["move_to"]),
                                               data["position_for_mandatory_capture"]
                                               )
                    await manager.send_to_room(1, changed_board)
                else:
                    info = get_mandatory_capture_for_one_position2(boards_keys_to_int(data["board"]), change(data["position"]), data["movers_color"])
                    captured_pieces = send_captured_pieces(boards_keys_to_int(data["board"]), change(data["position"]), data["position_for_mandatory_capture"])
                    await manager.send_to_room(1, {"essential_positions": info,
                                                                "captured_pieces": captured_pieces})
        except WebSocketDisconnect:
            await manager.disconnect(room_id, websocket)


