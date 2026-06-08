"""Ensure Grafana dashboard queries stay truthful for sparse counters."""

from __future__ import annotations

import json
import re

import pytest

from tests.observability.prometheus_helpers import (
    FORBIDDEN_REDIS_GAUGE_INCREASE,
    FORBIDDEN_SPARSE_INCREASE,
    GRAFANA_DASHBOARD,
    load_dashboard_exprs,
    load_dashboard_sql,
    redis_gauge_panel_exprs,
    sparse_counter_panel_exprs,
)

REQUIRED_CUMULATIVE = {
    "Games finished (total since app start)": r"shatra_games_finished_total",
    "Rooms created / games started (total)": r"shatra_(rooms_created_total|games_started_total)",
    "Timeouts (total)": r"shatra_timeouts_total",
    "Archive errors (total)": r"shatra_archive_errors_total",
}

REQUIRED_REDIS_GAUGES = {
    "Redis rooms (current)": r"shatra_redis_rooms_active",
    "Redis games (current)": r"shatra_redis_games_active",
    "Public rooms waiting for opponent": r"shatra_redis_rooms_waiting",
}

REQUIRED_RATE_PANELS = {
    "Moves rate": r"rate\(shatra_moves_total\[5m\]\)",
    "Rejected moves rate": r"rate\(shatra_moves_rejected_total\[5m\]\)",
}

REQUIRED_HISTOGRAM_PANELS = {
    "Game duration p95 / plies p50": r"shatra_game_duration_seconds_bucket",
}


def test_dashboard_file_exists():
    assert GRAFANA_DASHBOARD.is_file()


def test_all_panels_have_queries():
    data = json.loads(GRAFANA_DASHBOARD.read_text(encoding="utf-8"))
    panels = data.get("panels", [])
    assert len(panels) >= 16
    for panel in panels:
        title = panel.get("title", "")
        targets = panel.get("targets", [])
        assert targets, f"panel {title!r} has no targets"
        for target in targets:
            assert target.get("expr") or target.get("rawSql"), (
                f"panel {title!r} target missing expr/rawSql"
            )


@pytest.mark.parametrize("title,pattern", list(REQUIRED_CUMULATIVE.items()))
def test_sparse_counter_panels_use_cumulative_queries(title, pattern):
    exprs = dict(load_dashboard_exprs())
    assert title in exprs, f"missing panel {title!r}"
    assert re.search(pattern, exprs[title]), (
        f"panel {title!r} must use cumulative counter, got: {exprs[title]}"
    )


@pytest.mark.parametrize("title,pattern", list(REQUIRED_REDIS_GAUGES.items()))
def test_redis_panels_use_gauge_queries(title, pattern):
    exprs = dict(load_dashboard_exprs())
    assert title in exprs, f"missing panel {title!r}"
    assert re.search(pattern, exprs[title]), (
        f"panel {title!r} must query Redis gauge, got: {exprs[title]}"
    )


@pytest.mark.parametrize("title,pattern", list(REQUIRED_RATE_PANELS.items()))
def test_rate_panels_use_short_window(title, pattern):
    exprs = dict(load_dashboard_exprs())
    assert title in exprs, f"missing panel {title!r}"
    assert re.search(pattern, exprs[title]), (
        f"panel {title!r} must use rate() with 5m window, got: {exprs[title]}"
    )


@pytest.mark.parametrize("title,pattern", list(REQUIRED_HISTOGRAM_PANELS.items()))
def test_histogram_panels_use_buckets(title, pattern):
    exprs = [expr for panel_title, expr in load_dashboard_exprs() if panel_title == title]
    assert exprs, f"missing panel {title!r}"
    assert any(re.search(pattern, expr) for expr in exprs), (
        f"panel {title!r} must use histogram buckets, got: {exprs}"
    )


def test_postgres_reconciliation_panel_queries_finished_games():
    sql_by_title = dict(load_dashboard_sql())
    assert "Games archived (last 1h, Postgres)" in sql_by_title
    assert "finished_games" in sql_by_title["Games archived (last 1h, Postgres)"].lower()


def test_sparse_counter_panels_do_not_use_long_window_increase():
    violations = []
    for title, expr in sparse_counter_panel_exprs():
        if FORBIDDEN_SPARSE_INCREASE.search(expr):
            violations.append(f"{title}: {expr}")
    assert not violations, (
        "long-window increase() on game/room counters shows 0 after events; "
        "use cumulative _total or short rate windows for high-frequency metrics only:\n"
        + "\n".join(violations)
    )


def test_redis_gauge_panels_do_not_use_increase():
    violations = []
    for title, expr in redis_gauge_panel_exprs():
        if FORBIDDEN_REDIS_GAUGE_INCREASE.search(expr):
            violations.append(f"{title}: {expr}")
    assert not violations, (
        "Redis gauges are point-in-time; increase() hides current room count:\n"
        + "\n".join(violations)
    )


def test_games_finished_panel_uses_cumulative_total_not_increase():
    """Regression: increase(shatra_games_finished_total[1h]) hid finished games in Grafana."""
    title, expr = next(
        (pair for pair in load_dashboard_exprs() if "Games finished" in pair[0]),
    )
    assert "increase(" not in expr, (
        f"panel {title!r} must not use increase() on sparse counter: {expr}"
    )
    assert "shatra_games_finished_total" in expr
