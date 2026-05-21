import asyncio
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from game_engine.models import GameEvent
from game_engine.game_logic import GameLogic

from backend.models import CreateRoomRequest
from backend.room_manager import rooms, create_room, list_rooms, join_room
from backend.ws_manager import manager, handle_player2_join, games, init_game
from backend.board_utils import board_to_json, boards_keys_to_int, change_position_name_from_frontend

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Определяем, используем ли React (frontend/dist) или статику
REACT_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(REACT_DIST) and os.path.isfile(os.path.join(REACT_DIST, "index.html")):
    # Режим React (production build)
    app.mount("/assets", StaticFiles(directory=os.path.join(REACT_DIST, "assets")), name="react_assets")
    app.mount("/img", StaticFiles(directory=os.path.join(REACT_DIST, "img")), name="react_img")
    
    @app.get("/")
    @app.get("/game")
    async def serve_react():
        return FileResponse(os.path.join(REACT_DIST, "index.html"))
else:
    # Режим vanilla JS (для разработки или если нет React build)
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


@app.get("/rooms/{room_id}/status")
async def room_status_api(room_id: str):
    room = rooms.get(room_id)
    if not room:
        return {"found": False}
    return {
        "found": True,
        "game_started": room.game_started,
        "player2_connected": room.player2_connected,
        "room_id": room.room_id
    }


# === WebSocket ===

@app.websocket("/ws/{room_id}/")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    player_id = websocket.query_params.get("player")
    player_id_int = int(player_id) if player_id and player_id.isdigit() else None
    if not await manager.connect(room_id, websocket, player_id=player_id_int):
        return

    room = rooms.get(room_id)
    if not room:
        return

    game_started_on_connect = room.game_started
    is_player1 = room.player1_ws == websocket
    is_player2 = room.player2_ws == websocket

    if game_started_on_connect:
        # Игра уже началась (новый WS от P1 после редиректа)
        game = games.get(room_id)
        if game:
            await manager.send_to_player(websocket, {
                "status": "game_started",
                "movers_color": game["mover"],
                "desk": board_to_json(game["board"])
            })
    elif is_player1:
        # P1 — ждём, пока игра не начнётся
        await manager.send_to_player(websocket, {
            "status": "waiting",
            "link": room_id
        })
        try:
            while not room.game_started:
                await asyncio.sleep(1.0)
        except Exception:
            await manager.disconnect(room_id, websocket)
            return
    elif is_player2:
        # P2 — создаём игру
        await handle_player2_join(room_id, room)
        # После этой функции игра уже начата, но P2 мог получить данные
        # напрямую из handle_player2_join. Продолжаем игровой цикл.

    # Игровой цикл (для обоих игроков после начала игры)
    if not room.game_started:
        await manager.disconnect(room_id, websocket)
        return

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