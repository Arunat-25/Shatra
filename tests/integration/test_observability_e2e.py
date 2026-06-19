"""Integration tests for observability metrics and health."""

from __future__ import annotations

import os
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

import tests.test_env  # noqa: F401

from backend.board_utils import get_starting_board, keys_int_to_str
from backend.game_archive import on_game_finished
from backend.models import CreateRoomRequest
from backend.room_manager import create_room
from backend.state import close_redis, get_game, get_room, init_redis, set_game, set_room
from backend.ws_manager import handle_player2_join, manager
from main import app
from tests.integration.helpers import new_client_id
from tests.observability.prometheus_helpers import (
    get_metrics_text,
    parse_counter,
    parse_gauge,
    promql_increase_flat_counter,
)
from tests.observability.test_metrics_dashboard_alignment import sum_by_label, sum_metric

pytestmark = pytest.mark.integration


def _metric_delta(client: TestClient, name: str, labels: dict[str, str], action) -> float:
    before = parse_counter(get_metrics_text(client), name, labels)
    action()
    after = parse_counter(get_metrics_text(client), name, labels)
    return after - before


def _grafana_games_finished_total(metrics_body: str) -> float:
    return sum_metric(metrics_body, "shatra_games_finished_total")


def test_create_room_increments_rooms_created_metric():
    with TestClient(app) as client:
        delta = _metric_delta(
            client,
            "shatra_rooms_created_total",
            {"room_type": "public"},
            lambda: client.post(
                "/rooms",
                json={
                    "type": "public",
                    "creator_client_id": new_client_id(),
                    "color_preference": "белый",
                },
            ),
        )
    assert delta == 1.0


def test_create_room_exposes_redis_room_gauge():
    with TestClient(app) as client:
        client.post(
            "/rooms",
            json={
                "type": "public",
                "creator_client_id": new_client_id(),
                "color_preference": "белый",
            },
        )
        body = get_metrics_text(client)
        waiting = parse_gauge(
            body,
            "shatra_redis_rooms_waiting",
            {"room_type": "public"},
        )
        rooms = parse_gauge(body, "shatra_redis_rooms_active", {"room_type": "public"})
    assert rooms >= 1.0
    assert waiting >= 1.0


@pytest.mark.asyncio
async def test_pvp_resign_increments_games_finished_metric():
    from unittest.mock import AsyncMock

    from backend.db.models import User
    from backend.db.session import get_session_factory
    from backend.ws_control_handlers import handle_resign

    await init_redis()
    try:
        host_id = new_client_id()
        guest_id = new_client_id()
        factory = get_session_factory()
        async with factory() as session:
            host_user = User(
                username=f"obs_host_{uuid.uuid4().hex[:8]}",
                username_normalized=f"obs_host_{uuid.uuid4().hex[:8]}",
                password_hash="hash",
            )
            session.add(host_user)
            await session.commit()
            await session.refresh(host_user)

        result = await create_room(
            CreateRoomRequest(type="public", creator_client_id=host_id),
            user=host_user,
        )
        room_id = result["room_id"]

        async def _connect(client_id: str, user: User | None):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ok = await manager.connect(room_id, ws, client_id, user=user)
            assert ok is True
            return ws

        await _connect(host_id, host_user)
        await _connect(guest_id, None)
        room_data = await get_room(room_id)
        await handle_player2_join(room_id, room_data)
        ws = AsyncMock()
        await handle_resign(room_id, host_id, ws, is_ai_room=False)
        await on_game_finished(room_id)

        with TestClient(app) as client:
            body = get_metrics_text(client)
            value = parse_counter(
                body,
                "shatra_games_finished_total",
                {"reason": "resign", "room_type": "public"},
            )
            grafana_total = _grafana_games_finished_total(body)
            by_reason = sum_by_label(body, "shatra_games_finished_total", "reason")
        assert value >= 1.0
        assert grafana_total >= 1.0
        assert by_reason.get("resign", 0) >= 1.0
        assert promql_increase_flat_counter([grafana_total] * 4) == 0.0

        factory = get_session_factory()
        async with factory() as session:
            from sqlalchemy import func, select

            from backend.db.models import FinishedGame

            db_count = await session.scalar(
                select(func.count()).select_from(FinishedGame),
            )
        assert int(db_count or 0) >= 1
        assert grafana_total >= 1.0
    finally:
        manager.connections.clear()
        await close_redis()


@pytest.mark.asyncio
async def test_cancelled_game_does_not_increment_finished_metric():
    await init_redis()
    try:
        room_id = "cancel-metrics"
        await set_room(
            room_id,
            {
                "room_id": room_id,
                "type": "public",
                "game_started": True,
                "players": {"a": "белый", "b": "черный"},
            },
        )
        await set_game(
            room_id,
            {
                "board": get_starting_board(),
                "mover": "белый",
                "game_over": True,
                "winner_color": "белый",
                "reason": "cancelled",
                "move_history": [],
            },
        )

        with TestClient(app) as client:
            before = parse_counter(
                get_metrics_text(client),
                "shatra_games_finished_total",
                {"reason": "cancelled", "room_type": "public"},
            )
            await on_game_finished(room_id)
            after = parse_counter(
                get_metrics_text(client),
                "shatra_games_finished_total",
                {"reason": "cancelled", "room_type": "public"},
            )
        assert after == before
    finally:
        await close_redis()


def test_health_live_dependencies():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["redis"] == "ok"
    assert data["postgres"] == "ok"


@pytest.mark.integration
def test_prometheus_scrape_matches_app_games_finished_when_available():
    """When docker compose Prometheus is up, scraped totals must not be hidden by increase()."""
    prometheus_url = os.getenv("PROMETHEUS_URL", "http://127.0.0.1:9090").rstrip("/")
    try:
        with httpx.Client(timeout=2.0) as client:
            prom_response = client.get(f"{prometheus_url}/api/v1/query", params={
                "query": "sum(shatra_games_finished_total)",
            })
    except httpx.HTTPError:
        pytest.skip("Prometheus not reachable — start docker compose for this check")

    if prom_response.status_code != 200:
        pytest.skip(f"Prometheus returned {prom_response.status_code}")

    payload = prom_response.json()
    if payload.get("status") != "success":
        pytest.skip("Prometheus query API unavailable")

    results = payload.get("data", {}).get("result", [])
    if not results:
        pytest.skip("No shatra_games_finished_total samples in Prometheus yet")

    prom_total = float(results[0]["value"][1])
    with TestClient(app) as client:
        app_total = _grafana_games_finished_total(get_metrics_text(client))

    assert prom_total >= 0.0
    assert app_total >= 0.0
    if app_total >= 1.0:
        assert prom_total >= 1.0, (
            "Grafana uses sum(shatra_games_finished_total); Prometheus scrape must reflect finished games"
        )
    assert promql_increase_flat_counter([prom_total] * 4) == 0.0
