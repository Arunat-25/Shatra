"""Fixtures for bug report API tests."""

import psycopg2
import pytest
from fastapi.testclient import TestClient

import tests.test_env  # noqa: F401

from main import app
from tests.test_env import SYNC_DB_URL

VALID_PASSWORD = "secret12"

MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_bug_report_data():
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("TRUNCATE bug_reports, refresh_tokens, users CASCADE")
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
    return data


@pytest.fixture
def admin_headers(admin_user):
    return {"Authorization": f"Bearer {admin_user['access_token']}"}
