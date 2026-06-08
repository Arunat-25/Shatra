"""Tests for GET /api/auth/me/games."""

import uuid

import pytest

from tests.helpers.finished_games import insert_finished_game

pytestmark = pytest.mark.auth


class TestUserGamesApi:
    def test_requires_auth(self, client):
        r = client.get("/api/auth/me/games")
        assert r.status_code == 401

    def test_empty_list(self, client, register_user, auth_headers):
        r = client.get("/api/auth/me/games", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_lists_own_games(self, client, register_user):
        user = register_user("player1")
        user_id = uuid.UUID(user["user"]["id"])
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        insert_finished_game(
            room_id="game0001",
            white_user_id=user_id,
            black_is_anonymous=True,
            winner_color="белый",
            reason="resign",
        )
        r = client.get("/api/auth/me/games", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["room_id"] == "game0001"
        assert item["my_color"] == "белый"
        assert item["result"] == "win"
        assert item["opponent_display"] == "__anonymous__"

    def test_isolation_other_user(self, client, register_user):
        owner = register_user("owner")
        other = register_user("other")
        owner_id = uuid.UUID(owner["user"]["id"])
        insert_finished_game(room_id="iso0001", white_user_id=owner_id)
        r = client.get("/api/auth/me/games", headers={"Authorization": f"Bearer {other['access_token']}"})
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_pagination(self, client, register_user):
        user = register_user("paguser")
        user_id = uuid.UUID(user["user"]["id"])
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        for i in range(3):
            insert_finished_game(room_id=f"pag{i:04d}", white_user_id=user_id)
        r = client.get("/api/auth/me/games?limit=2&offset=0", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        r2 = client.get("/api/auth/me/games?limit=2&offset=2", headers=headers)
        assert len(r2.json()["items"]) == 1

    def test_ai_opponent_display(self, client, register_user):
        user = register_user("aiplayer")
        user_id = uuid.UUID(user["user"]["id"])
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        insert_finished_game(
            room_id="ai000001",
            room_type="ai",
            white_user_id=user_id,
            black_user_id=None,
            black_is_anonymous=True,
            winner_color="белый",
        )
        item = client.get("/api/auth/me/games", headers=headers).json()["items"][0]
        assert item["opponent_display"] == "__ai__"
        assert item["room_type"] == "ai"

    def test_draw_result(self, client, register_user):
        user = register_user("drawer")
        user_id = uuid.UUID(user["user"]["id"])
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        insert_finished_game(
            room_id="drw00001",
            white_user_id=user_id,
            winner_color=None,
            reason="draw_agreed",
        )
        item = client.get("/api/auth/me/games", headers=headers).json()["items"][0]
        assert item["result"] == "draw"

    def test_rating_delta_in_rated_game(self, client, register_user):
        white = register_user("rated_white")
        black = register_user("rated_black")
        white_id = uuid.UUID(white["user"]["id"])
        black_id = uuid.UUID(black["user"]["id"])
        headers = {"Authorization": f"Bearer {white['access_token']}"}
        insert_finished_game(
            room_id="rtd00001",
            white_user_id=white_id,
            black_user_id=black_id,
            black_is_anonymous=False,
            winner_color="белый",
            reason="resign",
            is_rated=True,
            white_rating_delta=10,
            black_rating_delta=-10,
        )
        item = client.get("/api/auth/me/games", headers=headers).json()["items"][0]
        assert item["is_rated"] is True
        assert item["rating_delta"] == 10

    def test_rating_delta_for_black_player(self, client, register_user):
        white = register_user("black_delta_white")
        black = register_user("black_delta_black")
        white_id = uuid.UUID(white["user"]["id"])
        black_id = uuid.UUID(black["user"]["id"])
        headers = {"Authorization": f"Bearer {black['access_token']}"}
        insert_finished_game(
            room_id="rtd00002",
            white_user_id=white_id,
            black_user_id=black_id,
            black_is_anonymous=False,
            winner_color="белый",
            reason="resign",
            is_rated=True,
            white_rating_delta=10,
            black_rating_delta=-10,
        )
        item = client.get("/api/auth/me/games", headers=headers).json()["items"][0]
        assert item["my_color"] == "черный"
        assert item["rating_delta"] == -10

    def test_unrated_game_rating_delta_null(self, client, register_user):
        user = register_user("unrated_hist")
        user_id = uuid.UUID(user["user"]["id"])
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        insert_finished_game(
            room_id="unr00001",
            white_user_id=user_id,
            black_is_anonymous=True,
            winner_color="белый",
            is_rated=False,
        )
        item = client.get("/api/auth/me/games", headers=headers).json()["items"][0]
        assert item["is_rated"] is False
        assert item["rating_delta"] is None

    def test_me_includes_rating(self, client, register_user, auth_headers):
        r = client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["rating"] == 1200
        assert data["rated_games_count"] == 0
