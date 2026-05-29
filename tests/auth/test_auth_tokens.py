"""Тесты срока жизни и работоспособности JWT / refresh-токенов."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from backend.auth.jwt_utils import (
    ALGORITHM,
    create_access_token,
    decode_token,
    hash_refresh_token,
    refresh_token_expires_at,
)
from backend.config import settings
from tests.auth.conftest import VALID_PASSWORD, expire_refresh_token_in_db


def _expired_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) - timedelta(seconds=1)
    payload = {"sub": str(user_id), "type": "access", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def _access_token_wrong_secret(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"sub": str(user_id), "type": "access", "exp": expire}
    return jwt.encode(payload, "wrong-secret-key", algorithm=ALGORITHM)


def _access_token_wrong_type(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"sub": str(user_id), "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def _access_token_missing_sub() -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"type": "access", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def _access_token_unknown_user() -> str:
    return create_access_token(uuid.uuid4())


# --- Юнит-тесты JWT ---


class TestAccessTokenLifetime:
    def test_exp_claim_matches_config(self, monkeypatch):
        monkeypatch.setattr(settings, "jwt_access_expire_minutes", 15)
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = exp - now
        assert timedelta(minutes=14) < delta < timedelta(minutes=16)

    def test_token_valid_immediately_after_creation(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        payload = decode_token(token, "access")
        assert payload["sub"] == str(user_id)

    def test_token_invalid_one_second_after_expiry(self):
        user_id = uuid.uuid4()
        expire = datetime.now(timezone.utc) - timedelta(seconds=1)
        payload = {"sub": str(user_id), "type": "access", "exp": expire}
        token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(token, "access")

    def test_wrong_secret_rejected(self):
        user_id = uuid.uuid4()
        token = _access_token_wrong_secret(user_id)
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(token, "access")


class TestRefreshTokenLifetime:
    def test_expires_at_respects_config_days(self, monkeypatch):
        monkeypatch.setattr(settings, "jwt_refresh_expire_days", 7)
        exp = refresh_token_expires_at()
        now = datetime.now(timezone.utc)
        assert timedelta(days=6, hours=23) < (exp - now) < timedelta(days=7, hours=1)


# --- API: просроченный access JWT ---


class TestExpiredAccessTokenApi:
    @pytest.mark.parametrize(
        "method,path,json_body",
        [
            ("get", "/api/auth/me", None),
            ("patch", "/api/auth/me", {"first_name": "X"}),
        ],
    )
    def test_protected_routes_reject_expired_access(
        self, client, auth_user, method, path, json_body
    ):
        user_id = uuid.UUID(auth_user["user"]["id"])
        headers = {"Authorization": f"Bearer {_expired_access_token(user_id)}"}
        if method == "get":
            r = client.get(path, headers=headers)
        else:
            r = client.patch(path, headers=headers, json=json_body)
        assert r.status_code == 401

    def test_expired_access_cannot_refresh_via_access_endpoint(self, client, auth_user):
        user_id = uuid.UUID(auth_user["user"]["id"])
        r = client.post(
            "/api/auth/refresh",
            json={"refresh_token": _expired_access_token(user_id)},
        )
        assert r.status_code == 401

    def test_wrong_secret_token_rejected(self, client, auth_user):
        user_id = uuid.UUID(auth_user["user"]["id"])
        r = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {_access_token_wrong_secret(user_id)}"},
        )
        assert r.status_code == 401

    def test_wrong_type_in_jwt_rejected(self, client, auth_user):
        user_id = uuid.UUID(auth_user["user"]["id"])
        r = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {_access_token_wrong_type(user_id)}"},
        )
        assert r.status_code == 401

    def test_missing_sub_rejected(self, client):
        r = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {_access_token_missing_sub()}"},
        )
        assert r.status_code == 401

    def test_unknown_user_in_sub_rejected(self, client):
        r = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {_access_token_unknown_user()}"},
        )
        assert r.status_code == 401


# --- API: просроченный refresh в БД ---


class TestExpiredRefreshTokenApi:
    def test_expired_refresh_in_db_returns_401(self, client, auth_user):
        refresh = auth_user["refresh_token"]
        expire_refresh_token_in_db(refresh)
        r = client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert r.status_code == 401
        assert "сессия" in r.json()["detail"].lower() or "истек" in r.json()["detail"].lower()

    def test_expired_refresh_cannot_access_me_even_if_access_valid(
        self, client, auth_user, auth_headers
    ):
        """Просроченный refresh не продлевает сессию; текущий access ещё жив."""
        expire_refresh_token_in_db(auth_user["refresh_token"])
        r_me = client.get("/api/auth/me", headers=auth_headers)
        assert r_me.status_code == 200

        r_refresh = client.post(
            "/api/auth/refresh",
            json={"refresh_token": auth_user["refresh_token"]},
        )
        assert r_refresh.status_code == 401


# --- Восстановление сессии через refresh ---


class TestRefreshRestoresSession:
    def test_refresh_after_access_expired_issues_working_access(self, client, register_user):
        data = register_user("refresh_after_exp")
        user_id = uuid.UUID(data["user"]["id"])
        expired_headers = {
            "Authorization": f"Bearer {_expired_access_token(user_id)}",
        }
        assert client.get("/api/auth/me", headers=expired_headers).status_code == 401

        r = client.post(
            "/api/auth/refresh",
            json={"refresh_token": data["refresh_token"]},
        )
        assert r.status_code == 200
        new_access = r.json()["access_token"]
        new_headers = {"Authorization": f"Bearer {new_access}"}
        assert client.get("/api/auth/me", headers=new_headers).status_code == 200

    def test_chain_of_three_refreshes(self, client, auth_user):
        refresh = auth_user["refresh_token"]
        tokens = [refresh]
        last_response = None
        for _ in range(3):
            last_response = client.post(
                "/api/auth/refresh", json={"refresh_token": tokens[-1]}
            )
            assert last_response.status_code == 200
            tokens.append(last_response.json()["refresh_token"])

        for old in tokens[:-1]:
            r = client.post("/api/auth/refresh", json={"refresh_token": old})
            assert r.status_code == 401

        last_access = last_response.json()["access_token"]
        assert (
            client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {last_access}"},
            ).status_code
            == 200
        )

    def test_login_issues_fresh_tokens_after_refresh_revoked(self, client, register_user):
        data = register_user("relogin_user")
        client.post(
            "/api/auth/logout",
            json={"refresh_token": data["refresh_token"]},
        )
        r = client.post(
            "/api/auth/login",
            json={"username": "relogin_user", "password": VALID_PASSWORD},
        )
        assert r.status_code == 200
        new = r.json()
        assert client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {new['access_token']}"},
        ).status_code == 200


# --- Выданные при регистрации/входе токены ---


class TestIssuedTokens:
    def test_register_access_token_decodable_with_future_exp(self, client):
        r = client.post(
            "/api/auth/register",
            json={"username": "token_check", "password": VALID_PASSWORD},
        )
        token = r.json()["access_token"]
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
        assert payload["type"] == "access"
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert exp > datetime.now(timezone.utc)

    def test_login_refresh_stored_with_future_expires_at(self, client, register_user):
        data = register_user("db_exp_user")
        token_hash = hash_refresh_token(data["refresh_token"])
        import psycopg2

        from tests.auth.conftest import SYNC_DB_URL

        conn = psycopg2.connect(SYNC_DB_URL)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT expires_at, revoked_at FROM refresh_tokens WHERE token_hash = %s",
                (token_hash,),
            )
            row = cur.fetchone()
        conn.close()
        assert row is not None
        expires_at, revoked_at = row
        assert revoked_at is None
        assert expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)
