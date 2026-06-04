"""Shared helpers for inserting finished_games rows in tests."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone


def insert_finished_game(**overrides):
    from backend.db.models import FinishedGame
    from backend.db.session import get_session_factory

    now = datetime.now(timezone.utc)
    defaults = {
        "room_id": "abc12345",
        "room_type": "public",
        "white_is_anonymous": False,
        "black_is_anonymous": True,
        "moves_count": 1,
        "move_history": [],
        "finished_at": now,
    }
    defaults.update(overrides)

    async def _insert():
        factory = get_session_factory()
        async with factory() as session:
            row = FinishedGame(**defaults)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row.id

    return asyncio.run(_insert())
