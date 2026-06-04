"""Фикстуры для тестов аутентификации."""

import psycopg2
import pytest
from fastapi.testclient import TestClient

import tests.test_env  # noqa: F401

from main import app
from tests.test_env import SYNC_DB_URL

VALID_PASSWORD = "secret12"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_auth_data():
    """TRUNCATE users перед каждым тестом в tests/auth (без поднятия TestClient)."""
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("TRUNCATE finished_games, refresh_tokens, users CASCADE")
    conn.close()
    yield


@pytest.fixture
def register_user(client):
    """Фабрика: регистрация пользователя, возвращает TokenResponse JSON."""

    def _register(
        username: str = "testuser",
        password: str = VALID_PASSWORD,
        **extra,
    ) -> dict:
        payload = {"username": username, "password": password, **extra}
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 200, r.text
        return r.json()

    return _register


@pytest.fixture
def auth_user(register_user):
    """Зарегистрированный пользователь с токенами."""
    return register_user("auth_user", VALID_PASSWORD)


@pytest.fixture
def auth_headers(auth_user):
    return {"Authorization": f"Bearer {auth_user['access_token']}"}


def expire_refresh_token_in_db(refresh_token_plain: str) -> None:
    """Пометить refresh-токен в БД как просроченный."""
    from datetime import datetime, timedelta, timezone

    from backend.auth.jwt_utils import hash_refresh_token

    token_hash = hash_refresh_token(refresh_token_plain)
    past = datetime.now(timezone.utc) - timedelta(days=1)
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE refresh_tokens SET expires_at = %s WHERE token_hash = %s",
            (past, token_hash),
        )
    conn.close()
