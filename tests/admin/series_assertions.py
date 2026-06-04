"""Shared assertions for admin time-series API responses."""

from datetime import datetime, timezone

from backend.admin.service import iter_buckets


def _coerce_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def assert_series_buckets_match(data: dict) -> None:
    """Series responses must have one bucket per iter_buckets window."""
    start = _coerce_dt(data["from"])
    end = _coerce_dt(data["to"])
    granularity = data["granularity"]
    expected = len(iter_buckets(start, end, granularity))
    assert len(data["buckets"]) == expected, (
        f"expected {expected} {granularity} buckets, got {len(data['buckets'])}"
    )
