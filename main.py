from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Query, WebSocket
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
from datetime import datetime, timezone

from backend.room_manager import create_room, list_rooms, join_room
from backend.presence import touch_lobby_presence, count_online_for_lobby, end_lobby_sessions
from backend.session import websocket_endpoint
from backend.state import init_redis, close_redis, get_room
from backend.db.session import init_db, close_db
from backend.auth.router import router as auth_router
from backend.admin.router import router as admin_router
from backend.bug_reports.router import admin_router as bug_reports_admin_router
from backend.bug_reports.router import public_router as bug_reports_router


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

# Vite copies frontend/public/ (e.g. sounds/) to dist/ — must be mounted before SPA catch-all.
_sounds_dir = REACT_DIST / "sounds"
if _sounds_dir.is_dir():
    app.mount("/sounds", StaticFiles(directory=str(_sounds_dir)), name="game_sounds")

_images_dir = REACT_DIST / "images"
if _images_dir.is_dir():
    app.mount("/images", StaticFiles(directory=str(_images_dir)), name="site_images")


# === REST API (ДО catch-all) ===

app.include_router(auth_router, prefix="/api/auth")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(bug_reports_router, prefix="/api/bug-reports")
app.include_router(bug_reports_admin_router, prefix="/api/admin/bug-reports")
@app.post("/rooms")
async def create_room_api(
    request: CreateRoomRequest,
    user: User | None = Depends(get_optional_user),
):
    return await create_room(request, user)


@app.get("/rooms")
async def list_rooms_api(
    client_id: str | None = Query(default=None, min_length=1, max_length=64),
    user: User | None = Depends(get_optional_user),
):
    if client_id:
        await touch_lobby_presence(
            client_id=client_id,
            user_id=user.id if user else None,
            is_anonymous=user is None,
        )
    result = await list_rooms()
    online = await count_online_for_lobby()
    stats = result.setdefault("stats", {})
    stats["online_total"] = online["total_unique"]
    return result


@app.post("/rooms/presence/leave")
async def lobby_presence_leave(
    client_id: str = Query(..., min_length=1, max_length=64),
):
    await end_lobby_sessions(client_id)
    return {"ok": True}


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
