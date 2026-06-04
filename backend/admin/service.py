"""Admin statistics and helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import FinishedGame, User

Period = str | None
Granularity = Literal["hour", "day"]

VALID_PERIODS = frozenset({"1h", "3h", "6h", "12h", "24h", "7d", "30d", "all"})

_HOUR_PERIODS = {"1h": 1, "3h": 3, "6h": 6, "12h": 12, "24h": 24}


def parse_time_range(
    *,
    period: Period = "7d",
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if from_dt is not None and to_dt is not None:
        start = from_dt if from_dt.tzinfo else from_dt.replace(tzinfo=timezone.utc)
        end = to_dt if to_dt.tzinfo else to_dt.replace(tzinfo=timezone.utc)
        return start, end

    key = period or "7d"
    if key in _HOUR_PERIODS:
        return now - timedelta(hours=_HOUR_PERIODS[key]), now
    if key == "7d":
        return now - timedelta(days=7), now
    if key == "30d":
        return now - timedelta(days=30), now
    if key == "all":
        return datetime(1970, 1, 1, tzinfo=timezone.utc), now
    raise ValueError(f"Unknown period: {key}")


def infer_granularity(start: datetime, end: datetime) -> Granularity:
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if (end - start).total_seconds() <= 48 * 3600:
        return "hour"
    return "day"


def _align_bucket_start(ts: datetime, granularity: Granularity) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    if granularity == "hour":
        return ts.replace(minute=0, second=0, microsecond=0)
    return ts.replace(hour=0, minute=0, second=0, microsecond=0)


def iter_buckets(start: datetime, end: datetime, granularity: Granularity) -> list[datetime]:
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    delta = timedelta(hours=1) if granularity == "hour" else timedelta(days=1)
    current = _align_bucket_start(start, granularity)
    buckets: list[datetime] = []
    while current < end:
        buckets.append(current)
        current += delta
    return buckets


def _bucket_delta(granularity: Granularity) -> timedelta:
    return timedelta(hours=1) if granularity == "hour" else timedelta(days=1)


def fill_time_series(
    bucket_starts: list[datetime],
    counts_by_ts: dict[datetime, int],
) -> list[dict]:
    return [{"ts": b, "count": counts_by_ts.get(b, 0)} for b in bucket_starts]


async def count_registrations(
    db: AsyncSession,
    *,
    period: Period = "7d",
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> dict:
    start, end = parse_time_range(period=period, from_dt=from_dt, to_dt=to_dt)
    stmt = select(func.count()).select_from(User).where(
        User.created_at >= start,
        User.created_at <= end,
    )
    total = int((await db.scalar(stmt)) or 0)
    return {"total": total, "from": start, "to": end}


def anonymous_player_count(
    room_type: str,
    white_is_anonymous: bool,
    black_is_anonymous: bool,
) -> int:
    if room_type == "ai":
        if white_is_anonymous or black_is_anonymous:
            return 1
        return 0
    return int(white_is_anonymous) + int(black_is_anonymous)


async def count_games(
    db: AsyncSession,
    *,
    period: Period = "7d",
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    room_type: str = "all",
    anonymous_players: str = "all",
) -> dict:
    start, end = parse_time_range(period=period, from_dt=from_dt, to_dt=to_dt)
    stmt = select(FinishedGame).where(
        FinishedGame.finished_at >= start,
        FinishedGame.finished_at <= end,
    )
    if room_type != "all":
        stmt = stmt.where(FinishedGame.room_type == room_type)

    rows = list((await db.scalars(stmt)).all())

    by_room_type: dict[str, int] = {"public": 0, "private": 0, "ai": 0}
    by_anonymous_count: dict[str, int] = {"0": 0, "1": 0, "2": 0}
    filtered_total = 0

    for row in rows:
        anon_count = anonymous_player_count(
            row.room_type,
            row.white_is_anonymous,
            row.black_is_anonymous,
        )
        by_room_type[row.room_type] = by_room_type.get(row.room_type, 0) + 1
        by_anonymous_count[str(anon_count)] = by_anonymous_count.get(str(anon_count), 0) + 1

        if anonymous_players != "all" and str(anon_count) != anonymous_players:
            continue
        filtered_total += 1

    return {
        "total": filtered_total,
        "by_room_type": by_room_type,
        "by_anonymous_count": by_anonymous_count,
        "from": start,
        "to": end,
    }


async def registrations_series(
    db: AsyncSession,
    *,
    period: Period = "7d",
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> dict:
    start, end = parse_time_range(period=period, from_dt=from_dt, to_dt=to_dt)
    granularity = infer_granularity(start, end)
    bucket_starts = iter_buckets(start, end, granularity)
    trunc = func.date_trunc(granularity, User.created_at)
    stmt = (
        select(trunc.label("bucket"), func.count())
        .where(User.created_at >= start, User.created_at <= end)
        .group_by(trunc)
        .order_by(trunc)
    )
    rows = (await db.execute(stmt)).all()
    counts: dict[datetime, int] = {}
    for bucket_ts, count in rows:
        if bucket_ts is None:
            continue
        key = _align_bucket_start(bucket_ts, granularity)
        counts[key] = int(count)
    buckets = fill_time_series(bucket_starts, counts)
    return {"granularity": granularity, "buckets": buckets, "from": start, "to": end}


def _game_passes_anonymous_filter(
    row: FinishedGame,
    anonymous_players: str,
) -> bool:
    if anonymous_players == "all":
        return True
    anon_count = anonymous_player_count(
        row.room_type,
        row.white_is_anonymous,
        row.black_is_anonymous,
    )
    return str(anon_count) == anonymous_players


async def games_series(
    db: AsyncSession,
    *,
    period: Period = "7d",
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    room_type: str = "all",
    anonymous_players: str = "all",
) -> dict:
    start, end = parse_time_range(period=period, from_dt=from_dt, to_dt=to_dt)
    granularity = infer_granularity(start, end)
    bucket_starts = iter_buckets(start, end, granularity)
    counts = dict.fromkeys(bucket_starts, 0)

    stmt = select(FinishedGame).where(
        FinishedGame.finished_at >= start,
        FinishedGame.finished_at <= end,
    )
    if room_type != "all":
        stmt = stmt.where(FinishedGame.room_type == room_type)

    rows = list((await db.scalars(stmt)).all())
    for row in rows:
        if not _game_passes_anonymous_filter(row, anonymous_players):
            continue
        finished = row.finished_at
        if finished.tzinfo is None:
            finished = finished.replace(tzinfo=timezone.utc)
        key = _align_bucket_start(finished, granularity)
        if key in counts:
            counts[key] += 1

    buckets = fill_time_series(bucket_starts, counts)
    return {"granularity": granularity, "buckets": buckets, "from": start, "to": end}
