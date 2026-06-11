"""Централизованная конфигурация (pydantic-settings + .env)."""

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_DEFAULT_JWT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    redis_url: str = ""
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_ttl_seconds: int = 4 * 60 * 60

    disconnect_timeout: int = 30
    empty_room_grace_seconds: float = 2.0
    tick_interval_seconds: float = 1.0
    # Закрыть lobby-presence без poll дольше N с (очистка orphan строк, не задержка ухода).
    lobby_presence_stale_seconds: int = 6

    cors_allow_origins: str = "*"

    log_level: str = "INFO"
    log_format: str = "text"

    app_env: str = "development"
    app_version: str = "dev"

    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    database_url: str = "postgresql+asyncpg://shatra:shatra@localhost:5432/shatra"

    metrics_token: str = ""

    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 30

    admin_user_ids: str = ""

    @property
    def admin_user_id_set(self) -> frozenset[str]:
        if not self.admin_user_ids.strip():
            return frozenset()
        return frozenset(part.strip() for part in self.admin_user_ids.split(",") if part.strip())


def validate_production_settings(cfg: Settings) -> None:
    """Fail fast on unsafe defaults when APP_ENV=production."""
    if cfg.app_env != "production":
        return

    secret = (cfg.jwt_secret or "").strip()
    if not secret or secret == _DEFAULT_JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET must be set to a strong random value when APP_ENV=production"
        )

    if not (cfg.metrics_token or "").strip():
        raise RuntimeError(
            "METRICS_TOKEN must be set when APP_ENV=production"
        )

    if cfg.cors_allow_origins.strip() == "*":
        logger.warning(
            "CORS_ALLOW_ORIGINS is '*' in production; set explicit origins if API is split from frontend"
        )


settings = Settings()
