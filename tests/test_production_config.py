"""Production startup validation."""

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings, validate_production_settings
from main import app


def test_validate_production_rejects_default_jwt_secret():
    cfg = Settings(app_env="production", jwt_secret="change-me-in-production")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_production_settings(cfg)


def test_validate_production_rejects_empty_jwt_secret():
    cfg = Settings(app_env="production", jwt_secret="")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_production_settings(cfg)


def test_validate_production_accepts_strong_jwt_secret():
    validate_production_settings(
        Settings(app_env="production", jwt_secret="a" * 32, metrics_token="metrics-secret"),
    )


def test_validate_production_rejects_empty_metrics_token():
    cfg = Settings(app_env="production", jwt_secret="a" * 32, metrics_token="")
    with pytest.raises(RuntimeError, match="METRICS_TOKEN"):
        validate_production_settings(cfg)


def test_validate_development_allows_default_jwt_secret():
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
