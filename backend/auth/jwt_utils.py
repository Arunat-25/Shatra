"""JWT: access и refresh."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from backend.config import settings

ALGORITHM = "HS256"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: uuid.UUID) -> str:
    expire = _utcnow() + timedelta(minutes=settings.jwt_access_expire_minutes)
    payload = {"sub": str(user_id), "type": "access", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def generate_refresh_token_plain() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(f"{token}{settings.jwt_secret}".encode()).hexdigest()


def refresh_token_expires_at() -> datetime:
    return _utcnow() + timedelta(days=settings.jwt_refresh_expire_days)
