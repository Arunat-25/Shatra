"""Юнит-тесты JWT и хэширования паролей."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from backend.auth.jwt_utils import (
    ALGORITHM,
    create_access_token,
    decode_token,
    generate_refresh_token_plain,
    hash_refresh_token,
    refresh_token_expires_at,
)
from backend.auth.passwords import hash_password, verify_password
from backend.config import settings


class TestPasswords:
    def test_hash_and_verify_success(self):
        hashed = hash_password("mySecret99")
        assert hashed != "mySecret99"
        assert verify_password("mySecret99", hashed)

    def test_verify_wrong_password(self):
        hashed = hash_password("correct12")
        assert not verify_password("wrong12", hashed)

    def test_same_password_different_hashes(self):
        h1 = hash_password("samepass1")
        h2 = hash_password("samepass1")
        assert h1 != h2


class TestJwtUtils:
    def test_access_token_roundtrip(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        payload = decode_token(token, "access")
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_wrong_token_type_rejected(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(token, "refresh")

    def test_expired_token_rejected(self):
        user_id = uuid.uuid4()
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {"sub": str(user_id), "type": "access", "exp": expire}
        token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(token, "access")

    def test_tampered_token_rejected(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        parts = token.split(".")
        parts[1] = parts[1][:-2] + "XX"
        bad = ".".join(parts)
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(bad, "access")

    def test_refresh_token_plain_unique(self):
        a = generate_refresh_token_plain()
        b = generate_refresh_token_plain()
        assert a != b
        assert len(a) > 20

    def test_hash_refresh_token_deterministic(self):
        plain = "test-refresh-token"
        assert hash_refresh_token(plain) == hash_refresh_token(plain)
        assert hash_refresh_token(plain) != hash_refresh_token(plain + "x")

    def test_refresh_expires_in_future(self):
        assert refresh_token_expires_at() > datetime.now(timezone.utc)

    def test_access_token_not_valid_as_refresh_type(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(token, "refresh")

    def test_decode_rejects_malformed_string(self):
        with pytest.raises(jwt.DecodeError):
            decode_token("not.a.jwt", "access")
