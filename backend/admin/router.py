"""Admin API routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.admin.schemas import (
    GamesStatsResponse,
    OnlinePeriodStatsResponse,
    OnlineSeriesResponse,
    OnlineStatsResponse,
    SeriesResponse,
    StatsPeriodResponse,
)
from backend.admin.service import (
    VALID_PERIODS,
    count_games,
    count_registrations,
    games_series,
    infer_granularity,
    parse_time_range,
    registrations_series,
)
from backend.auth.dependencies import get_admin_user
from backend.db.models import User
from backend.db.session import get_db
from backend.presence import (
    count_online_at,
    count_online_unique_in_period,
    online_unique_series,
)

router = APIRouter(tags=["admin"])


def _parse_optional_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid datetime format") from exc


def _validate_period(period: str) -> str:
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=422, detail=f"Unknown period: {period}")
    return period


@router.get("/stats/registrations", response_model=StatsPeriodResponse)
async def stats_registrations(
    period: str = Query(default="7d"),
    from_dt: str | None = Query(default=None, alias="from"),
    to_dt: str | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    parsed_from = _parse_optional_dt(from_dt)
    parsed_to = _parse_optional_dt(to_dt)
    if (parsed_from is None) ^ (parsed_to is None):
        raise HTTPException(status_code=422, detail="Both from and to are required for custom range")
    if parsed_from is None:
        _validate_period(period)
    try:
        data = await count_registrations(db, period=period, from_dt=parsed_from, to_dt=parsed_to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return StatsPeriodResponse(total=data["total"], from_=data["from"], to=data["to"])


@router.get("/stats/registrations/series", response_model=SeriesResponse)
async def stats_registrations_series(
    period: str = Query(default="7d"),
    from_dt: str | None = Query(default=None, alias="from"),
    to_dt: str | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    parsed_from = _parse_optional_dt(from_dt)
    parsed_to = _parse_optional_dt(to_dt)
    if (parsed_from is None) ^ (parsed_to is None):
        raise HTTPException(status_code=422, detail="Both from and to are required for custom range")
    if parsed_from is None:
        _validate_period(period)
    try:
        data = await registrations_series(db, period=period, from_dt=parsed_from, to_dt=parsed_to)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SeriesResponse(
        granularity=data["granularity"],
        buckets=data["buckets"],
        from_=data["from"],
        to=data["to"],
    )


@router.get("/stats/online", response_model=OnlineStatsResponse)
async def stats_online(
    at: str = Query(...),
    _admin: User = Depends(get_admin_user),
):
    parsed_at = _parse_optional_dt(at)
    if parsed_at is None:
        raise HTTPException(status_code=422, detail="at is required")
    data = await count_online_at(parsed_at)
    return OnlineStatsResponse(**data)


@router.get("/stats/online/period", response_model=OnlinePeriodStatsResponse)
async def stats_online_period(
    period: str = Query(default="7d"),
    from_dt: str | None = Query(default=None, alias="from"),
    to_dt: str | None = Query(default=None, alias="to"),
    _admin: User = Depends(get_admin_user),
):
    parsed_from = _parse_optional_dt(from_dt)
    parsed_to = _parse_optional_dt(to_dt)
    if (parsed_from is None) ^ (parsed_to is None):
        raise HTTPException(status_code=422, detail="Both from and to are required for custom range")
    if parsed_from is None:
        _validate_period(period)
    try:
        start, end = parse_time_range(period=period, from_dt=parsed_from, to_dt=parsed_to)
        data = await count_online_unique_in_period(start, end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return OnlinePeriodStatsResponse(
        from_=data["from"],
        to=data["to"],
        total_unique=data["total_unique"],
        anonymous_unique=data["anonymous_unique"],
        registered_unique=data["registered_unique"],
    )


@router.get("/stats/online/series", response_model=OnlineSeriesResponse)
async def stats_online_series(
    period: str = Query(default="7d"),
    from_dt: str | None = Query(default=None, alias="from"),
    to_dt: str | None = Query(default=None, alias="to"),
    _admin: User = Depends(get_admin_user),
):
    parsed_from = _parse_optional_dt(from_dt)
    parsed_to = _parse_optional_dt(to_dt)
    if (parsed_from is None) ^ (parsed_to is None):
        raise HTTPException(status_code=422, detail="Both from and to are required for custom range")
    if parsed_from is None:
        _validate_period(period)
    try:
        start, end = parse_time_range(period=period, from_dt=parsed_from, to_dt=parsed_to)
        granularity = infer_granularity(start, end)
        data = await online_unique_series(start, end, granularity)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return OnlineSeriesResponse(
        granularity=data["granularity"],
        buckets=data["buckets"],
        from_=data["from"],
        to=data["to"],
    )


@router.get("/stats/games", response_model=GamesStatsResponse)
async def stats_games(
    period: str = Query(default="7d"),
    from_dt: str | None = Query(default=None, alias="from"),
    to_dt: str | None = Query(default=None, alias="to"),
    room_type: str = Query(default="all", pattern="^(all|public|private|ai)$"),
    anonymous_players: str = Query(default="all", pattern="^(all|0|1|2)$"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    parsed_from = _parse_optional_dt(from_dt)
    parsed_to = _parse_optional_dt(to_dt)
    if (parsed_from is None) ^ (parsed_to is None):
        raise HTTPException(status_code=422, detail="Both from and to are required for custom range")
    if parsed_from is None:
        _validate_period(period)
    try:
        data = await count_games(
            db,
            period=period,
            from_dt=parsed_from,
            to_dt=parsed_to,
            room_type=room_type,
            anonymous_players=anonymous_players,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return GamesStatsResponse(
        total=data["total"],
        by_room_type=data["by_room_type"],
        by_anonymous_count=data["by_anonymous_count"],
        from_=data["from"],
        to=data["to"],
    )


@router.get("/stats/games/series", response_model=SeriesResponse)
async def stats_games_series(
    period: str = Query(default="7d"),
    from_dt: str | None = Query(default=None, alias="from"),
    to_dt: str | None = Query(default=None, alias="to"),
    room_type: str = Query(default="all", pattern="^(all|public|private|ai)$"),
    anonymous_players: str = Query(default="all", pattern="^(all|0|1|2)$"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    parsed_from = _parse_optional_dt(from_dt)
    parsed_to = _parse_optional_dt(to_dt)
    if (parsed_from is None) ^ (parsed_to is None):
        raise HTTPException(status_code=422, detail="Both from and to are required for custom range")
    if parsed_from is None:
        _validate_period(period)
    try:
        data = await games_series(
            db,
            period=period,
            from_dt=parsed_from,
            to_dt=parsed_to,
            room_type=room_type,
            anonymous_players=anonymous_players,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SeriesResponse(
        granularity=data["granularity"],
        buckets=data["buckets"],
        from_=data["from"],
        to=data["to"],
    )
