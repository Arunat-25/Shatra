import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.models import CreateRoomRequest
from backend.room_manager import create_room, list_rooms, join_room
from backend.game_session import websocket_endpoint
from backend.state import init_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_redis()
    yield
    # Shutdown
    await close_redis()


app = FastAPI(lifespan=lifespan)

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
    return await create_room(request)


@app.get("/rooms")
async def list_rooms_api():
    return await list_rooms()


@app.post("/rooms/{room_id}/join")
async def join_room_api(room_id: str):
    return await join_room(room_id)


@app.get("/rooms/{room_id}/status")
async def room_status_api(room_id: str):
    from backend.state import get_room
    room_data = await get_room(room_id)
    if not room_data:
        return {"found": False}
    return {
        "found": True,
        "game_started": room_data.get("game_started", False),
        "player2_connected": room_data.get("player2_connected", False),
        "room_id": room_data.get("room_id"),
        "time_control": room_data.get("time_control"),
    }


# === WebSocket ===

@app.websocket("/ws/{room_id}/")
async def ws_endpoint(websocket: WebSocket, room_id: str):
    await websocket_endpoint(websocket, room_id)