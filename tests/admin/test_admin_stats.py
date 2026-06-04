"""Tests for admin statistics API."""

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from unittest.mock import patch

import pytest

from backend.admin.service import (
    anonymous_player_count,
    count_games,
    infer_granularity,
    iter_buckets,
    parse_time_range,
)
from backend.db.session import get_session_factory
from backend.message_codes import ADMIN_FORBIDDEN, AUTH_REQUIRED
from backend.presence import (
    count_online_at,
    count_online_unique_in_period,
    end_session,
    start_session,
)
from tests.admin.conftest import insert_finished_game, insert_user_created_at
from tests.admin.series_assertions import assert_series_buckets_match
from tests.test_env import SYNC_DB_URL

import psycopg2


class TestAdminAuth:
    def test_registrations_requires_auth(self, client):
        r = client.get("/api/admin/stats/registrations")
        assert r.status_code == 401
        assert r.json()["detail"] == AUTH_REQUIRED

    def test_registrations_forbidden_for_regular_user(self, client, regular_headers):
        r = client.get("/api/admin/stats/registrations", headers=regular_headers)
        assert r.status_code == 403
        assert r.json()["detail"] == ADMIN_FORBIDDEN

    def test_registrations_ok_for_db_admin(self, client, admin_headers):
        r = client.get("/api/admin/stats/registrations", headers=admin_headers)
        assert r.status_code == 200
        assert "total" in r.json()

    def test_registrations_ok_for_env_admin(self, client, regular_user):
        user_id = regular_user["user"]["id"]
        with patch("backend.config.settings.admin_user_ids", user_id):
            headers = {"Authorization": f"Bearer {regular_user['access_token']}"}
            r = client.get("/api/admin/stats/registrations", headers=headers)
            assert r.status_code == 200

    def test_me_includes_is_admin(self, client, admin_headers):
        r = client.get("/api/auth/me", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["is_admin"] is True

    def test_me_is_admin_false_for_regular(self, client, regular_headers):
        r = client.get("/api/auth/me", headers=regular_headers)
        assert r.status_code == 200
        assert r.json()["is_admin"] is False


class TestRegistrationStats:
    def test_count_returns_integer(self, client, admin_headers):
        r = client.get("/api/admin/stats/registrations?period=7d", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json()["total"], int)

    def test_count_includes_recent_registration(self, client, admin_headers, register_user):
        register_user("newbie1")
        r = client.get("/api/admin/stats/registrations?period=7d", headers=admin_headers)
        assert r.json()["total"] >= 1

    def test_count_respects_custom_range(self, client, admin_headers):
        old = datetime.now(timezone.utc) - timedelta(days=40)
        insert_user_created_at(old)
        recent = datetime.now(timezone.utc) - timedelta(days=2)
        insert_user_created_at(recent)

        start = quote((recent - timedelta(hours=1)).isoformat(), safe="")
        end = quote((recent + timedelta(hours=1)).isoformat(), safe="")
        r = client.get(
            f"/api/admin/stats/registrations?from={start}&to={end}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_custom_range_requires_both_bounds(self, client, admin_headers):
        r = client.get(
            "/api/admin/stats/registrations?from=2026-01-01T00:00:00%2B00:00",
            headers=admin_headers,
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_count_registrations_empty_db(self):
        from backend.admin.service import count_registrations
        from backend.db.session import get_session_factory

        factory = get_session_factory()
        async with factory() as db:
            data = await count_registrations(
                db,
                from_dt=datetime(2099, 1, 1, tzinfo=timezone.utc),
                to_dt=datetime(2099, 1, 2, tzinfo=timezone.utc),
            )
        assert data["total"] == 0


@pytest.mark.asyncio
class TestOnlineStats:
    async def test_empty_at_returns_zero(self, client, admin_headers):
        at = quote(datetime.now(timezone.utc).isoformat(), safe="")
        r = client.get(f"/api/admin/stats/online?at={at}", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["total_unique"] == 0
        assert body["anonymous_unique"] == 0
        assert body["registered_unique"] == 0

    async def test_registered_user_online_at_point(self, register_user):
        data = register_user("online_user")
        user_id = uuid.UUID(data["user"]["id"])
        now = datetime.now(timezone.utc)
        await start_session(
            client_id="client-reg",
            user_id=user_id,
            is_anonymous=False,
            room_id="room1234",
        )
        data = await count_online_at(now + timedelta(seconds=1))
        assert data["total_unique"] == 1
        assert data["registered_unique"] == 1
        assert data["anonymous_unique"] == 0

    async def test_anonymous_online_at_point(self):
        now = datetime.now(timezone.utc)
        await start_session(
            client_id="anon-client",
            user_id=None,
            is_anonymous=True,
            room_id="room1234",
        )
        data = await count_online_at(now + timedelta(seconds=1))
        assert data["total_unique"] == 1
        assert data["anonymous_unique"] == 1
        assert data["registered_unique"] == 0

    async def test_same_user_two_sessions_counts_once(self, register_user):
        data = register_user("dual_tab_user")
        user_id = uuid.UUID(data["user"]["id"])
        now = datetime.now(timezone.utc)
        await start_session(client_id="tab-a", user_id=user_id, is_anonymous=False, room_id="r1")
        await start_session(client_id="tab-b", user_id=user_id, is_anonymous=False, room_id="r2")
        data = await count_online_at(now + timedelta(seconds=1))
        assert data["total_unique"] == 1
        assert data["registered_unique"] == 1

    async def test_disconnect_before_at_not_counted(self):
        now = datetime.now(timezone.utc)
        await start_session(client_id="gone", user_id=None, is_anonymous=True, room_id="r1")
        await end_session("gone")
        data = await count_online_at(now + timedelta(seconds=5))
        assert data["total_unique"] == 0

    async def test_reconnect_creates_new_active_window(self):
        await start_session(client_id="rc", user_id=None, is_anonymous=True, room_id="r1")
        await end_session("rc")
        between = datetime.now(timezone.utc)
        assert (await count_online_at(between))["total_unique"] == 0
        await start_session(client_id="rc", user_id=None, is_anonymous=True, room_id="r1")
        assert (await count_online_at(datetime.now(timezone.utc)))["total_unique"] == 1

    async def test_at_before_connect_is_zero(self):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        await start_session(client_id="late", user_id=None, is_anonymous=True, room_id="r1")
        data = await count_online_at(past)
        assert data["total_unique"] == 0


def _insert_presence_session(
    *,
    client_id: str,
    connected_at: datetime,
    disconnected_at: datetime | None = None,
    user_id: uuid.UUID | None = None,
    is_anonymous: bool = True,
    room_id: str | None = None,
) -> None:
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO presence_sessions (
                id, client_id, user_id, is_anonymous, room_id,
                connected_at, disconnected_at, last_seen_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid.uuid4()),
                client_id,
                str(user_id) if user_id else None,
                is_anonymous,
                room_id,
                connected_at,
                disconnected_at,
                connected_at if room_id is None else None,
            ),
        )
    conn.close()


@pytest.mark.asyncio
class TestOnlinePeriodStats:
    async def test_empty_period_returns_zero(self):
        start = datetime(2099, 1, 1, tzinfo=timezone.utc)
        end = datetime(2099, 1, 2, tzinfo=timezone.utc)
        data = await count_online_unique_in_period(start, end)
        assert data["total_unique"] == 0
        assert data["anonymous_unique"] == 0
        assert data["registered_unique"] == 0

    async def test_session_inside_period_counts_one(self):
        now = datetime.now(timezone.utc)
        _insert_presence_session(
            client_id="period-anon",
            connected_at=now - timedelta(hours=1),
            disconnected_at=now - timedelta(minutes=30),
        )
        data = await count_online_unique_in_period(
            now - timedelta(days=1),
            now + timedelta(minutes=1),
        )
        assert data["total_unique"] == 1
        assert data["anonymous_unique"] == 1

    async def test_session_ended_before_period_not_counted(self):
        now = datetime.now(timezone.utc)
        _insert_presence_session(
            client_id="period-old",
            connected_at=now - timedelta(days=10),
            disconnected_at=now - timedelta(days=9),
        )
        data = await count_online_unique_in_period(
            now - timedelta(days=7),
            now,
        )
        assert data["total_unique"] == 0

    async def test_same_user_two_sessions_counts_once(self, register_user):
        reg = register_user("period_dual")
        user_id = uuid.UUID(reg["user"]["id"])
        now = datetime.now(timezone.utc)
        _insert_presence_session(
            client_id="tab-a",
            user_id=user_id,
            is_anonymous=False,
            room_id="room0001",
            connected_at=now - timedelta(hours=2),
            disconnected_at=now - timedelta(hours=1),
        )
        _insert_presence_session(
            client_id="tab-b",
            user_id=user_id,
            is_anonymous=False,
            room_id="room0002",
            connected_at=now - timedelta(minutes=30),
            disconnected_at=None,
        )
        data = await count_online_unique_in_period(now - timedelta(days=1), now + timedelta(minutes=1))
        assert data["total_unique"] == 1
        assert data["registered_unique"] == 1

    async def test_two_anonymous_clients_counts_two(self):
        now = datetime.now(timezone.utc)
        _insert_presence_session(
            client_id="anon-a",
            connected_at=now - timedelta(hours=1),
        )
        _insert_presence_session(
            client_id="anon-b",
            connected_at=now - timedelta(minutes=20),
        )
        data = await count_online_unique_in_period(now - timedelta(days=1), now + timedelta(minutes=1))
        assert data["total_unique"] == 2
        assert data["anonymous_unique"] == 2

    def test_http_online_period_endpoint(self, client, admin_headers):
        now = datetime.now(timezone.utc)
        _insert_presence_session(
            client_id="http-period",
            connected_at=now - timedelta(minutes=5),
        )
        r = client.get("/api/admin/stats/online/period?period=7d", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["total_unique"] >= 1
        assert "from" in body
        assert "to" in body
        assert body["registered_unique"] + body["anonymous_unique"] >= body["total_unique"] - 1


class TestGamesStats:
    def test_anonymous_player_count_pvp(self):
        assert anonymous_player_count("public", False, False) == 0
        assert anonymous_player_count("public", True, False) == 1
        assert anonymous_player_count("private", True, True) == 2

    def test_anonymous_player_count_ai(self):
        assert anonymous_player_count("ai", False, False) == 0
        assert anonymous_player_count("ai", True, False) == 1
        assert anonymous_player_count("ai", False, True) == 1

    def test_games_breakdown_and_filters(self, client, admin_headers):
        now = datetime.now(timezone.utc)
        insert_finished_game(
            room_id="pub1",
            room_type="public",
            white_is_anonymous=False,
            black_is_anonymous=True,
            finished_at=now,
        )
        insert_finished_game(
            room_id="priv1",
            room_type="private",
            white_is_anonymous=True,
            black_is_anonymous=True,
            finished_at=now,
        )
        insert_finished_game(
            room_id="ai1",
            room_type="ai",
            white_is_anonymous=True,
            black_is_anonymous=False,
            finished_at=now,
        )

        r = client.get("/api/admin/stats/games?period=24h", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert body["by_room_type"]["public"] == 1
        assert body["by_room_type"]["private"] == 1
        assert body["by_room_type"]["ai"] == 1
        assert body["by_anonymous_count"]["1"] == 2
        assert body["by_anonymous_count"]["2"] == 1

    def test_games_filter_room_type(self, client, admin_headers):
        now = datetime.now(timezone.utc)
        insert_finished_game(room_type="public", finished_at=now)
        insert_finished_game(room_id="p2", room_type="private", finished_at=now)

        r = client.get(
            "/api/admin/stats/games?period=24h&room_type=private",
            headers=admin_headers,
        )
        assert r.json()["total"] == 1
        assert r.json()["by_room_type"]["private"] == 1
        assert r.json()["by_room_type"]["public"] == 0

    def test_games_filter_anonymous_players(self, client, admin_headers):
        now = datetime.now(timezone.utc)
        insert_finished_game(
            room_type="public",
            white_is_anonymous=False,
            black_is_anonymous=False,
            finished_at=now,
        )
        insert_finished_game(
            room_id="x2",
            room_type="public",
            white_is_anonymous=True,
            black_is_anonymous=False,
            finished_at=now,
        )

        r = client.get(
            "/api/admin/stats/games?period=24h&anonymous_players=1",
            headers=admin_headers,
        )
        assert r.json()["total"] == 1

    def test_rematch_two_rows_same_room(self, client, admin_headers):
        now = datetime.now(timezone.utc)
        insert_finished_game(room_id="same123", finished_at=now - timedelta(minutes=5))
        insert_finished_game(room_id="same123", finished_at=now)
        r = client.get("/api/admin/stats/games?period=24h", headers=admin_headers)
        assert r.json()["total"] == 2

    @pytest.mark.asyncio
    async def test_count_games_service(self):
        factory = get_session_factory()
        async with factory() as db:
            data = await count_games(db, period="all")
        assert "total" in data
        assert "by_room_type" in data


class TestParseTimeRange:
    @pytest.mark.parametrize(
        ("period", "hours"),
        [("1h", 1), ("3h", 3), ("6h", 6), ("12h", 12), ("24h", 24)],
    )
    def test_hour_periods(self, period, hours):
        start, end = parse_time_range(period=period)
        assert end > start
        assert abs((end - start).total_seconds() - hours * 3600) < 2

    def test_period_7d(self):
        start, end = parse_time_range(period="7d")
        assert (end - start).days == 7

    def test_custom_range(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 31, tzinfo=timezone.utc)
        parsed_start, parsed_end = parse_time_range(from_dt=start, to_dt=end)
        assert parsed_start == start
        assert parsed_end == end

    def test_unknown_period_raises(self):
        with pytest.raises(ValueError, match="Unknown period"):
            parse_time_range(period="today")


class TestPeriodValidation:
    def test_registrations_accepts_1h(self, client, admin_headers):
        r = client.get("/api/admin/stats/registrations?period=1h", headers=admin_headers)
        assert r.status_code == 200
        assert "total" in r.json()

    def test_registrations_rejects_unknown_period(self, client, admin_headers):
        r = client.get("/api/admin/stats/registrations?period=today", headers=admin_headers)
        assert r.status_code == 422

    def test_games_accepts_6h(self, client, admin_headers):
        r = client.get("/api/admin/stats/games?period=6h", headers=admin_headers)
        assert r.status_code == 200
        assert "total" in r.json()


class TestSeriesAuth:
    def test_registrations_series_requires_auth(self, client):
        r = client.get("/api/admin/stats/registrations/series")
        assert r.status_code == 401

    def test_registrations_series_forbidden(self, client, regular_headers):
        r = client.get("/api/admin/stats/registrations/series", headers=regular_headers)
        assert r.status_code == 403

    def test_games_series_requires_auth(self, client):
        r = client.get("/api/admin/stats/games/series")
        assert r.status_code == 401

    def test_online_series_forbidden(self, client, regular_headers):
        r = client.get("/api/admin/stats/online/series", headers=regular_headers)
        assert r.status_code == 403


class TestRegistrationSeries:
    def test_series_hour_granularity_for_24h(self, client, admin_headers):
        now = datetime.now(timezone.utc)
        insert_user_created_at(now - timedelta(hours=2))
        r = client.get("/api/admin/stats/registrations/series?period=24h", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["granularity"] == "hour"
        assert len(body["buckets"]) >= 1
        assert sum(b["count"] for b in body["buckets"]) >= 1

    def test_series_fills_zero_buckets(self, client, admin_headers):
        r = client.get("/api/admin/stats/registrations/series?period=7d", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        buckets = body["buckets"]
        start, end = parse_time_range(period="7d")
        expected_len = len(iter_buckets(start, end, body["granularity"]))
        assert len(buckets) == expected_len
        assert all("ts" in b and "count" in b for b in buckets)


class TestGamesSeries:
    def test_series_respects_filters(self, client, admin_headers):
        now = datetime.now(timezone.utc)
        insert_finished_game(room_id="pub1", room_type="public", finished_at=now - timedelta(days=1))
        insert_finished_game(room_id="ai1", room_type="ai", finished_at=now - timedelta(days=1))
        r = client.get(
            "/api/admin/stats/games/series?period=7d&room_type=public",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert sum(b["count"] for b in r.json()["buckets"]) == 1


class TestOnlineSeries:
    def test_online_series_counts_session(self, client, admin_headers):
        now = datetime.now(timezone.utc)
        mid = now - timedelta(hours=12)
        _insert_presence_session(
            client_id="series-client",
            connected_at=mid - timedelta(hours=1),
            disconnected_at=mid + timedelta(hours=1),
        )

        r = client.get("/api/admin/stats/online/series?period=24h", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["granularity"] == "hour"
        assert any(b["total_unique"] >= 1 for b in body["buckets"])


class TestBucketHelpers:
    def test_infer_granularity_hour_vs_day(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert infer_granularity(start, start + timedelta(hours=24)) == "hour"
        assert infer_granularity(start, start + timedelta(days=3)) == "day"

    def test_iter_buckets_day_count(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 8, tzinfo=timezone.utc)
        assert len(iter_buckets(start, end, "day")) == 7


class TestSeriesBucketInvariant:
    """HTTP series responses must align with iter_buckets (prevents off-by-one charts)."""

    @pytest.mark.parametrize(
        ("path", "query"),
        [
            ("/api/admin/stats/registrations/series", "period=7d"),
            ("/api/admin/stats/games/series", "period=7d"),
            ("/api/admin/stats/online/series", "period=24h"),
        ],
    )
    def test_bucket_count_matches_range(self, client, admin_headers, path, query):
        r = client.get(f"{path}?{query}", headers=admin_headers)
        assert r.status_code == 200
        assert_series_buckets_match(r.json())

    def test_custom_from_to_series(self, client, admin_headers):
        start = datetime(2026, 5, 1, tzinfo=timezone.utc)
        end = datetime(2026, 5, 4, tzinfo=timezone.utc)
        qs = f"from={quote(start.isoformat())}&to={quote(end.isoformat())}"
        r = client.get(f"/api/admin/stats/registrations/series?{qs}", headers=admin_headers)
        assert r.status_code == 200
        assert_series_buckets_match(r.json())
        assert r.json()["granularity"] == "day"


class TestRegistrationSeriesExtended:
    def test_registration_in_correct_day_bucket(self, client, admin_headers):
        ts = datetime.now(timezone.utc) - timedelta(days=1)
        insert_user_created_at(ts)
        r = client.get("/api/admin/stats/registrations/series?period=7d", headers=admin_headers)
        assert r.status_code == 200
        assert sum(b["count"] for b in r.json()["buckets"]) >= 1


class TestGamesSeriesExtended:
    def test_anonymous_players_filter_on_series(self, client, admin_headers):
        now = datetime.now(timezone.utc)
        insert_finished_game(
            room_id="anongame",
            room_type="public",
            white_is_anonymous=True,
            black_is_anonymous=False,
            finished_at=now - timedelta(hours=2),
        )
        insert_finished_game(
            room_id="reggame1",
            room_type="public",
            white_is_anonymous=False,
            black_is_anonymous=False,
            finished_at=now - timedelta(hours=2),
        )
        r = client.get(
            "/api/admin/stats/games/series?period=24h&anonymous_players=1",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert sum(b["count"] for b in r.json()["buckets"]) == 1


class TestOnlineSeriesExtended:
    def test_online_series_bucket_count(self, client, admin_headers):
        r = client.get("/api/admin/stats/online/series?period=24h", headers=admin_headers)
        assert r.status_code == 200
        assert_series_buckets_match(r.json())
