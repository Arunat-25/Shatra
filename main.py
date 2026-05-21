from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from game_engine.models import GameEvent
from game_engine.game_logic import GameLogic

from backend.models import CreateRoomRequest
from backend.room_manager import rooms, create_room, list_rooms, join_room, quick_start
from backend.ws_manager import manager, handle_player1_waiting, handle_player2_join, games
from backend.board_utils import board_to_json, boards_keys_to_int, change_position_name_from_frontend

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/Frontend", StaticFiles(directory="Frontend", html=True), name="frontend")


@app.get("/")
async def root():
    return RedirectResponse(url="/Frontend/lobby.html")


# === REST API ===

@app.post("/rooms")
async def create_room_api(request: CreateRoomRequest):
    return create_room(request)


@app.get("/rooms")
async def list_rooms_api():
    return list_rooms()


@app.post("/rooms/{room_id}/join")
async def join_room_api(room_id: str):
    return join_room(room_id)


@app.get("/rooms/quick-start")
async def quick_start_api():
    return quick_start()


# === WebSocket ===

@app.websocket("/ws/{room_id}/")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    if not await manager.connect(room_id, websocket):
        return

    room = rooms.get(room_id)
    if not room:
        return

    # Первый игрок — ждём второго
    if room.player1_ws == websocket and not room.player2_connected:
        await handle_player1_waiting(room_id, websocket, room)

    # Второй игрок — создаём игру
    elif room.player2_ws == websocket:
        await handle_player2_join(room_id, room)

    # Игровой цикл
    try:
        while True:
            data = await websocket.receive_json()

            event = GameEvent(
                positions=boards_keys_to_int(data["board"]),
                mover_color=data["movers_color"],
                from_pos=change_position_name_from_frontend(data.get("move_from")) if data.get("move_from") else None,
                to_pos=change_position_name_from_frontend(data.get("move_to")) if data.get("move_to") else None,
                position=change_position_name_from_frontend(data.get("position")) if data.get("position") else None,
                position_for_mandatory_capture=data.get("position_for_mandatory_capture")
            )

            game = games[room_id]
            prev_mover = game["mover"]
            result = game["logic"].handle_event(
                event, batyr_captured_this_turn=game["pending_batyr_captures"]
            )

            if result.updated_positions:
                game["board"] = result.updated_positions

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

            if result.movers_color and result.movers_color != prev_mover:
                response["position_for_mandatory_capture"] = None

            await manager.send_to_room(room_id, response)

    except WebSocketDisconnect:
        await manager.disconnect(room_id, websocket)