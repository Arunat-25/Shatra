"""Health check endpoint helpers."""

from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend import state
from backend.db.session import get_engine

router = APIRouter(tags=["health"])

_started_at = time.time()


async def check_redis() -> str:
    if state.redis_client is None:
        return "down"
    try:
        await state.redis_client.ping()
        return "ok"
    except Exception:
        return "down"


async def check_postgres() -> str:
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "down"


@router.get("/health")
async def health():
    redis_status = await check_redis()
    postgres_status = await check_postgres()
    ok = redis_status == "ok" and postgres_status == "ok"
    body = {
        "status": "ok" if ok else "degraded",
        "redis": redis_status,
        "postgres": postgres_status,
        "uptime_seconds": round(time.time() - _started_at, 1),
    }
    return JSONResponse(body, status_code=200 if ok else 503)
