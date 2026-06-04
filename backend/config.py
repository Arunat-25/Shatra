"""Централизованная конфигурация (pydantic-settings + .env)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    sentry_dsn: str = ""

    database_url: str = "postgresql+asyncpg://shatra:shatra@localhost:5432/shatra"

    jwt_secret: str = "change-me-in-production"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 30

    admin_user_ids: str = ""

    @property
    def admin_user_id_set(self) -> frozenset[str]:
        if not self.admin_user_ids.strip():
            return frozenset()
        return frozenset(part.strip() for part in self.admin_user_ids.split(",") if part.strip())


settings = Settings()
