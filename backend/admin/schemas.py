"""Pydantic schemas for admin API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Granularity = Literal["hour", "day"]


class StatsPeriodResponse(BaseModel):
    total: int
    from_: datetime = Field(serialization_alias="from")
    to: datetime

    model_config = {"populate_by_name": True}


class OnlineStatsResponse(BaseModel):
    at: datetime
    total_unique: int
    anonymous_unique: int
    registered_unique: int


class OnlinePeriodStatsResponse(BaseModel):
    total_unique: int
    anonymous_unique: int
    registered_unique: int
    from_: datetime = Field(serialization_alias="from")
    to: datetime

    model_config = {"populate_by_name": True}


class GamesStatsResponse(BaseModel):
    total: int
    by_room_type: dict[str, int]
    by_anonymous_count: dict[str, int]
    from_: datetime = Field(serialization_alias="from")
    to: datetime

    model_config = {"populate_by_name": True}


class TimeBucket(BaseModel):
    ts: datetime
    count: int


class SeriesResponse(BaseModel):
    granularity: Granularity
    buckets: list[TimeBucket]
    from_: datetime = Field(serialization_alias="from")
    to: datetime

    model_config = {"populate_by_name": True}


class OnlineSeriesBucket(BaseModel):
    ts: datetime
    total_unique: int
    registered_unique: int
    anonymous_unique: int


class OnlineSeriesResponse(BaseModel):
    granularity: Granularity
    buckets: list[OnlineSeriesBucket]
    from_: datetime = Field(serialization_alias="from")
    to: datetime

    model_config = {"populate_by_name": True}
