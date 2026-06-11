"""Integration tests: data persisted to PostgreSQL tables (users, refresh_tokens, finished_games, presence_sessions)."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from backend.auth.passwords import verify_password
from backend.board_utils import get_starting_board, keys_int_to_str
from backend.db.models import FinishedGame, PresenceSession
from backend.db.session import get_session_factory
from backend.game_archive import archive_finished_game
from backend.presence import end_session, start_session
from tests.db.conftest import (
    VALID_PASSWORD,
    db_fetchall,
    db_fetchone,
    db_scalar,
    login,
    register,
)


def _room(room_id="roomdb01", user_id=None, username="player1", **extra):
    meta_white = {
        "user_id": str(user_id) if user_id else None,
        "username": username if user_id else None,
        "is_anonymous": user_id is None,
    }
    return {
        "room_id": room_id,
        "type": "public",
        "game_started": True,
        "game_started_at": "2026-06-01T10:00:00+00:00",
        "players": {"c-white": "белый", "c-black": "черный"},
        "player_meta": {
            "c-white": meta_white,
            "c-black": {"user_id": None, "username": None, "is_anonymous": True},
        },
        "time_control": 300,
        "increment": 5,
        "timer_white": 100.0,
        "timer_black": 200.0,
        **extra,
    }


def _finished_game(**extra):
    g = {
        "board": get_starting_board(),
        "mover": "черный",
        "game_over": True,
        "winner_color": "белый",
        "reason": "resign",
        "move_history": [
            {
                "from_pos": 53,
                "to_pos": 46,
                "desk": keys_int_to_str(get_starting_board()),
                "mover": "белый",
            },
        ],
    }
    g.update(extra)
    return g


def _ai_room_db(room_id, human_id=None, human_name=None, *, human_anonymous=False, **extra):
    human_meta = {
        "user_id": str(human_id) if human_id else None,
        "username": human_name if human_id else None,
        "is_anonymous": human_anonymous if not human_id else False,
    }
    if human_id:
        human_meta["is_anonymous"] = False
    return {
        "room_id": room_id,
        "type": "ai",
        "game_started": True,
        "game_started_at": "2026-06-01T11:00:00+00:00",
        "players": {"human-1": "белый"},
        "player_meta": {"human-1": human_meta},
        "time_control": 600,
        "increment": 3,
        "timer_white": 450.0,
        "timer_black": 0.0,
        **extra,
    }


def _private_friend_room(
    room_id,
    host_id,
    host_name,
    *,
    guest_id=None,
    guest_name=None,
    guest_anonymous=True,
    **extra,
):
    guest_meta = {
        "user_id": str(guest_id) if guest_id else None,
        "username": guest_name if guest_id else None,
        "is_anonymous": guest_anonymous if not guest_id else False,
    }
    if guest_id:
        guest_meta = {
            "user_id": str(guest_id),
            "username": guest_name,
            "is_anonymous": False,
        }
    return {
        "room_id": room_id,
        "type": "private",
        "game_started": True,
        "game_started_at": "2026-06-01T12:00:00+00:00",
        "players": {"host-1": "белый", "guest-1": "черный"},
        "player_meta": {
            "host-1": {
                "user_id": str(host_id),
                "username": host_name,
                "is_anonymous": False,
            },
            "guest-1": guest_meta,
        },
        "time_control": 900,
        "increment": 10,
        "timer_white": 800.0,
        "timer_black": 750.0,
        **extra,
    }


class ArchiveStub:
    def __init__(self, room_id, game, room):
        self.room_id = room_id
        self.game = dict(game)
        self.room = dict(room)
        from tests.server.conftest import ensure_users_for_room

        ensure_users_for_room(self.room)

    async def get_game(self, rid):
        return self.game if rid == self.room_id else None

    async def get_room(self, rid):
        return self.room if rid == self.room_id else None

    async def set_game(self, rid, data):
        if rid == self.room_id:
            self.game = dict(data)


async def _run_archive(stub: ArchiveStub):
    from tests.server.conftest import ensure_users_for_room

    ensure_users_for_room(stub.room)
    with (
        patch("backend.game_archive.get_game", side_effect=stub.get_game),
        patch("backend.game_archive.get_room", side_effect=stub.get_room),
        patch("backend.game_archive.set_game", side_effect=stub.set_game),
    ):
        return await archive_finished_game(stub.room_id)


async def _get_finished(room_id: str) -> FinishedGame:
    factory = get_session_factory()
    async with factory() as session:
        row = await session.scalar(
            select(FinishedGame).where(FinishedGame.room_id == room_id)
        )
    assert row is not None
    return row


async def _count(model) -> int:
    factory = get_session_factory()
    async with factory() as session:
        return int((await session.scalar(select(func.count()).select_from(model))) or 0)


@pytest.mark.usefixtures("client")
class TestUsersTablePersistence:
    def test_register_persists_user_fields(self, client):
        data = register(
            client,
            "AltaiPlayer",
            first_name="Иван",
            last_name="Петров",
            district="Горно-Алтайск",
        )
        user_id = data["user"]["id"]
        row = db_fetchone(
            """
            SELECT username, username_normalized, first_name, last_name,
                   district, is_admin, password_hash, created_at, updated_at
            FROM users WHERE id = %s
            """,
            (user_id,),
        )
        assert row is not None
        username, norm, first, last, district, is_admin, pwd_hash, created, updated = row
        assert username == "AltaiPlayer"
        assert norm == "altaiplayer"
        assert first == "Иван"
        assert last == "Петров"
        assert district == "Горно-Алтайск"
        assert is_admin is False
        assert verify_password(VALID_PASSWORD, pwd_hash)
        assert created is not None
        assert updated is not None

    def test_profile_patch_updates_users_row(self, client):
        data = register(client, "patchme")
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        r = client.patch(
            "/api/auth/me",
            headers=headers,
            json={
                "first_name": "Новое",
                "last_name": "Имя",
                "district": "Онгудай",
            },
        )
        assert r.status_code == 200
        row = db_fetchone(
            "SELECT first_name, last_name, district FROM users WHERE id = %s",
            (data["user"]["id"],),
        )
        assert row == ("Новое", "Имя", "Онгудай")

    def test_is_admin_persists_in_db(self, client):
        data = register(client, "future_admin")
        user_id = data["user"]["id"]
        import psycopg2
        from tests.db.conftest import SYNC_DB_URL

        conn = psycopg2.connect(SYNC_DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET is_admin = TRUE WHERE id = %s", (user_id,))
        conn.close()
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
        assert me.json()["is_admin"] is True
        assert db_scalar("SELECT is_admin FROM users WHERE id = %s", (user_id,)) is True


@pytest.mark.usefixtures("client")
class TestRefreshTokensTablePersistence:
    def test_register_creates_refresh_token_row(self, client):
        data = register(client, "token_user")
        user_id = data["user"]["id"]
        count = db_scalar(
            "SELECT COUNT(*) FROM refresh_tokens WHERE user_id = %s AND revoked_at IS NULL",
            (user_id,),
        )
        assert count == 1
        row = db_fetchone(
            "SELECT token_hash, expires_at, revoked_at FROM refresh_tokens WHERE user_id = %s",
            (user_id,),
        )
        assert row[0]  # token_hash
        assert row[1] is not None
        assert row[2] is None

    def test_login_adds_new_refresh_token(self, client):
        register(client, "login_twice")
        first = db_scalar("SELECT COUNT(*) FROM refresh_tokens")
        login(client, "login_twice")
        second = db_scalar("SELECT COUNT(*) FROM refresh_tokens")
        assert second == first + 1

    def test_refresh_rotates_token_in_db(self, client):
        data = register(client, "rotate_me")
        old_hash = db_fetchone(
            "SELECT token_hash FROM refresh_tokens WHERE user_id = %s",
            (data["user"]["id"],),
        )[0]
        r = client.post("/api/auth/refresh", json={"refresh_token": data["refresh_token"]})
        assert r.status_code == 200
        rows = db_fetchall(
            "SELECT token_hash, revoked_at FROM refresh_tokens WHERE user_id = %s ORDER BY created_at",
            (data["user"]["id"],),
        )
        assert len(rows) >= 2
        revoked_hashes = [h for h, rev in rows if rev is not None]
        active_hashes = [h for h, rev in rows if rev is None]
        assert old_hash in revoked_hashes
        assert len(active_hashes) >= 1
        assert old_hash not in active_hashes

    def test_logout_revokes_refresh_token(self, client):
        data = register(client, "logout_user")
        client.post("/api/auth/logout", json={"refresh_token": data["refresh_token"]})
        revoked = db_scalar(
            """
            SELECT COUNT(*) FROM refresh_tokens
            WHERE user_id = %s AND revoked_at IS NOT NULL
            """,
            (data["user"]["id"],),
        )
        assert revoked >= 1
        active = db_scalar(
            """
            SELECT COUNT(*) FROM refresh_tokens
            WHERE user_id = %s AND revoked_at IS NULL
            """,
            (data["user"]["id"],),
        )
        assert active == 0

    def test_logout_does_not_revoke_other_users_tokens(self, client):
        u1 = register(client, "user_a")
        u2 = register(client, "user_b")
        client.post("/api/auth/logout", json={"refresh_token": u1["refresh_token"]})
        u2_active = db_scalar(
            "SELECT COUNT(*) FROM refresh_tokens WHERE user_id = %s AND revoked_at IS NULL",
            (u2["user"]["id"],),
        )
        assert u2_active == 1


@pytest.mark.asyncio
class TestFinishedGamesTablePersistence:
    async def test_archive_writes_all_columns(self, client):
        user = register(client, "gamer1")
        user_id = uuid.UUID(user["user"]["id"])
        stub = ArchiveStub(
            "fg000001",
            _finished_game(),
            _room("fg000001", user_id=user_id, username="gamer1"),
        )
        with (
            patch("backend.game_archive.get_game", side_effect=stub.get_game),
            patch("backend.game_archive.get_room", side_effect=stub.get_room),
            patch("backend.game_archive.set_game", side_effect=stub.set_game),
        ):
            record_id = await archive_finished_game("fg000001")
        assert record_id is not None
        factory = get_session_factory()
        async with factory() as session:
            row = await session.get(FinishedGame, record_id)
        assert row.room_id == "fg000001"
        assert row.room_type == "public"
        assert row.white_user_id == user_id
        assert row.black_is_anonymous is True
        assert row.winner_color == "белый"
        assert row.reason == "resign"
        assert row.moves_count == 1
        assert row.move_history[0]["from_pos"] == 53
        assert row.final_board is not None
        assert row.started_at.year == 2026

    async def test_private_and_ai_rows_distinct(self, client):
        user_id = uuid.UUID(register(client, "multi_type")["user"]["id"])

        for room_id, room_type, reason in [
            ("priv0001", "private", "timeout"),
            ("ai000001", "ai", "ai.no_move"),
        ]:
            players = {"h1": "белый"} if room_type == "ai" else {"c-w": "белый", "c-b": "черный"}
            meta = {
                "h1" if room_type == "ai" else "c-w": {
                    "user_id": str(user_id),
                    "username": "multi_type",
                    "is_anonymous": False,
                },
            }
            if room_type != "ai":
                meta["c-b"] = {"user_id": None, "username": None, "is_anonymous": True}
            stub = ArchiveStub(
                room_id,
                _finished_game(reason=reason),
                _room(room_id, user_id=user_id, type=room_type, players=players, player_meta=meta),
            )
            with (
                patch("backend.game_archive.get_game", side_effect=stub.get_game),
                patch("backend.game_archive.get_room", side_effect=stub.get_room),
                patch("backend.game_archive.set_game", side_effect=stub.set_game),
            ):
                await archive_finished_game(room_id)

        types = db_fetchall(
            "SELECT room_type, reason FROM finished_games ORDER BY room_id"
        )
        assert ("ai", "ai.no_move") in types
        assert ("private", "timeout") in types

    async def test_two_finished_games_same_room_id(self):
        stub = ArchiveStub("same0001", _finished_game(), _room("same0001"))
        with (
            patch("backend.game_archive.get_game", side_effect=stub.get_game),
            patch("backend.game_archive.get_room", side_effect=stub.get_room),
            patch("backend.game_archive.set_game", side_effect=stub.set_game),
        ):
            await archive_finished_game("same0001")
            stub.game["archived"] = False
            stub.game["reason"] = "draw_agreed"
            stub.game["winner_color"] = ""
            stub.room["game_started_at"] = "2026-06-01T11:00:00+00:00"
            await archive_finished_game("same0001")
        assert db_scalar("SELECT COUNT(*) FROM finished_games WHERE room_id = %s", ("same0001",)) == 2

    async def test_cancelled_game_not_in_db(self):
        stub = ArchiveStub(
            "canc0001",
            _finished_game(reason="cancelled"),
            _room("canc0001"),
        )
        with (
            patch("backend.game_archive.get_game", side_effect=stub.get_game),
            patch("backend.game_archive.get_room", side_effect=stub.get_room),
            patch("backend.game_archive.set_game", side_effect=stub.set_game),
        ):
            assert await archive_finished_game("canc0001") is None
        assert await _count(FinishedGame) == 0


@pytest.mark.asyncio
class TestFinishedGameAiPersistence:
    async def test_ai_registered_human_full_row_in_db(self, client):
        user = register(client, "ai_player")
        user_id = uuid.UUID(user["user"]["id"])
        stub = ArchiveStub(
            "ai000101",
            _finished_game(reason="ai.no_move", winner_color="белый"),
            _ai_room_db("ai000101", user_id, "ai_player"),
        )
        record_id = await _run_archive(stub)
        assert record_id is not None
        row = await _get_finished("ai000101")
        assert row.room_type == "ai"
        assert row.reason == "ai.no_move"
        assert row.winner_color == "белый"
        assert row.white_user_id == user_id
        assert row.white_is_anonymous is False
        assert row.black_user_id is None
        assert row.black_client_id is None
        assert row.black_is_anonymous is False
        assert row.time_control == 600
        assert row.increment == 3
        assert row.moves_count == 1

    async def test_ai_anonymous_human_persisted(self, client):
        stub = ArchiveStub(
            "ai000102",
            _finished_game(reason="resign", winner_color="черный"),
            _ai_room_db("ai000102", human_anonymous=True),
        )
        await _run_archive(stub)
        row = await _get_finished("ai000102")
        assert row.room_type == "ai"
        assert row.white_user_id is None
        assert row.white_is_anonymous is True
        assert row.white_client_id == "human-1"
        assert row.reason == "resign"
        assert row.winner_color == "черный"

    async def test_ai_only_one_side_in_players_meta(self, client):
        user_id = uuid.UUID(register(client, "solo_ai")["user"]["id"])
        stub = ArchiveStub(
            "ai000103",
            _finished_game(reason="timeout", winner_color="белый"),
            _ai_room_db("ai000103", user_id, "solo_ai"),
        )
        await _run_archive(stub)
        row = await _get_finished("ai000103")
        assert len(stub.room["players"]) == 1
        assert row.black_client_id is None
        assert db_scalar("SELECT COUNT(*) FROM finished_games WHERE room_type = 'ai'") == 1


@pytest.mark.asyncio
class TestFinishedGamePrivateFriendPersistence:
    async def test_private_both_friends_registered_in_db(self, client):
        host = register(client, "host_friend")
        guest = register(client, "guest_friend")
        host_id = uuid.UUID(host["user"]["id"])
        guest_id = uuid.UUID(guest["user"]["id"])
        stub = ArchiveStub(
            "priv0001",
            _finished_game(reason="resign", winner_color="белый"),
            _private_friend_room(
                "priv0001", host_id, "host_friend", guest_id=guest_id, guest_name="guest_friend"
            ),
        )
        await _run_archive(stub)
        row = await _get_finished("priv0001")
        assert row.room_type == "private"
        assert row.white_user_id == host_id
        assert row.black_user_id == guest_id
        assert row.white_is_anonymous is False
        assert row.black_is_anonymous is False
        assert row.reason == "resign"
        assert row.timer_white_final == 800.0
        assert row.timer_black_final == 750.0

    async def test_private_host_registered_guest_anonymous(self, client):
        host_id = uuid.UUID(register(client, "room_host")["user"]["id"])
        stub = ArchiveStub(
            "priv0002",
            _finished_game(reason="timeout", winner_color="черный"),
            _private_friend_room("priv0002", host_id, "room_host", guest_anonymous=True),
        )
        await _run_archive(stub)
        row = await _get_finished("priv0002")
        assert row.room_type == "private"
        assert row.white_user_id == host_id
        assert row.black_user_id is None
        assert row.black_is_anonymous is True
        assert row.black_client_id == "guest-1"
        assert row.reason == "timeout"

    async def test_private_both_anonymous_friends(self, client):
        stub = ArchiveStub(
            "priv0003",
            _finished_game(reason="draw_agreed", winner_color=""),
            _private_friend_room(
                "priv0003",
                host_id=uuid.uuid4(),
                host_name="ignored",
                guest_anonymous=True,
            ),
        )
        stub.room["player_meta"]["host-1"] = {
            "user_id": None,
            "username": None,
            "is_anonymous": True,
        }
        stub.room["players"] = {"host-1": "белый", "guest-1": "черный"}
        await _run_archive(stub)
        row = await _get_finished("priv0003")
        assert row.room_type == "private"
        assert row.white_is_anonymous is True
        assert row.black_is_anonymous is True
        assert row.white_user_id is None
        assert row.black_user_id is None
        assert row.winner_color is None
        assert row.reason == "draw_agreed"

    async def test_private_distinct_from_public_and_ai(self, client):
        user_id = uuid.UUID(register(client, "triple_type")["user"]["id"])
        scenarios = [
            ("pub00001", "public", _room("pub00001", user_id, "triple_type")),
            (
                "priv0004",
                "private",
                _private_friend_room("priv0004", user_id, "triple_type", guest_anonymous=True),
            ),
            ("ai000104", "ai", _ai_room_db("ai000104", user_id, "triple_type")),
        ]
        for room_id, expected_type, room_data in scenarios:
            stub = ArchiveStub(room_id, _finished_game(), room_data)
            await _run_archive(stub)
        types = db_fetchall("SELECT room_id, room_type FROM finished_games ORDER BY room_id")
        assert types == [
            ("ai000104", "ai"),
            ("priv0004", "private"),
            ("pub00001", "public"),
        ]


@pytest.mark.asyncio
class TestPresenceSessionsTablePersistence:
    async def test_start_session_inserts_row(self, client):
        data = register(client, "presence_user")
        user_id = uuid.UUID(data["user"]["id"])
        await start_session(
            client_id="pres-001",
            user_id=user_id,
            is_anonymous=False,
            room_id="room0001",
        )
        factory = get_session_factory()
        async with factory() as session:
            rows = list((await session.scalars(select(PresenceSession))).all())
        assert len(rows) == 1
        assert rows[0].client_id == "pres-001"
        assert rows[0].user_id == user_id
        assert rows[0].is_anonymous is False
        assert rows[0].room_id == "room0001"
        assert rows[0].connected_at is not None
        assert rows[0].disconnected_at is None

    async def test_end_session_sets_disconnected_at(self):
        await start_session(
            client_id="pres-002",
            user_id=None,
            is_anonymous=True,
            room_id="room0002",
        )
        await end_session("pres-002")
        row = db_fetchone(
            "SELECT disconnected_at FROM presence_sessions WHERE client_id = %s",
            ("pres-002",),
        )
        assert row[0] is not None

    async def test_reconnect_creates_second_row(self):
        await start_session(client_id="pres-rc", user_id=None, is_anonymous=True, room_id="r1")
        await end_session("pres-rc")
        await start_session(client_id="pres-rc", user_id=None, is_anonymous=True, room_id="r1")
        assert db_scalar(
            "SELECT COUNT(*) FROM presence_sessions WHERE client_id = %s", ("pres-rc",)
        ) == 2
        open_sessions = db_scalar(
            """
            SELECT COUNT(*) FROM presence_sessions
            WHERE client_id = %s AND disconnected_at IS NULL
            """,
            ("pres-rc",),
        )
        assert open_sessions == 1

    async def test_multiple_client_ids_for_same_user(self, client):
        data = register(client, "presence_multi")
        user_id = uuid.UUID(data["user"]["id"])
        await start_session(client_id="tab-a", user_id=user_id, is_anonymous=False, room_id="r1")
        await start_session(client_id="tab-b", user_id=user_id, is_anonymous=False, room_id="r2")
        assert db_scalar(
            "SELECT COUNT(*) FROM presence_sessions WHERE user_id = %s", (str(user_id),)
        ) == 2


class TestCrossTablePersistence:
    @pytest.mark.asyncio
    async def test_registered_user_game_links_user_id(self, client):
        data = register(client, "linked_gamer")
        user_id = uuid.UUID(data["user"]["id"])
        stub = ArchiveStub(
            "link0001",
            _finished_game(),
            _room("link0001", user_id=user_id, username="linked_gamer"),
        )
        with (
            patch("backend.game_archive.get_game", side_effect=stub.get_game),
            patch("backend.game_archive.get_room", side_effect=stub.get_room),
            patch("backend.game_archive.set_game", side_effect=stub.set_game),
        ):
            await archive_finished_game("link0001")

        assert db_scalar("SELECT COUNT(*) FROM users") == 1
        assert db_scalar("SELECT COUNT(*) FROM refresh_tokens WHERE user_id = %s", (str(user_id),)) == 1
        white_uid = db_fetchone(
            "SELECT white_user_id FROM finished_games WHERE room_id = %s", ("link0001",)
        )[0]
        assert str(white_uid) == str(user_id)

    @pytest.mark.asyncio
    async def test_user_presence_and_game_coexist(self, client):
        data = register(client, "online_gamer")
        user_id = uuid.UUID(data["user"]["id"])
        await start_session(
            client_id="online-c1",
            user_id=user_id,
            is_anonymous=False,
            room_id="onl00001",
        )
        stub = ArchiveStub(
            "onl00001",
            _finished_game(reason="opponent_disconnected"),
            _room("onl00001", user_id=user_id, username="online_gamer"),
        )
        with (
            patch("backend.game_archive.get_game", side_effect=stub.get_game),
            patch("backend.game_archive.get_room", side_effect=stub.get_room),
            patch("backend.game_archive.set_game", side_effect=stub.set_game),
        ):
            await archive_finished_game("onl00001")

        assert db_scalar("SELECT COUNT(*) FROM users") >= 1
        assert db_scalar("SELECT COUNT(*) FROM presence_sessions WHERE user_id = %s", (str(user_id),)) == 1
        assert db_scalar("SELECT COUNT(*) FROM finished_games WHERE room_id = %s", ("onl00001",)) == 1

    def test_logout_keeps_user_and_finished_games(self, client):
        import psycopg2
        from tests.db.conftest import SYNC_DB_URL

        data = register(client, "persist_user")
        user_id = data["user"]["id"]
        conn = psycopg2.connect(SYNC_DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO finished_games (
                    id, room_id, room_type, moves_count, move_history, finished_at,
                    white_user_id
                ) VALUES (%s, %s, 'public', 0, '[]', NOW(), %s)
                """,
                (str(uuid.uuid4()), "oldgame1", user_id),
            )
        conn.close()

        client.post("/api/auth/logout", json={"refresh_token": data["refresh_token"]})
        assert db_scalar("SELECT COUNT(*) FROM users WHERE id = %s", (user_id,)) == 1
        assert db_scalar(
            "SELECT COUNT(*) FROM finished_games WHERE white_user_id = %s", (user_id,)
        ) == 1
        assert db_scalar(
            "SELECT COUNT(*) FROM refresh_tokens WHERE user_id = %s AND revoked_at IS NULL",
            (user_id,),
        ) == 0

    @pytest.mark.asyncio
    async def test_tables_are_independent_counts(self, client):
        register(client, "counter")
        await start_session(client_id="cnt-1", user_id=None, is_anonymous=True, room_id="cntroom")
        stub = ArchiveStub("cntroom", _finished_game(), _room("cntroom"))
        with (
            patch("backend.game_archive.get_game", side_effect=stub.get_game),
            patch("backend.game_archive.get_room", side_effect=stub.get_room),
            patch("backend.game_archive.set_game", side_effect=stub.set_game),
        ):
            await archive_finished_game("cntroom")

        assert db_scalar("SELECT COUNT(*) FROM users") == 1
        assert db_scalar("SELECT COUNT(*) FROM refresh_tokens") == 1
        assert db_scalar("SELECT COUNT(*) FROM finished_games") == 1
        assert db_scalar("SELECT COUNT(*) FROM presence_sessions") == 1

    @pytest.mark.asyncio
    async def test_anonymous_game_and_presence_no_user_fk(self):
        await start_session(client_id="anon-pres", user_id=None, is_anonymous=True, room_id="anon01")
        stub = ArchiveStub(
            "anon01",
            _finished_game(),
            _room("anon01", user_id=None, username=None),
        )
        stub.room["player_meta"] = {
            "c-white": {"user_id": None, "username": None, "is_anonymous": True},
            "c-black": {"user_id": None, "username": None, "is_anonymous": True},
        }
        with (
            patch("backend.game_archive.get_game", side_effect=stub.get_game),
            patch("backend.game_archive.get_room", side_effect=stub.get_room),
            patch("backend.game_archive.set_game", side_effect=stub.set_game),
        ):
            await archive_finished_game("anon01")

        game = db_fetchone(
            "SELECT white_user_id, black_user_id, white_is_anonymous, black_is_anonymous "
            "FROM finished_games WHERE room_id = %s",
            ("anon01",),
        )
        assert game == (None, None, True, True)
        pres = db_fetchone(
            "SELECT user_id, is_anonymous FROM presence_sessions WHERE client_id = %s",
            ("anon-pres",),
        )
        assert pres == (None, True)
