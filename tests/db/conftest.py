"""Fixtures for cross-table PostgreSQL persistence tests."""

import uuid

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
def clean_all_tables():
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE presence_sessions, finished_games, refresh_tokens, users CASCADE"
        )
    conn.close()
    yield


def db_scalar(sql: str, params=()) -> int:
    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def db_fetchone(sql: str, params=()) -> tuple | None:
    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    conn.close()
    return row


def db_fetchall(sql: str, params=()) -> list[tuple]:
    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    conn.close()
    return rows


def register(client, username: str = "dbuser", **extra) -> dict:
    payload = {"username": username, "password": VALID_PASSWORD, **extra}
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def login(client, username: str) -> dict:
    r = client.post(
        "/api/auth/login",
        json={"username": username, "password": VALID_PASSWORD},
    )
    assert r.status_code == 200, r.text
    return r.json()
