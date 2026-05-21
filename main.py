import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from game_engine.models import GameEvent

from backend.models import CreateRoomRequest
from backend.room_manager import rooms, create_room, list_rooms, join_room
from backend.ws_manager import manager, games, init_game
from backend.board_utils import keys_int_to_str, keys_str_to_int, change_position_name_from_frontend
from backend.ai import get_best_move

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# React production build
REACT_DIST = Path(__file__).parent / "frontend" / "dist"
app.mount("/assets", StaticFiles(directory=str(REACT_DIST / "assets")), name="react_assets")


@app.get("/")
@app.get("/game")
async def serve_react():
    return FileResponse(str(REACT_DIST / "index.html"))


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

async def handle_ai_move(room_id: str, game: dict, max_recursion: int = 5):
    """Вычислить и отправить ход AI."""
    await asyncio.sleep(1.5)  # небольшая задержка, как у человека

    board = game["board"]
    board_snapshot = dict(board)
    ai_color = game["mover"]
    move = get_best_move(board, ai_color, depth=3)
    if move is None:
        return

    from_cell, to_cell = move
    data = GameEvent(
        positions=board,
        mover_color=ai_color,
        from_pos=from_cell,
        to_pos=to_cell,
    )
    prev_mover = game["mover"]
    result = game["logic"].handle_event(data, batyr_captured_this_turn=game["pending_batyr_captures"])

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
        "desk": keys_int_to_str(game["board"]),
        "game_over": result.game_over,
        "winner": result.winner,
        "position_for_mandatory_capture": result.position_for_mandatory_capture,
        "opportunity_pass_the_move": result.opportunity_pass_the_move,
        "essential_positions": result.essential_positions,
        "captured_pieces": result.captured_pieces,
        "captured_positions": result.captured_positions,
    }

    if result.movers_color and result.movers_color != prev_mover:
        response["position_for_mandatory_capture"] = None

    await manager.send_to_room(room_id, response)

    # Если AI может продолжать (цепочка взятий), ходим снова
    # Если ход не удался (доска не изменилась) — прекращаем
    if not result.updated_positions or result.updated_positions == board_snapshot:
        return

    # Цепочка взятий: AI ходит снова (макс 5 раз)
    if result.movers_color == ai_color and not result.game_over:
        await handle_ai_move(room_id, game, max_recursion - 1)


@app.websocket("/ws/{room_id}/")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    player_id = websocket.query_params.get("player")
    player_id_int = int(player_id) if player_id and player_id.isdigit() else None
    if not await manager.connect(room_id, websocket, player_id=player_id_int):
        return

    room = rooms.get(room_id)
    if not room:
        return

    is_ai_room = room.type == "ai"
    is_player1 = room.player1_ws == websocket

    # AI-комнаты: немедленный старт
    if is_ai_room and is_player1:
        room.player2_connected = True
        room.player2_ws = None  # AI не использует WebSocket
        await init_game(room_id)
        game = games[room_id]
        room.game_started = True

        await manager.send_to_player(websocket, {
            "status": "game_started",
            "movers_color": game["mover"],
            "desk": keys_int_to_str(game["board"]),
        })

        # Если AI ходит первым (должен быть белый, а AI чёрный)
        if game["mover"] == "черный":
            await handle_ai_move(room_id, game)

    elif room.game_started:
        game = games.get(room_id)
        if game:
            await manager.send_to_player(websocket, {
                "status": "game_started",
                "movers_color": game["mover"],
                "desk": keys_int_to_str(game["board"]),
            })
    elif is_player1:
        await manager.send_to_player(websocket, {
            "status": "waiting",
            "link": room_id,
        })
        try:
            while not room.game_started:
                await asyncio.sleep(1.0)
        except Exception:
            await manager.disconnect(room_id, websocket)
            return
    else:
        # P2 подсоединяется
        from backend.ws_manager import handle_player2_join
        await handle_player2_join(room_id, room)

    if not room.game_started:
        await manager.disconnect(room_id, websocket)
        return

    try:
        while True:
            data = await websocket.receive_json()

            event = GameEvent(
                positions=keys_str_to_int(data["board"]),
                mover_color=data["movers_color"],
                from_pos=change_position_name_from_frontend(data.get("move_from")) if data.get("move_from") else None,
                to_pos=change_position_name_from_frontend(data.get("move_to")) if data.get("move_to") else None,
                position=change_position_name_from_frontend(data.get("position")) if data.get("position") else None,
                position_for_mandatory_capture=data.get("position_for_mandatory_capture"),
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
                "desk": keys_int_to_str(game["board"]),
                "game_over": result.game_over,
                "winner": result.winner,
                "position_for_mandatory_capture": result.position_for_mandatory_capture,
                "opportunity_pass_the_move": result.opportunity_pass_the_move,
                "essential_positions": result.essential_positions,
                "captured_pieces": result.captured_pieces,
                "captured_positions": result.captured_positions,
            }

            if result.movers_color and result.movers_color != prev_mover:
                response["position_for_mandatory_capture"] = None

            await manager.send_to_room(room_id, response)

            # AI ход после игрока
            if is_ai_room and not result.game_over and game["mover"] == "черный":
                await handle_ai_move(room_id, game)

    except WebSocketDisconnect:
        await manager.disconnect(room_id, websocket)