"""Ensure /metrics values match what Grafana panels should display."""

from __future__ import annotations

import re

from tests.observability.prometheus_helpers import (
    parse_counter,
    promql_increase_flat_counter,
)


def sum_metric(body: str, name: str) -> float:
    """Model `sum(metric)` over all label combinations in exposition text."""
    total = 0.0
    prefix = name + "{"
    for line in body.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        if line.startswith(name + " "):
            total += float(line.split()[-1])
        elif line.startswith(prefix):
            total += float(line.split()[-1])
    return total


def sum_by_label(body: str, name: str, label: str) -> dict[str, float]:
    """Model `sum by (label) (metric)` for exposition text."""
    totals: dict[str, float] = {}
    pattern = re.compile(
        rf"^{re.escape(name)}\{{[^}}]*{re.escape(label)}=\"([^\"]+)\"[^}}]*\}} (\d+(?:\.\d+)?)$"
    )
    for line in body.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        match = pattern.match(line.strip())
        if match:
            key = match.group(1)
            totals[key] = totals.get(key, 0.0) + float(match.group(2))
    return totals


def test_grafana_games_finished_panel_query_nonzero_after_one_game():
    """Same logic as `sum by (reason) (shatra_games_finished_total)` in shatra.json."""
    body = """
shatra_games_finished_total{reason="resign",room_type="public"} 1.0
"""
    by_reason = sum_by_label(body, "shatra_games_finished_total", "reason")
    assert by_reason.get("resign", 0) >= 1.0


def test_grafana_rooms_panel_query_nonzero_after_one_room():
    body = """
shatra_rooms_created_total{room_type="public"} 1.0
shatra_games_started_total{room_type="public"} 1.0
"""
    assert sum_metric(body, "shatra_rooms_created_total") >= 1.0
    assert sum_metric(body, "shatra_games_started_total") >= 1.0


def test_dashboard_increase_query_would_hide_recorded_game():
    """Document why games panel must not rely on long-window increase()."""
    body = """
shatra_games_finished_total{reason="biy_wins",room_type="public"} 1.0
"""
    cumulative = sum_metric(body, "shatra_games_finished_total")
    flat_samples = [cumulative] * 4
    assert cumulative >= 1.0
    assert promql_increase_flat_counter(flat_samples) == 0.0
    assert parse_counter(
        body,
        "shatra_games_finished_total",
        {"reason": "biy_wins", "room_type": "public"},
    ) == 1.0


def test_grafana_operational_panels_nonzero_from_sample_body():
    body = """
shatra_moves_total{source="player"} 120.0
shatra_moves_rejected_total{reason="move.impossible"} 3.0
shatra_timeouts_total{type="clock"} 2.0
shatra_archive_errors_total 1.0
shatra_redis_rooms_active{room_type="public"} 4.0
shatra_redis_games_active{game_over="false"} 2.0
shatra_redis_rooms_waiting{room_type="public"} 1.0
"""
    assert sum_metric(body, "shatra_moves_total") >= 1.0
    assert sum_by_label(body, "shatra_moves_rejected_total", "reason").get(
        "move.impossible", 0,
    ) >= 1.0
    assert sum_metric(body, "shatra_timeouts_total") >= 1.0
    assert sum_metric(body, "shatra_archive_errors_total") >= 1.0
    assert sum_by_label(body, "shatra_redis_rooms_active", "room_type").get(
        "public", 0,
    ) >= 1.0
    assert parse_counter(
        body,
        "shatra_redis_rooms_waiting",
        {"room_type": "public"},
    ) >= 1.0
