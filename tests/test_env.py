"""Изолированное окружение для pytest (отдельная БД и Redis DB)."""

from __future__ import annotations

import os

DEFAULT_TEST_DATABASE_URL = (
    "postgresql+asyncpg://shatra:shatra@localhost:5432/shatra_test"
)


def test_database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


def sync_db_url(async_url: str | None = None) -> str:
    url = async_url or test_database_url()
    return url.replace("postgresql+asyncpg://", "postgresql://")


SYNC_DB_URL = sync_db_url()


def configure_test_env() -> None:
    """Вызывается при импорте conftest — тесты не трогают dev-базу shatra."""
    os.environ["DATABASE_URL"] = test_database_url()
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ.setdefault("REDIS_HOST", "localhost")
    os.environ.setdefault("REDIS_PORT", "6379")
    os.environ.setdefault("REDIS_DB", "1")


configure_test_env()
