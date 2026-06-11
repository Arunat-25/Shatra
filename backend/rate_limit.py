"""Shared Redis sliding-window rate limiting."""

from __future__ import annotations

from backend import state


async def check_sliding_window_rate_limit(
    key: str,
    *,
    limit: int,
    window_seconds: int,
) -> bool:
    """Return True if the request is allowed."""
    if state.redis_client is None:
        return True
    count = await state.redis_client.incr(key)
    if count == 1:
        await state.redis_client.expire(key, window_seconds)
    return count <= limit
