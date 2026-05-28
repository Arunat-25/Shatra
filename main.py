from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import json
import os
import time

from backend.models import CreateRoomRequest
from backend.room_manager import create_room, list_rooms, join_room
from backend.game_session import websocket_endpoint
from backend.state import init_redis, close_redis, get_room


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_redis()
    yield
    # Shutdown
    await close_redis()


app = FastAPI(lifespan=lifespan)

def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
    if raw == "*":
        return ["*"]
    if raw.startswith("["):
        try:
            data = json.loads(raw)
            if isinstance(data, list) and all(isinstance(x, str) for x in data):
                return data
        except Exception:
            pass
    return [o.strip() for o in raw.split(",") if o.strip()]


# region agent log
_DEBUG_LOG_PATH = "/home/arunat/coding/Shatra/.cursor/debug-55e98f.log"
_DBG_COUNTS: dict[str, int] = {}
def _dbg(hypothesis_id: str, location: str, message: str, data: dict):
    try:
        _DBG_COUNTS[hypothesis_id] = _DBG_COUNTS.get(hypothesis_id, 0) + 1
        if _DBG_COUNTS[hypothesis_id] > 20:
            return
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "sessionId": "55e98f",
                "runId": "pre-fix",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(time.time() * 1000),
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass
# endregion

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# React production build
REACT_DIST = Path(__file__).parent / "frontend" / "dist"
if (REACT_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(REACT_DIST / "assets")), name="react_assets")
else:
    # Не ломаем разработку (vite dev), но в проде это поможет понять, что build не сделан.
    _dbg("H3", "main.py:react_dist", "react dist assets missing; static mount skipped", {"react_dist": str(REACT_DIST)})


# === REST API (ДО catch-all) ===

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
    room_data = await get_room(room_id)
    if not room_data:
        return {"found": False}
    return {
        "found": True,
        "game_started": room_data.get("game_started", False),
        "room_id": room_data.get("room_id"),
        "time_control": room_data.get("time_control"),
    }


# === WebSocket ===

@app.websocket("/ws/{room_id}/")
async def ws_endpoint(websocket: WebSocket, room_id: str):
    await websocket_endpoint(websocket, room_id)


# === SPA (catch-all — ДОЛЖЕН БЫТЬ ПОСЛЕДНИМ) ===

@app.get("/")
@app.get("/{path:path}")
async def serve_react(path=""):
    return FileResponse(str(REACT_DIST / "index.html"))
