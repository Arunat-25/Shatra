"""Unit tests for admin time-series bucket helpers (regression guard)."""

from datetime import datetime, timedelta, timezone

import pytest

from backend.admin.service import (
    fill_time_series,
    games_series,
    infer_granularity,
    iter_buckets,
    parse_time_range,
    registrations_series,
)
from backend.db.session import get_session_factory
from backend.presence import online_unique_series
from tests.admin.conftest import insert_user_created_at
from tests.admin.series_assertions import assert_series_buckets_match


class TestIterBuckets:
    def test_seven_midnight_aligned_days(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 8, tzinfo=timezone.utc)
        assert len(iter_buckets(start, end, "day")) == 7

    def test_seven_calendar_days_when_start_has_offset(self):
        """7d wall-clock span with noon start spans 8 UTC day buckets."""
        start = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        end = start + timedelta(days=7)
        assert len(iter_buckets(start, end, "day")) == 8

    def test_parse_time_range_7d_matches_iter_buckets(self):
        start, end = parse_time_range(period="7d")
        granularity = infer_granularity(start, end)
        assert granularity == "day"
        assert len(iter_buckets(start, end, granularity)) >= 7

    def test_twenty_four_hours_hour_buckets(self):
        start = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
        end = start + timedelta(hours=24)
        buckets = iter_buckets(start, end, "hour")
        assert len(buckets) == 24
        assert buckets[0] == start

    def test_buckets_are_strictly_before_end(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 4, tzinfo=timezone.utc)
        for b in iter_buckets(start, end, "day"):
            assert b < end


class TestFillTimeSeries:
    def test_missing_keys_default_to_zero(self):
        starts = [
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 2, tzinfo=timezone.utc),
        ]
        filled = fill_time_series(starts, {starts[0]: 3})
        assert filled[0]["count"] == 3
        assert filled[1]["count"] == 0

    def test_preserves_bucket_order(self):
        starts = iter_buckets(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 4, tzinfo=timezone.utc),
            "day",
        )
        counts = {starts[1]: 2}
        filled = fill_time_series(starts, counts)
        assert [b["ts"] for b in filled] == starts


@pytest.mark.asyncio
class TestRegistrationsSeriesService:
    async def test_bucket_count_matches_iter_buckets(self):
        factory = get_session_factory()
        async with factory() as db:
            data = await registrations_series(db, period="7d")
        assert_series_buckets_match(data)

    async def test_registration_lands_in_aligned_bucket(self):
        ts = datetime.now(timezone.utc) - timedelta(hours=3)
        insert_user_created_at(ts)
        factory = get_session_factory()
        async with factory() as db:
            data = await registrations_series(db, period="24h")
        total = sum(b["count"] for b in data["buckets"])
        assert total >= 1


@pytest.mark.asyncio
class TestGamesSeriesService:
    async def test_bucket_count_matches_iter_buckets(self):
        factory = get_session_factory()
        async with factory() as db:
            data = await games_series(db, period="7d")
        assert_series_buckets_match(data)

@pytest.mark.asyncio
class TestOnlineSeriesService:
    async def test_bucket_count_matches_iter_buckets(self):
        start, end = parse_time_range(period="24h")
        granularity = infer_granularity(start, end)
        data = await online_unique_series(start, end, granularity)
        assert_series_buckets_match(data)
        for bucket in data["buckets"]:
            assert bucket["total_unique"] >= bucket["registered_unique"]
            assert bucket["total_unique"] >= bucket["anonymous_unique"]
