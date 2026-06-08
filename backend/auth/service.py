"""Бизнес-логика аутентификации."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.message_codes import (
    AUTH_INVALID_CREDENTIALS,
    AUTH_SESSION_EXPIRED,
    AUTH_USER_NOT_FOUND,
    AUTH_USERNAME_TAKEN_PROFILE,
    AUTH_USERNAME_TAKEN_REGISTER,
    AUTH_WRONG_PASSWORD,
)
from backend.auth.jwt_utils import (
    create_access_token,
    generate_refresh_token_plain,
    hash_refresh_token,
    refresh_token_expires_at,
)
from backend.auth.passwords import hash_password, verify_password
from backend.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)
from backend.auth.constants import DISTRICTS
from backend.config import settings
from backend.db.models import RefreshToken, User

logger = logging.getLogger(__name__)


def _normalize_username(username: str) -> str:
    return username.strip().lower()


async def _ensure_username_available(
    db: AsyncSession,
    username: str,
    *,
    exclude_user_id: uuid.UUID | None = None,
    taken_message: str = AUTH_USERNAME_TAKEN_PROFILE,
) -> tuple[str, str]:
    """Проверить уникальность; вернуть (отображаемое имя, normalized)."""
    display = username.strip()
    normalized = _normalize_username(display)
    query = select(User).where(User.username_normalized == normalized)
    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)
    if await db.scalar(query):
        raise HTTPException(status_code=409, detail=taken_message)
    return display, normalized


async def register(db: AsyncSession, body: RegisterRequest) -> TokenResponse:
    display, username_norm = await _ensure_username_available(
        db, body.username, taken_message=AUTH_USERNAME_TAKEN_REGISTER
    )

    user = User(
        username=display,
        username_normalized=username_norm,
        password_hash=hash_password(body.password),
        first_name=body.first_name.strip() if body.first_name else None,
        last_name=body.last_name.strip() if body.last_name else None,
        district=body.district,
    )
    db.add(user)
    await db.flush()
    return await _issue_tokens(db, user)


async def login(db: AsyncSession, body: LoginRequest) -> TokenResponse:
    username_norm = _normalize_username(body.username)
    user = await db.scalar(select(User).where(User.username_normalized == username_norm))
    if not user or not verify_password(body.password, user.password_hash):
        logger.warning(
            "Login failed for username=%s",
            username_norm,
            extra={"username": username_norm},
        )
        raise HTTPException(status_code=401, detail=AUTH_INVALID_CREDENTIALS)
    return await _issue_tokens(db, user)


async def refresh_session(db: AsyncSession, refresh_token: str) -> TokenResponse:
    token_hash = hash_refresh_token(refresh_token)
    now = datetime.now(timezone.utc)
    row = await db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .where(RefreshToken.revoked_at.is_(None))
        .where(RefreshToken.expires_at > now)
    )
    if not row:
        raise HTTPException(status_code=401, detail=AUTH_SESSION_EXPIRED)

    row.revoked_at = now
    user = await db.get(User, row.user_id)
    if not user:
        raise HTTPException(status_code=401, detail=AUTH_USER_NOT_FOUND)
    return await _issue_tokens(db, user)


async def change_password(db: AsyncSession, user: User, body: ChangePasswordRequest) -> None:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail=AUTH_WRONG_PASSWORD)
    user.password_hash = hash_password(body.new_password)
    user.updated_at = datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)
    tokens = (
        await db.scalars(
            select(RefreshToken)
            .where(RefreshToken.user_id == user.id)
            .where(RefreshToken.revoked_at.is_(None))
        )
    ).all()
    for t in tokens:
        t.revoked_at = now


async def logout(db: AsyncSession, refresh_token: str) -> None:
    token_hash = hash_refresh_token(refresh_token)
    now = datetime.now(timezone.utc)
    row = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if row and row.revoked_at is None:
        row.revoked_at = now


async def update_profile(db: AsyncSession, user: User, body: ProfileUpdateRequest) -> UserPublic:
    if body.username is not None:
        display, normalized = await _ensure_username_available(
            db, body.username, exclude_user_id=user.id
        )
        user.username = display
        user.username_normalized = normalized
    if body.first_name is not None:
        user.first_name = body.first_name.strip() or None
    if body.last_name is not None:
        user.last_name = body.last_name.strip() or None
    if body.district is not None:
        user.district = body.district
    user.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return user_to_public(user)


def is_user_admin(user: User) -> bool:
    if user.is_admin:
        return True
    return str(user.id) in settings.admin_user_id_set


def user_to_public(user: User) -> UserPublic:
    return UserPublic.model_validate(user).model_copy(update={"is_admin": is_user_admin(user)})


async def _issue_tokens(db: AsyncSession, user: User) -> TokenResponse:
    access = create_access_token(user.id)
    plain_refresh = generate_refresh_token_plain()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(plain_refresh),
            expires_at=refresh_token_expires_at(),
        )
    )
    await db.commit()
    await db.refresh(user)
    return TokenResponse(
        access_token=access,
        refresh_token=plain_refresh,
        user=user_to_public(user),
    )


def list_districts() -> list[str]:
    return list(DISTRICTS)
