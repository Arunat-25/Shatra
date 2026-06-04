"""Fixtures for REST → WebSocket → PostgreSQL integration tests."""

import uuid

import psycopg2
import pytest
from fastapi.testclient import TestClient

import tests.test_env  # noqa: F401

from main import app
from tests.db.conftest import register
from tests.integration.helpers import flush_redis, new_client_id
from tests.test_env import SYNC_DB_URL


def _reset_lobby_chat_sync() -> None:
    """Сброс без asyncio.run — иначе redis_client привязывается к закрытому loop."""
    import backend.lobby_chat as lobby_chat_mod
    from backend.lobby_chat import lobby_chat_manager

    lobby_chat_manager.connections.clear()
    lobby_chat_mod._memory_messages = []
    flush_redis()


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: full-stack tests with Redis and PostgreSQL"
    )


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_db_and_redis():
    _reset_lobby_chat_sync()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE presence_sessions, finished_games, refresh_tokens, users CASCADE"
        )
    conn.close()
    yield
    _reset_lobby_chat_sync()


@pytest.fixture
def auth_user_factory(client):
    def _factory(username: str | None = None) -> dict:
        name = username or f"user_{uuid.uuid4().hex[:8]}"
        data = register(client, name)
        return {
            "username": name,
            "user_id": data["user"]["id"],
            "access_token": data["access_token"],
            "client_id": new_client_id(),
        }

    return _factory
