"""Tests for HTTP observability middleware."""

import pytest
from fastapi.testclient import TestClient

from backend.observability.metrics import HTTP_REQUESTS_TOTAL
from backend.observability.middleware import _should_skip, normalize_path
from main import app


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/rooms/abc123/join", "/rooms/{room_id}/join"),
        ("/rooms/xyz/status", "/rooms/{room_id}/status"),
        ("/rooms", "/rooms"),
        ("/api/auth/login", "/api/auth/login"),
    ],
)
def test_normalize_path(path, expected):
    assert normalize_path(path) == expected


@pytest.mark.parametrize(
    ("path", "skipped"),
    [
        ("/health", True),
        ("/metrics", True),
        ("/assets/main.js", True),
        ("/sounds/piano/Move.ogg", True),
        ("/rooms", False),
    ],
)
def test_should_skip(path, skipped):
    assert _should_skip(path) is skipped


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def healthy_deps(monkeypatch):
    async def ok():
        return "ok"

    monkeypatch.setattr("backend.observability.health.check_redis", ok)
    monkeypatch.setattr("backend.observability.health.check_postgres", ok)


def test_middleware_adds_request_id(client, healthy_deps):
    response = client.get("/rooms")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_middleware_preserves_incoming_request_id(client, healthy_deps):
    response = client.get("/rooms", headers={"X-Request-ID": "fixed-id-123"})
    assert response.headers["X-Request-ID"] == "fixed-id-123"


def test_health_skips_middleware_headers(client, healthy_deps):
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" not in response.headers


def test_middleware_increments_http_requests_total(client, healthy_deps):
    label = HTTP_REQUESTS_TOTAL.labels(method="GET", path="/rooms", status="200")
    before = label._value.get()
    client.get("/rooms")
    assert label._value.get() == before + 1
