"""Production startup validation."""

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings, validate_production_settings
from main import app

_VALID_PROD_SETTINGS = {
    "app_env": "production",
    "jwt_secret": "a" * 32,
    "metrics_token": "metrics-secret",
    "database_url": "postgresql+asyncpg://user:pass@db.example.com/neondb",
    "redis_url": "rediss://default:pass@redis.example.com:6379",
}


def test_validate_production_rejects_default_jwt_secret():
    cfg = Settings(app_env="production", jwt_secret="change-me-in-production")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_production_settings(cfg)


def test_validate_production_rejects_empty_jwt_secret():
    cfg = Settings(app_env="production", jwt_secret="")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_production_settings(cfg)


def test_validate_production_accepts_valid_settings():
    validate_production_settings(Settings(**_VALID_PROD_SETTINGS))


def test_validate_production_rejects_empty_metrics_token():
    cfg = Settings(**{**_VALID_PROD_SETTINGS, "metrics_token": ""})
    with pytest.raises(RuntimeError, match="METRICS_TOKEN"):
        validate_production_settings(cfg)


def test_validate_production_rejects_default_database_url():
    cfg = Settings(**{**_VALID_PROD_SETTINGS, "database_url": "postgresql+asyncpg://shatra:shatra@localhost:5432/shatra"})
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        validate_production_settings(cfg)


def test_validate_production_rejects_empty_database_url():
    cfg = Settings(**{**_VALID_PROD_SETTINGS, "database_url": ""})
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        validate_production_settings(cfg)


def test_validate_production_rejects_empty_redis_url():
    cfg = Settings(**{**_VALID_PROD_SETTINGS, "redis_url": ""})
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        validate_production_settings(cfg)


def test_validate_development_allows_local_defaults():
    validate_production_settings(
        Settings(app_env="development", jwt_secret="change-me-in-production"),
    )


def test_app_starts_in_development_with_default_jwt(monkeypatch):
    monkeypatch.setattr("main.settings.app_env", "development")
    monkeypatch.setattr("main.settings.jwt_secret", "change-me-in-production")

    with TestClient(app) as client:
        assert client.get("/health").status_code in (200, 503)


def test_app_fails_startup_in_production_with_default_jwt(monkeypatch):
    monkeypatch.setattr("main.settings.app_env", "production")
    monkeypatch.setattr("main.settings.jwt_secret", "change-me-in-production")

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        with TestClient(app):
            pass


def test_app_fails_startup_in_production_with_default_database_url(monkeypatch):
    monkeypatch.setattr("main.settings.app_env", "production")
    monkeypatch.setattr("main.settings.jwt_secret", "a" * 32)
    monkeypatch.setattr("main.settings.metrics_token", "metrics-secret")
    monkeypatch.setattr(
        "main.settings.database_url",
        "postgresql+asyncpg://shatra:shatra@localhost:5432/shatra",
    )

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        with TestClient(app):
            pass
