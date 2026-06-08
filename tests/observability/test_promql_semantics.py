"""Document PromQL pitfalls that made Grafana show 0 despite recorded games."""

from __future__ import annotations

import pytest

from tests.observability.prometheus_helpers import parse_counter, promql_increase_flat_counter


def test_flat_counter_increase_is_zero_while_total_is_nonzero():
    """After one game, counter stays at 1 — increase() over 1h is 0, total is 1."""
    samples = [1.0, 1.0, 1.0, 1.0]
    assert promql_increase_flat_counter(samples) == 0.0
    assert samples[-1] == 1.0


def test_increase_detects_change_within_window():
    samples = [0.0, 0.0, 1.0, 1.0]
    assert promql_increase_flat_counter(samples) == 1.0


def test_parse_counter_matches_prometheus_text():
    body = """
# HELP shatra_games_started_total Games started
# TYPE shatra_games_started_total counter
shatra_games_started_total{room_type="public"} 2.0
"""
    assert parse_counter(body, "shatra_games_started_total", {"room_type": "public"}) == 2.0


def test_cumulative_query_reflects_recorded_games():
    """Grafana must use this style of query for sparse counters."""
    body = """
shatra_games_finished_total{reason="resign",room_type="public"} 1.0
"""
    cumulative = parse_counter(
        body,
        "shatra_games_finished_total",
        {"reason": "resign", "room_type": "public"},
    )
    increase_over_hour = promql_increase_flat_counter([cumulative] * 4)
    assert cumulative == 1.0
    assert increase_over_hour == 0.0, (
        "increase() over a flat window hides finished games — use _total in dashboard"
    )
