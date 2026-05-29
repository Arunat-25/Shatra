from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import json
import logging

import sentry_sdk

from backend.config import settings
from backend.auth.dependencies import get_optional_user
from backend.db.models import User
from backend.models import CreateRoomRequest
from backend.room_manager import create_room, list_rooms, join_room
from backend.session import websocket_endpoint
from backend.state import init_redis, close_redis, get_room
from backend.db.session import init_db, close_db
from backend.auth.router import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_redis()
    await init_db()
    yield
    # Shutdown
    await close_db()
    await close_redis()


app = FastAPI(lifespan=lifespan)

def _parse_cors_origins() -> list[str]:
    raw = settings.cors_allow_origins
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


logger = logging.getLogger(__name__)

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

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
    logger.warning("React dist assets missing; static mount skipped: %s", REACT_DIST)


# === REST API (ДО catch-all) ===

app.include_router(auth_router, prefix="/api/auth")

@app.post("/rooms")
async def create_room_api(
    request: CreateRoomRequest,
    user: User | None = Depends(get_optional_user),
):
    return await create_room(request, user)


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
