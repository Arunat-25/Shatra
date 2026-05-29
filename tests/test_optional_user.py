"""Тесты get_optional_user и resolve_user_from_access_token."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from fastapi.security import HTTPAuthorizationCredentials

from backend.auth.dependencies import get_optional_user
from backend.auth.jwt_utils import ALGORITHM, create_access_token
from backend.config import settings
from backend.player_identity import (
    build_players_info,
    display_name,
    meta_from_user,
    resolve_user_from_access_token,
)


@pytest.mark.asyncio
class TestGetOptionalUser:
    async def test_no_credentials_returns_none(self):
        db = AsyncMock()
        assert await get_optional_user(None, db) is None
        db.get.assert_not_called()

    async def test_wrong_scheme_returns_none(self):
        creds = HTTPAuthorizationCredentials(scheme="Basic", credentials="x")
        db = AsyncMock()
        assert await get_optional_user(creds, db) is None

    async def test_invalid_jwt_returns_none(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token.here")
        db = AsyncMock()
        assert await get_optional_user(creds, db) is None

    async def test_valid_token_loads_user(self):
        user_id = uuid.uuid4()
        user = MagicMock()
        user.id = user_id
        db = AsyncMock()
        db.get = AsyncMock(return_value=user)
        token = create_access_token(user_id)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        from backend.db.models import User

        result = await get_optional_user(creds, db)
        assert result is user
        db.get.assert_awaited_once_with(User, user_id)

    async def test_refresh_token_type_rejected(self):
        """Refresh JWT (если бы был) не должен проходить как access."""
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        payload = {"sub": str(uuid.uuid4()), "type": "refresh", "exp": expire}
        token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        db = AsyncMock()
        assert await get_optional_user(creds, db) is None


@pytest.mark.asyncio
class TestResolveUserFromAccessToken:
    async def test_none_token(self):
        db = AsyncMock()
        assert await resolve_user_from_access_token(None, db) is None

    async def test_garbage_token(self):
        db = AsyncMock()
        assert await resolve_user_from_access_token("not-jwt", db) is None

    async def test_deleted_user_returns_none(self):
        user_id = uuid.uuid4()
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        token = create_access_token(user_id)
        assert await resolve_user_from_access_token(token, db) is None


class TestPlayerIdentityHelpers:
    def test_display_name_anonymous_when_flag_set(self):
        assert display_name({"username": "x", "is_anonymous": True}) == "Аноним"

    def test_display_name_without_meta(self):
        assert display_name(None) == "Аноним"
        assert display_name({}) == "Аноним"

    def test_meta_from_user_serializes_uuid(self):
        user = MagicMock()
        user.id = uuid.uuid4()
        user.username = "Тест"
        meta = meta_from_user(user)
        assert meta["user_id"] == str(user.id)
        assert meta["is_anonymous"] is False

    def test_build_players_info_empty_room(self):
        assert build_players_info({"players": {}}) == []

    def test_build_players_info_defaults_missing_meta_to_anonymous(self):
        info = build_players_info({"players": {"cid": "белый"}, "player_meta": {}})
        assert len(info) == 1
        assert info[0]["is_anonymous"] is True
        assert info[0]["display_name"] == "Аноним"

    def test_build_players_info_preserves_color(self):
        info = build_players_info({
            "players": {"a": "черный"},
            "player_meta": {"a": {"username": "bob", "is_anonymous": False}},
        })
        assert info[0]["color"] == "черный"
        assert info[0]["client_id"] == "a"
