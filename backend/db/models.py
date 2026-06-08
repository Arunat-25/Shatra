"""SQLAlchemy-модели пользователей."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    username_normalized: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    rating: Mapped[int] = mapped_column(Integer, default=1200, server_default="1200")
    rated_games_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rating_gain_blocked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class FinishedGame(Base):
    __tablename__ = "finished_games"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id: Mapped[str] = mapped_column(String(8), index=True)
    room_type: Mapped[str] = mapped_column(String(16))

    white_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    black_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    white_client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    black_client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    white_is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    black_is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    white_user: Mapped[User | None] = relationship(foreign_keys=[white_user_id])
    black_user: Mapped[User | None] = relationship(foreign_keys=[black_user_id])

    winner_color: Mapped[str | None] = mapped_column(String(8), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(32), nullable=True)

    time_control: Mapped[int | None] = mapped_column(Integer, nullable=True)
    increment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timer_white_final: Mapped[float | None] = mapped_column(Float, nullable=True)
    timer_black_final: Mapped[float | None] = mapped_column(Float, nullable=True)

    moves_count: Mapped[int] = mapped_column(Integer, default=0)
    move_history: Mapped[list] = mapped_column(JSONB, default=list)
    final_board: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    is_rated: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    white_rating_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    black_rating_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loser_rated_games_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    white_gain_capped: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    black_gain_capped: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class PresenceSession(Base):
    __tablename__ = "presence_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    room_id: Mapped[str | None] = mapped_column(String(8), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class BugReport(Base):
    __tablename__ = "bug_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    screenshot: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    screenshot_mime: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    client_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    page_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    user: Mapped[User | None] = relationship(foreign_keys=[user_id])
