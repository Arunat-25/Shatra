"""Track WebSocket presence sessions for admin analytics."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import String, and_, cast, false, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import PresenceSession
from backend.db.session import get_session_factory

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def end_lobby_sessions(client_id: str) -> None:
    """Close open lobby presence rows when user enters a game room."""
    try:
        now = _utcnow()
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(
                update(PresenceSession)
                .where(
                    PresenceSession.client_id == client_id,
                    PresenceSession.room_id.is_(None),
                    PresenceSession.disconnected_at.is_(None),
                )
                .values(disconnected_at=now)
            )
            await session.commit()
    except Exception:
        logger.exception("Failed to end lobby sessions for client %s", client_id[:6])


async def touch_lobby_presence(
    *,
    client_id: str,
    user_id: uuid.UUID | None,
    is_anonymous: bool,
) -> None:
    """Refresh lobby presence on GET /rooms polling."""
    try:
        now = _utcnow()
        factory = get_session_factory()
        async with factory() as session:
            open_rows = list(
                (
                    await session.scalars(
                        select(PresenceSession)
                        .where(
                            PresenceSession.client_id == client_id,
                            PresenceSession.room_id.is_(None),
                            PresenceSession.disconnected_at.is_(None),
                        )
                        .order_by(PresenceSession.connected_at.desc())
                    )
                ).all()
            )
            if open_rows:
                row = open_rows[0]
                for duplicate in open_rows[1:]:
                    duplicate.disconnected_at = now
                row.last_seen_at = now
                row.user_id = user_id
                row.is_anonymous = is_anonymous
                await session.commit()
                return

            session.add(
                PresenceSession(
                    client_id=client_id,
                    user_id=user_id,
                    is_anonymous=is_anonymous,
                    room_id=None,
                    connected_at=now,
                    last_seen_at=now,
                )
            )
            await session.commit()
    except Exception:
        logger.exception("Failed to touch lobby presence for client %s", client_id[:6])


async def close_stale_lobby_presence() -> None:
    """Close orphan lobby rows that stopped polling (without relying on leave beacon)."""
    try:
        now = _utcnow()
        cutoff = now - timedelta(seconds=settings.lobby_presence_stale_seconds)
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(
                update(PresenceSession)
                .where(
                    PresenceSession.room_id.is_(None),
                    PresenceSession.disconnected_at.is_(None),
                    PresenceSession.last_seen_at.isnot(None),
                    PresenceSession.last_seen_at < cutoff,
                )
                .values(disconnected_at=now)
            )
            await session.commit()
    except Exception:
        logger.exception("Failed to close stale lobby presence")


async def close_orphan_ws_presence(live_client_ids: frozenset[str]) -> None:
    """Close open game presence rows with no matching live WebSocket."""
    try:
        now = _utcnow()
        factory = get_session_factory()
        async with factory() as session:
            stmt = (
                update(PresenceSession)
                .where(
                    PresenceSession.room_id.isnot(None),
                    PresenceSession.disconnected_at.is_(None),
                )
                .values(disconnected_at=now)
            )
            if live_client_ids:
                stmt = stmt.where(~PresenceSession.client_id.in_(live_client_ids))
            await session.execute(stmt)
            await session.commit()
    except Exception:
        logger.exception("Failed to close orphan ws presence")


async def start_session(
    *,
    client_id: str,
    user_id: uuid.UUID | None,
    is_anonymous: bool,
    room_id: str | None,
) -> None:
    try:
        if room_id is not None:
            await end_lobby_sessions(client_id)
        now = _utcnow()
        factory = get_session_factory()
        async with factory() as session:
            session.add(
                PresenceSession(
                    client_id=client_id,
                    user_id=user_id,
                    is_anonymous=is_anonymous,
                    room_id=room_id,
                    connected_at=now,
                    last_seen_at=now if room_id is None else None,
                )
            )
            await session.commit()
    except Exception:
        logger.exception("Failed to start presence session for client %s", client_id[:6])


async def end_session(client_id: str) -> None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(
                update(PresenceSession)
                .where(
                    PresenceSession.client_id == client_id,
                    PresenceSession.disconnected_at.is_(None),
                )
                .values(disconnected_at=_utcnow())
            )
            await session.commit()
    except Exception:
        logger.exception("Failed to end presence session for client %s", client_id[:6])


def _ws_active_at(at: datetime):
    return and_(
        PresenceSession.room_id.isnot(None),
        PresenceSession.connected_at <= at,
        or_(
            PresenceSession.disconnected_at.is_(None),
            PresenceSession.disconnected_at > at,
        ),
    )


def _lobby_active_at(at: datetime):
    return and_(
        PresenceSession.room_id.is_(None),
        PresenceSession.connected_at <= at,
        or_(
            PresenceSession.disconnected_at.is_(None),
            PresenceSession.disconnected_at > at,
        ),
    )


def _active_at(at: datetime, *, live_ws_client_ids: frozenset[str] | None = None):
    ws_clause = _ws_active_at(at)
    if live_ws_client_ids is not None:
        if live_ws_client_ids:
            ws_clause = and_(ws_clause, PresenceSession.client_id.in_(live_ws_client_ids))
        else:
            ws_clause = false()
    return or_(ws_clause, _lobby_active_at(at))


def _identity_key():
    return func.coalesce(
        cast(PresenceSession.user_id, String),
        func.concat("anon:", PresenceSession.client_id),
    )


def _overlaps_period(start: datetime, end: datetime):
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return and_(
        PresenceSession.connected_at < end,
        or_(
            PresenceSession.disconnected_at.is_(None),
            PresenceSession.disconnected_at > start,
        ),
    )


async def count_online_unique_in_period(
    start: datetime,
    end: datetime,
    session: AsyncSession | None = None,
) -> dict:
    """Count unique people with at least one presence session overlapping [start, end]."""
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    async def _run(db: AsyncSession) -> dict:
        overlap = _overlaps_period(start, end)
        identity = _identity_key()

        total_stmt = select(func.count(func.distinct(identity))).where(overlap)
        total_unique = int((await db.scalar(total_stmt)) or 0)

        anon_stmt = (
            select(func.count(func.distinct(PresenceSession.client_id)))
            .where(overlap, PresenceSession.is_anonymous.is_(True))
        )
        anonymous_unique = int((await db.scalar(anon_stmt)) or 0)

        registered_unique = max(total_unique - anonymous_unique, 0)
        return {
            "from": start,
            "to": end,
            "total_unique": total_unique,
            "anonymous_unique": anonymous_unique,
            "registered_unique": registered_unique,
        }

    if session is not None:
        return await _run(session)

    factory = get_session_factory()
    async with factory() as db:
        return await _run(db)


async def online_unique_series(
    start: datetime,
    end: datetime,
    granularity: str,
    session: AsyncSession | None = None,
) -> dict:
    """Per-bucket unique online counts (sessions overlapping each interval)."""
    from backend.admin.service import _bucket_delta, iter_buckets

    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    bucket_starts = iter_buckets(start, end, granularity)
    delta = _bucket_delta(granularity)
    buckets: list[dict] = []

    async def _append_buckets(db: AsyncSession) -> None:
        for b_start in bucket_starts:
            b_end = min(b_start + delta, end)
            if b_start >= end:
                break
            stats = await count_online_unique_in_period(b_start, b_end, session=db)
            buckets.append(
                {
                    "ts": b_start,
                    "total_unique": stats["total_unique"],
                    "anonymous_unique": stats["anonymous_unique"],
                    "registered_unique": stats["registered_unique"],
                }
            )

    if session is not None:
        await _append_buckets(session)
    else:
        factory = get_session_factory()
        async with factory() as db:
            await _append_buckets(db)

    return {
        "granularity": granularity,
        "buckets": buckets,
        "from": start,
        "to": end,
    }


async def count_online_for_lobby() -> dict:
    """Live online count for lobby: purge stale/orphan rows, then count."""
    from backend.ws_manager import manager

    await close_stale_lobby_presence()
    live_ids = manager.connected_client_ids()
    await close_orphan_ws_presence(live_ids)
    return await count_online_at(
        _utcnow(),
        live_ws_client_ids=live_ids,
    )


async def count_online_at(
    at: datetime,
    session: AsyncSession | None = None,
    *,
    live_ws_client_ids: frozenset[str] | None = None,
) -> dict:
    """Count unique people online at a point in time."""
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)

    async def _run(db: AsyncSession) -> dict:
        active = _active_at(at, live_ws_client_ids=live_ws_client_ids)
        identity = _identity_key()

        total_stmt = select(func.count(func.distinct(identity))).where(active)
        total_unique = int((await db.scalar(total_stmt)) or 0)

        anon_stmt = (
            select(func.count(func.distinct(PresenceSession.client_id)))
            .where(active, PresenceSession.is_anonymous.is_(True))
        )
        anonymous_unique = int((await db.scalar(anon_stmt)) or 0)

        registered_unique = max(total_unique - anonymous_unique, 0)
        return {
            "at": at,
            "total_unique": total_unique,
            "anonymous_unique": anonymous_unique,
            "registered_unique": registered_unique,
        }

    if session is not None:
        return await _run(session)

    factory = get_session_factory()
    async with factory() as db:
        return await _run(db)
