"""Room lock discipline: nested acquire on asyncio.Lock deadlocks."""

import asyncio

import pytest

from backend.state import get_room_lock


@pytest.mark.asyncio
async def test_nested_room_lock_deadlocks():
    """Document why *_locked helpers must be used under an existing lock."""
    room_id = "lock-audit"
    lock = get_room_lock(room_id)

    async def reacquire():
        async with lock:
            return True

    async with lock:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(reacquire(), timeout=0.05)


@pytest.mark.asyncio
async def test_finish_game_path_uses_locked_helper_under_ticker_lock():
    """game_ticker holds lock then calls _finish_game_locked (not finish_game)."""
    from backend import timers

    source = open(timers.__file__, encoding="utf-8").read()
    assert "await _finish_game_locked(" in source
    assert "handle_timeout" in source
    # disconnect_timer runs outside room lock — finish_game is OK there
    disconnect_block = source.split("async def disconnect_timer")[1].split("async def")[0]
    assert "await finish_game(" in disconnect_block


@pytest.mark.asyncio
async def test_rematch_uses_archive_locked_not_public_wrapper():
    from backend.session import rematch

    source = open(rematch.__file__, encoding="utf-8").read()
    assert "_archive_finished_game_locked" in source
    assert "archive_finished_game(" not in source
