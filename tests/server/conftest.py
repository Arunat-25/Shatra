"""Fixtures for server tests that touch PostgreSQL finished_games."""

import psycopg2
import pytest
from fastapi.testclient import TestClient

import tests.test_env  # noqa: F401

from main import app
from tests.test_env import SYNC_DB_URL


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def ensure_users_for_room(room: dict) -> None:
    """Insert users referenced in player_meta so FK constraints pass."""
    meta = room.get("player_meta") or {}
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        for entry in meta.values():
            uid = entry.get("user_id")
            if not uid or entry.get("is_anonymous", True):
                continue
            uid_str = str(uid)
            username = f"archive_{uid_str.replace('-', '')[:16]}"
            cur.execute(
                """
                INSERT INTO users (
                    id, username, username_normalized, password_hash,
                    is_admin, created_at, updated_at
                ) VALUES (%s, %s, %s, 'hash', FALSE, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
                """,
                (uid_str, username, username.lower()),
            )
    conn.close()


@pytest.fixture(autouse=True)
def reset_ws_manager_connections():
    """Isolate unit tests from live WS rooms left by integration tests."""
    from backend.ws_manager import manager

    manager.connections.clear()
    yield
    manager.connections.clear()


@pytest.fixture(autouse=True)
def clean_finished_games_table():
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("TRUNCATE finished_games")
        cur.execute("TRUNCATE presence_sessions")
    conn.close()
    yield
