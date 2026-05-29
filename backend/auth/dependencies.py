"""FastAPI-зависимости для аутентификации."""

import uuid

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt_utils import decode_token
from backend.auth.service import user_to_public
from backend.auth.schemas import UserPublic
from backend.db.models import User
from backend.db.session import get_db
from backend.message_codes import (
    AUTH_INVALID_TOKEN,
    AUTH_REQUIRED,
    AUTH_USER_NOT_FOUND,
)

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail=AUTH_REQUIRED)
    try:
        payload = decode_token(credentials.credentials, "access")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail=AUTH_INVALID_TOKEN) from None

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail=AUTH_USER_NOT_FOUND)
    return user


async def get_current_user_public(
    user: User = Depends(get_current_user),
) -> UserPublic:
    return user_to_public(user)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    try:
        payload = decode_token(credentials.credentials, "access")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        return None
    return await db.get(User, user_id)
