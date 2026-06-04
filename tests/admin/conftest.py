"""Fixtures for admin API tests."""

import uuid
from datetime import datetime, timedelta, timezone

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
def clean_admin_data():
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("TRUNCATE presence_sessions, finished_games, refresh_tokens, users CASCADE")
    conn.close()
    yield


@pytest.fixture
def register_user(client):
    def _register(username: str = "testuser", password: str = VALID_PASSWORD, **extra) -> dict:
        payload = {"username": username, "password": password, **extra}
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 200, r.text
        return r.json()

    return _register


@pytest.fixture
def regular_user(register_user):
    return register_user("regular")


@pytest.fixture
def regular_headers(regular_user):
    return {"Authorization": f"Bearer {regular_user['access_token']}"}


@pytest.fixture
def admin_user(register_user, client):
    data = register_user("adminuser")
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET is_admin = TRUE WHERE id = %s", (data["user"]["id"],))
    conn.close()
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200
    data["user"] = me.json()
    assert data["user"]["is_admin"] is True
    return data


@pytest.fixture
def admin_headers(admin_user):
    return {"Authorization": f"Bearer {admin_user['access_token']}"}


from tests.helpers.finished_games import insert_finished_game


def backdate_finished_game(room_id: str, finished_at: datetime) -> None:
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE finished_games SET finished_at = %s WHERE room_id = %s",
            (finished_at, room_id),
        )
    conn.close()


def set_presence_last_seen(client_id: str, last_seen_at: datetime) -> None:
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE presence_sessions SET last_seen_at = %s
            WHERE client_id = %s AND room_id IS NULL AND disconnected_at IS NULL
            """,
            (last_seen_at, client_id),
        )
    conn.close()


def set_user_created_at(user_id: str | uuid.UUID, created_at: datetime) -> None:
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET created_at = %s, updated_at = %s WHERE id = %s",
            (created_at, created_at, str(user_id)),
        )
    conn.close()


def insert_user_created_at(created_at: datetime) -> uuid.UUID:
    user_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (
                id, username, username_normalized, password_hash, is_admin, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, FALSE, %s, %s)
            """,
            (
                str(user_id),
                f"user_{user_id.hex[:8]}",
                f"user_{user_id.hex[:8]}",
                "hash",
                created_at,
                created_at,
            ),
        )
    conn.close()
    return user_id
