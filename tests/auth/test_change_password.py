"""Расширенные тесты смены пароля: сессии, граничные случаи, изоляция."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from backend.auth.jwt_utils import ALGORITHM, hash_refresh_token
from backend.auth.passwords import verify_password
from backend.config import settings
from tests.auth.conftest import SYNC_DB_URL, VALID_PASSWORD
from tests.auth.test_auth_api import _login

NEW_PASSWORD = "newpass99"


def _change(client, headers, current=VALID_PASSWORD, new=NEW_PASSWORD):
    return client.post(
        "/api/auth/password/change",
        headers=headers,
        json={"current_password": current, "new_password": new},
    )


def _count_active_refresh_tokens(user_id: str) -> int:
    import psycopg2

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM refresh_tokens
            WHERE user_id = %s AND revoked_at IS NULL
            """,
            (user_id,),
        )
        count = cur.fetchone()[0]
    conn.close()
    return count


@pytest.mark.usefixtures("client", "clean_auth_data")
class TestChangePasswordSuccess:
    def test_login_with_new_password(self, client, auth_user, auth_headers):
        assert _change(client, auth_headers).status_code == 200
        old_login = _login(client, auth_user["user"]["username"], VALID_PASSWORD)
        assert old_login.status_code == 401
        new_login = _login(client, auth_user["user"]["username"], NEW_PASSWORD)
        assert new_login.status_code == 200

    def test_old_refresh_revoked_new_refresh_works(self, client, auth_user, auth_headers):
        old_refresh = auth_user["refresh_token"]
        assert _change(client, auth_headers).status_code == 200
        assert client.post(
            "/api/auth/refresh", json={"refresh_token": old_refresh}
        ).status_code == 401
        new_login = _login(client, auth_user["user"]["username"], NEW_PASSWORD)
        new_refresh = new_login.json()["refresh_token"]
        assert client.post(
            "/api/auth/refresh", json={"refresh_token": new_refresh}
        ).status_code == 200

    def test_revokes_all_device_sessions(self, client, register_user):
        """Два refresh-токена (два «устройства») — оба отзываются."""
        u = register_user("multi_device")
        headers = {"Authorization": f"Bearer {u['access_token']}"}
        r2 = client.post("/api/auth/refresh", json={"refresh_token": u["refresh_token"]})
        assert r2.status_code == 200
        second_refresh = r2.json()["refresh_token"]
        user_id = u["user"]["id"]
        assert _count_active_refresh_tokens(user_id) >= 1

        assert _change(client, headers, new=NEW_PASSWORD).status_code == 200

        assert client.post(
            "/api/auth/refresh", json={"refresh_token": u["refresh_token"]}
        ).status_code == 401
        assert client.post(
            "/api/auth/refresh", json={"refresh_token": second_refresh}
        ).status_code == 401

    def test_access_still_valid_until_expiry(self, client, auth_user, auth_headers):
        """Access не отзывается при смене пароля (как при logout)."""
        access = auth_user["access_token"]
        assert _change(client, auth_headers).status_code == 200
        r = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert r.status_code == 200


@pytest.mark.usefixtures("client", "clean_auth_data")
class TestChangePasswordFailures:
    def test_wrong_current_leaves_password_unchanged(self, client, auth_user, auth_headers):
        r = _change(client, auth_headers, current="wrongpass1")
        assert r.status_code == 401
        assert _login(client, auth_user["user"]["username"], VALID_PASSWORD).status_code == 200

    def test_new_password_without_digit(self, client, auth_headers):
        r = _change(client, auth_headers, new="onlyletters")
        assert r.status_code == 422

    def test_new_password_without_letter(self, client, auth_headers):
        r = _change(client, auth_headers, new="12345678")
        assert r.status_code == 422

    def test_expired_access_token(self, client, auth_user):
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {"sub": auth_user["user"]["id"], "type": "access", "exp": expire}
        token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
        r = _change(client, {"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_malformed_bearer(self, client):
        r = _change(client, {"Authorization": "NotBearer x"})
        assert r.status_code == 401

    def test_unknown_user_in_token(self, client):
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        payload = {"sub": str(uuid.uuid4()), "type": "access", "exp": expire}
        token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
        r = _change(client, {"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


@pytest.mark.usefixtures("client", "clean_auth_data")
class TestChangePasswordIsolation:
    def test_other_user_sessions_unaffected(self, client, register_user):
        u1 = register_user("user_one")
        u2 = register_user("user_two")
        assert _change(
            client,
            {"Authorization": f"Bearer {u1['access_token']}"},
            new=NEW_PASSWORD,
        ).status_code == 200
        assert client.post(
            "/api/auth/refresh", json={"refresh_token": u2["refresh_token"]}
        ).status_code == 200


@pytest.mark.usefixtures("client", "clean_auth_data")
class TestChangePasswordServiceContract:
    def test_response_message(self, client, auth_headers):
        r = _change(client, auth_headers)
        assert "изменён" in r.json()["message"].lower() or "войдите" in r.json()["message"].lower()

    def test_password_hash_updated_in_db(self, client, auth_user, auth_headers):
        import psycopg2

        assert _change(client, auth_headers).status_code == 200
        conn = psycopg2.connect(SYNC_DB_URL)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT password_hash FROM users WHERE id = %s",
                (auth_user["user"]["id"],),
            )
            row = cur.fetchone()
        conn.close()
        assert row is not None
        assert verify_password(NEW_PASSWORD, row[0])
        assert not verify_password(VALID_PASSWORD, row[0])
