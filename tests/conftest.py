"""Общие фикстуры для тестов Shatra."""

import asyncio

import psycopg2
import pytest

import tests.test_env  # noqa: F401 — изолированная БД/Redis до импорта backend

from backend.board_utils import get_starting_board
from tests.test_env import SYNC_DB_URL


def _ensure_schema_patches() -> None:
    """Добавляет колонки из новых миграций, если БД создана через create_all_tables."""
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'presence_sessions'
              AND column_name = 'last_seen_at'
            """
        )
        if cur.fetchone() is None:
            cur.execute(
                "ALTER TABLE presence_sessions ADD COLUMN last_seen_at TIMESTAMPTZ"
            )
            cur.execute(
                "UPDATE presence_sessions SET last_seen_at = connected_at"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_presence_sessions_last_seen_at "
                "ON presence_sessions (last_seen_at)"
            )

        cur.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'users'
              AND column_name = 'rating'
            """
        )
        if cur.fetchone() is None:
            cur.execute(
                "ALTER TABLE users ADD COLUMN rating INTEGER NOT NULL DEFAULT 1200"
            )
            cur.execute(
                "ALTER TABLE users ADD COLUMN rated_games_count INTEGER NOT NULL DEFAULT 0"
            )

        cur.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'finished_games'
              AND column_name = 'is_rated'
            """
        )
        if cur.fetchone() is None:
            cur.execute(
                "ALTER TABLE finished_games ADD COLUMN is_rated BOOLEAN NOT NULL DEFAULT false"
            )
            cur.execute(
                "ALTER TABLE finished_games ADD COLUMN white_rating_delta INTEGER"
            )
            cur.execute(
                "ALTER TABLE finished_games ADD COLUMN black_rating_delta INTEGER"
            )

        cur.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'users'
              AND column_name = 'rating_gain_blocked_until'
            """
        )
        if cur.fetchone() is None:
            cur.execute(
                "ALTER TABLE users ADD COLUMN rating_gain_blocked_until TIMESTAMPTZ"
            )

        cur.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'finished_games'
              AND column_name = 'loser_rated_games_before'
            """
        )
        if cur.fetchone() is None:
            cur.execute(
                "ALTER TABLE finished_games ADD COLUMN loser_rated_games_before INTEGER"
            )
            cur.execute(
                "ALTER TABLE finished_games ADD COLUMN white_gain_capped "
                "BOOLEAN NOT NULL DEFAULT false"
            )
            cur.execute(
                "ALTER TABLE finished_games ADD COLUMN black_gain_capped "
                "BOOLEAN NOT NULL DEFAULT false"
            )

        cur.execute(
            """
            SELECT 1 FROM pg_constraint
            WHERE conname = 'uq_finished_games_room_started'
            """
        )
        if cur.fetchone() is None:
            cur.execute(
                "ALTER TABLE finished_games "
                "ADD CONSTRAINT uq_finished_games_room_started "
                "UNIQUE (room_id, started_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_finished_games_white_user_finished_at "
                "ON finished_games (white_user_id, finished_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_finished_games_black_user_finished_at "
                "ON finished_games (black_user_id, finished_at DESC)"
            )
    conn.close()


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: full-stack tests with Redis and PostgreSQL"
    )


def _skip_db_setup(items) -> bool:
    if not items:
        return False
    skip_only_files = {"test_nginx_config.py", "test_rules_contract.py", "test_ws_v2_protocol.py"}
    return all(
        getattr(item.path, "name", "") in skip_only_files for item in items
    )


@pytest.fixture(scope="session", autouse=True)
def ensure_test_db_schema(request):
    if _skip_db_setup(request.session.items):
        yield
        return

    from backend.db.session import create_all_tables

    asyncio.run(create_all_tables())
    _ensure_schema_patches()
    yield


@pytest.fixture(autouse=True)
def reset_redis_gauges_cache():
    from backend.observability.redis_metrics import invalidate_redis_gauges_cache

    invalidate_redis_gauges_cache()
    yield
    invalidate_redis_gauges_cache()


@pytest.fixture(autouse=True)
def reset_in_memory_room_state():
    """Prevent leaked room locks / timers from hanging later tests."""
    from backend import state

    state._room_locks.clear()
    for task in list(state.disconnect_timers.values()):
        if task is not None and hasattr(task, "cancel") and not task.done():
            task.cancel()
    state.disconnect_timers.clear()
    for task in list(state.game_timers.values()):
        if task is not None and hasattr(task, "cancel") and not task.done():
            task.cancel()
    state.game_timers.clear()
    yield
    state._room_locks.clear()
    state.disconnect_timers.clear()
    state.game_timers.clear()


@pytest.fixture
def starting_board():
    return get_starting_board()


@pytest.fixture
def sample_room_data():
    return {
        "room_id": "abcd1234",
        "type": "public",
        "game_started": False,
        "creator_client_id": "creator-1",
        "creator_color_preference": "белый",
        "time_control": 300,
        "increment": 5,
        "timer_white": 300.0,
        "timer_black": 300.0,
        "players": {},
    }


@pytest.fixture
def game_in_progress(starting_board):
    return {
        "board": starting_board,
        "mover": "белый",
        "game_over": False,
        "move_history": [],
        "pending_batyr_captures": [],
        "position_history": {},
        "moves_with_two_biys": 0,
    }
