"""Метаданные игроков в комнате (аноним vs аккаунт)."""

import uuid

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt_utils import decode_token
from backend.db.models import User
from backend.rating.elo import DEFAULT_RATING


def meta_from_user(user: User | None) -> dict:
    if user:
        return {
            "user_id": str(user.id),
            "username": user.username,
            "is_anonymous": False,
            "rating": user.rating,
        }
    return {"user_id": None, "username": None, "is_anonymous": True, "rating": None}


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
        entry = {
            "client_id": client_id,
            "color": color,
            "username": meta.get("username"),
            "is_anonymous": meta.get("is_anonymous", True),
            "display_name": display_name(meta),
        }
        if not entry["is_anonymous"]:
            entry["rating"] = meta.get("rating", DEFAULT_RATING)
        info.append(entry)
    return info


async def refresh_player_ratings_in_room(room_data: dict, db: AsyncSession) -> None:
    """Подтянуть актуальный рейтинг из БД перед стартом / resync PvP."""
    meta_map = room_data.get("player_meta") or {}
    user_ids: list[uuid.UUID] = []
    client_by_uid: dict[uuid.UUID, str] = {}
    for client_id, meta in meta_map.items():
        if meta.get("is_anonymous", True):
            continue
        uid = user_id_from_meta(meta)
        if uid is None:
            continue
        user_ids.append(uid)
        client_by_uid[uid] = client_id
    if not user_ids:
        return

    rows = (
        await db.scalars(select(User).where(User.id.in_(user_ids)))
    ).all()
    for user in rows:
        client_id = client_by_uid.get(user.id)
        if not client_id:
            continue
        meta_map[client_id] = {
            **meta_map.get(client_id, {}),
            **meta_from_user(user),
        }
    room_data["player_meta"] = meta_map


async def refresh_pvp_ratings_for_room(room_data: dict) -> None:
    """Load current ratings from DB for registered players in a PvP room."""
    if room_data.get("type") not in ("public", "private"):
        return
    from backend.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as db:
        await refresh_player_ratings_in_room(room_data, db)


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
