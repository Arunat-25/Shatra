"""Метаданные игроков в комнате (аноним vs аккаунт)."""

import uuid

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt_utils import decode_token
from backend.db.models import User


def meta_from_user(user: User | None) -> dict:
    if user:
        return {
            "user_id": str(user.id),
            "username": user.username,
            "is_anonymous": False,
        }
    return {"user_id": None, "username": None, "is_anonymous": True}


def merge_player_meta(existing: dict | None, user: User | None) -> dict:
    """WS без токена не затирает аккаунт, записанный при REST create room."""
    if user is not None:
        return meta_from_user(user)
    if existing and existing.get("user_id") and not existing.get("is_anonymous", True):
        return dict(existing)
    return meta_from_user(None)


def user_id_from_meta(meta: dict | None) -> uuid.UUID | None:
    if not meta:
        return None
    raw = meta.get("user_id")
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        return None


def display_name(meta: dict | None) -> str:
    if not meta:
        return "Аноним"
    if meta.get("is_anonymous") or not meta.get("username"):
        return "Аноним"
    return meta["username"]


def build_players_info(room_data: dict) -> list[dict]:
    players = room_data.get("players") or {}
    meta_map = room_data.get("player_meta") or {}
    info = []
    for client_id, color in players.items():
        meta = meta_map.get(client_id) or {}
        info.append({
            "client_id": client_id,
            "color": color,
            "username": meta.get("username"),
            "is_anonymous": meta.get("is_anonymous", True),
            "display_name": display_name(meta),
        })
    return info


async def resolve_user_from_access_token(
    token: str | None,
    db: AsyncSession,
) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token, "access")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        return None
    return await db.get(User, user_id)
