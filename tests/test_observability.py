"""Health and metrics endpoint tests."""

import pytest
from fastapi.testclient import TestClient

from main import app


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


def test_health_ok(client, healthy_deps):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["redis"] == "ok"
    assert data["postgres"] == "ok"
    assert "uptime_seconds" in data


def test_health_degraded(client, monkeypatch):
    async def redis_down():
        return "down"

    async def postgres_ok():
        return "ok"

    monkeypatch.setattr("backend.observability.health.check_redis", redis_down)
    monkeypatch.setattr("backend.observability.health.check_postgres", postgres_ok)

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["redis"] == "down"


def test_health_postgres_down(client, monkeypatch):
    async def redis_ok():
        return "ok"

    async def postgres_down():
        return "down"

    monkeypatch.setattr("backend.observability.health.check_redis", redis_ok)
    monkeypatch.setattr("backend.observability.health.check_postgres", postgres_down)

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["postgres"] == "down"


def test_metrics_exposes_shatra_metrics(client, monkeypatch):
    async def noop_refresh():
        return None

    monkeypatch.setattr("main.refresh_redis_gauges", noop_refresh)
    monkeypatch.setattr("main.settings.metrics_token", "")

    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "shatra_ws_connections_active" in body
    assert "http_requests_total" in body
    assert "shatra_games_finished_total" in body
    assert "shatra_redis_rooms_active" in body
    assert "shatra_game_duration_seconds_bucket" in body


def test_metrics_requires_bearer_token_when_configured(client, monkeypatch):
    async def noop_refresh():
        return None

    monkeypatch.setattr("main.refresh_redis_gauges", noop_refresh)
    monkeypatch.setattr("main.settings.metrics_token", "secret-metrics-token")

    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401

    response = client.get(
        "/metrics",
        headers={"Authorization": "Bearer secret-metrics-token"},
    )
    assert response.status_code == 200
    assert "shatra_ws_connections_active" in response.text


def test_sentry_debug_not_exposed_without_dsn(client, monkeypatch):
    monkeypatch.setattr("main.settings.sentry_dsn", "")

    response = client.get("/sentry-debug")

    assert response.status_code == 404


def test_sentry_debug_not_exposed_in_production(client, monkeypatch):
    monkeypatch.setattr("main.settings.app_env", "production")
    monkeypatch.setattr("main.settings.sentry_dsn", "https://example@sentry.io/1")

    response = client.get("/sentry-debug")

    assert response.status_code == 404
