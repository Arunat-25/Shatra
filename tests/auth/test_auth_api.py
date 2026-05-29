"""Интеграционные тесты API аутентификации."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt

import pytest

from backend.auth.constants import DISTRICTS
from backend.auth.jwt_utils import ALGORITHM
from backend.config import settings
from tests.auth.conftest import VALID_PASSWORD


def _register(client, username, password=VALID_PASSWORD, **extra):
    return client.post(
        "/api/auth/register",
        json={"username": username, "password": password, **extra},
    )


def _login(client, username, password=VALID_PASSWORD):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def _expired_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) - timedelta(hours=1)
    payload = {"sub": str(user_id), "type": "access", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


# --- Регистрация ---


class TestRegister:
    def test_success_with_profile_fields(self, client):
        r = _register(
            client,
            "АлтайскийИгрок",
            first_name="Иван",
            last_name="Иванов",
            district="Горно-Алтайск",
        )
        assert r.status_code == 200
        data = r.json()
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "АлтайскийИгрок"
        assert data["user"]["first_name"] == "Иван"
        assert data["user"]["district"] == "Горно-Алтайск"
        assert data["access_token"]
        assert data["refresh_token"]

    def test_minimal_register(self, client):
        r = _register(client, "minimal_user")
        assert r.status_code == 200
        assert r.json()["user"]["first_name"] is None

    def test_username_with_spaces_rejected(self, client):
        r = _register(client, "  spaced_name  ")
        assert r.status_code == 422

    def test_login_trims_username(self, client):
        _register(client, "spaced_name")
        r = _login(client, "  spaced_name  ")
        assert r.status_code == 200

    def test_duplicate_username_exact(self, client):
        _register(client, "dup_user")
        r = _register(client, "dup_user", password="otherpass1")
        assert r.status_code == 409
        assert r.json()["detail"] == "auth.username_taken_register"

    def test_duplicate_username_case_insensitive(self, client):
        _register(client, "CaseUser")
        r = _register(client, "caseuser", password="otherpass1")
        assert r.status_code == 409

    def test_login_works_with_different_case(self, client):
        _register(client, "MixedCase")
        r = _login(client, "mixedcase")
        assert r.status_code == 200

    @pytest.mark.parametrize(
        "payload",
        [
            {"username": "ab", "password": VALID_PASSWORD},
            {"username": "valid_user", "password": "short"},
            {"username": "valid_user", "password": "onlyletters"},
            {"username": "valid_user", "password": VALID_PASSWORD, "district": "Москва"},
            {"username": "bad name", "password": VALID_PASSWORD},
        ],
    )
    def test_validation_errors_return_422(self, client, payload):
        r = client.post("/api/auth/register", json=payload)
        assert r.status_code == 422


# --- Вход ---


class TestLogin:
    def test_success_after_register(self, client):
        _register(client, "login_ok")
        r = _login(client, "login_ok")
        assert r.status_code == 200
        assert r.json()["user"]["username"] == "login_ok"

    def test_wrong_password(self, client):
        _register(client, "login_test")
        r = _login(client, "login_test", password="wrongpass1")
        assert r.status_code == 401
        assert r.json()["detail"] == "auth.invalid_credentials"

    def test_unknown_user(self, client):
        r = _login(client, "nobody_here")
        assert r.status_code == 401

    def test_empty_body_422(self, client):
        r = client.post("/api/auth/login", json={})
        assert r.status_code == 422


# --- /me и авторизация ---


class TestMe:
    def test_me_with_valid_token(self, auth_user, auth_headers, client):
        r = client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["username"] == auth_user["user"]["username"]
        assert r.json()["id"] == auth_user["user"]["id"]

    def test_me_without_token(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_me_with_invalid_token(self, client):
        r = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer not-a-valid-jwt"},
        )
        assert r.status_code == 401

    def test_me_with_malformed_authorization(self, client):
        r = client.get(
            "/api/auth/me",
            headers={"Authorization": "Token abc"},
        )
        assert r.status_code == 401

    def test_me_with_expired_token(self, client, auth_user):
        user_id = uuid.UUID(auth_user["user"]["id"])
        token = _expired_access_token(user_id)
        r = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 401

    def test_me_for_deleted_user(self, client, auth_user, auth_headers):
        import psycopg2

        from tests.auth.conftest import SYNC_DB_URL

        conn = psycopg2.connect(SYNC_DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (auth_user["user"]["id"],))
        conn.close()

        r = client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 401


# --- Профиль ---


class TestProfileUpdate:
    def test_update_all_fields(self, client, auth_headers):
        r = client.patch(
            "/api/auth/me",
            headers=auth_headers,
            json={
                "first_name": "Пётр",
                "last_name": "Петров",
                "district": "Чоя",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["first_name"] == "Пётр"
        assert body["last_name"] == "Петров"
        assert body["district"] == "Чоя"

    def test_partial_update_leaves_other_fields(self, client, register_user):
        data = register_user(
            "profile_partial",
            first_name="Было",
            district="Майма",
        )
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        r = client.patch(
            "/api/auth/me",
            headers=headers,
            json={"last_name": "Стало"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["first_name"] == "Было"
        assert body["last_name"] == "Стало"
        assert body["district"] == "Майма"

    def test_clear_name_with_empty_string(self, client, auth_headers):
        client.patch(
            "/api/auth/me",
            headers=auth_headers,
            json={"first_name": "Временно"},
        )
        r = client.patch(
            "/api/auth/me",
            headers=auth_headers,
            json={"first_name": ""},
        )
        assert r.status_code == 200
        assert r.json()["first_name"] is None

    def test_null_district_in_patch_does_not_clear_existing(self, client, register_user):
        """PATCH с district=null не меняет поле (только явная новая строка)."""
        data = register_user("clear_dist", district="Чемал")
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        r = client.patch(
            "/api/auth/me",
            headers=headers,
            json={"district": None},
        )
        assert r.status_code == 200
        assert r.json()["district"] == "Чемал"

    def test_invalid_district_422(self, client, auth_headers):
        r = client.patch(
            "/api/auth/me",
            headers=auth_headers,
            json={"district": "Санкт-Петербург"},
        )
        assert r.status_code == 422

    def test_unauthorized_401(self, client):
        r = client.patch("/api/auth/me", json={"first_name": "Хакер"})
        assert r.status_code == 401

    def test_change_username(self, client, register_user):
        data = register_user("old_name")
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        r = client.patch(
            "/api/auth/me",
            headers=headers,
            json={"username": "НовоеИмя"},
        )
        assert r.status_code == 200
        assert r.json()["username"] == "НовоеИмя"

        r_me = client.get("/api/auth/me", headers=headers)
        assert r_me.json()["username"] == "НовоеИмя"

    def test_login_with_new_username_after_change(self, client, register_user):
        data = register_user("rename_login")
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        client.patch(
            "/api/auth/me",
            headers=headers,
            json={"username": "renamed_user"},
        )
        r = _login(client, "renamed_user")
        assert r.status_code == 200

        r_old = _login(client, "rename_login")
        assert r_old.status_code == 401

    def test_change_username_case_only(self, client, register_user):
        data = register_user("caseuser")
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        r = client.patch(
            "/api/auth/me",
            headers=headers,
            json={"username": "CaseUser"},
        )
        assert r.status_code == 200
        assert r.json()["username"] == "CaseUser"

        r = _login(client, "caseuser")
        assert r.status_code == 200

    def test_duplicate_username_on_profile_409(self, client, register_user):
        register_user("taken_name")
        data = register_user("changer")
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        r = client.patch(
            "/api/auth/me",
            headers=headers,
            json={"username": "taken_name"},
        )
        assert r.status_code == 409
        assert r.json()["detail"] == "auth.username_taken_profile"

    def test_invalid_username_on_profile_422(self, client, auth_headers):
        r = client.patch(
            "/api/auth/me",
            headers=auth_headers,
            json={"username": "x"},
        )
        assert r.status_code == 422

    def test_keep_same_username_normalized(self, client, register_user):
        data = register_user("same_user")
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        r = client.patch(
            "/api/auth/me",
            headers=headers,
            json={"username": "Same_User", "first_name": "Иван"},
        )
        assert r.status_code == 200
        assert r.json()["username"] == "Same_User"
        assert r.json()["first_name"] == "Иван"


# --- Refresh и logout ---


class TestRefreshAndLogout:
    def test_refresh_returns_new_tokens(self, client, auth_user):
        old_refresh = auth_user["refresh_token"]
        r = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
        assert r.status_code == 200
        data = r.json()
        assert data["refresh_token"] != old_refresh
        assert data["access_token"]
        assert data["user"]["username"] == auth_user["user"]["username"]

    def test_old_refresh_token_cannot_be_reused(self, client, auth_user):
        old_refresh = auth_user["refresh_token"]
        r1 = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
        assert r1.status_code == 200
        r2 = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
        assert r2.status_code == 401

    def test_refresh_with_garbage_token(self, client):
        r = client.post("/api/auth/refresh", json={"refresh_token": "invalid"})
        assert r.status_code == 401

    def test_logout_revokes_refresh(self, client, auth_user):
        refresh = auth_user["refresh_token"]
        r = client.post("/api/auth/logout", json={"refresh_token": refresh})
        assert r.status_code == 200

        r2 = client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert r2.status_code == 401

    def test_logout_unknown_token_still_ok(self, client):
        r = client.post("/api/auth/logout", json={"refresh_token": "unknown-token"})
        assert r.status_code == 200

    def test_access_token_works_after_logout(self, client, auth_user, auth_headers):
        client.post(
            "/api/auth/logout",
            json={"refresh_token": auth_user["refresh_token"]},
        )
        r = client.get("/api/auth/me", headers=auth_headers)
        # access не отзывается при logout — только refresh
        assert r.status_code == 200


# Смена пароля: см. tests/auth/test_change_password.py


# --- Справочники и сквозные сценарии ---


class TestDistricts:
    def test_list_matches_constants(self, client):
        r = client.get("/api/auth/districts")
        assert r.status_code == 200
        assert r.json()["districts"] == list(DISTRICTS)

    def test_districts_public_without_auth(self, client):
        r = client.get("/api/auth/districts")
        assert r.status_code == 200


class TestEndToEndFlows:
    def test_register_login_me_profile_logout(self, client):
        reg = _register(
            client,
            "e2e_user",
            first_name="А",
            district="Кош-Агач",
        )
        assert reg.status_code == 200
        tokens = reg.json()

        login = _login(client, "e2e_user")
        assert login.status_code == 200

        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        me = client.get("/api/auth/me", headers=headers)
        assert me.json()["district"] == "Кош-Агач"

        patch = client.patch(
            "/api/auth/me",
            headers=headers,
            json={"district": "Другое"},
        )
        assert patch.json()["district"] == "Другое"

        client.post(
            "/api/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
        )

    def test_two_users_isolated(self, client):
        u1 = _register(client, "user_alpha").json()
        u2 = _register(client, "user_beta").json()
        assert u1["user"]["id"] != u2["user"]["id"]

        r = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {u1['access_token']}"},
        )
        assert r.json()["username"] == "user_alpha"
