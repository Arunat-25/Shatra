"""Shared helpers for metrics text parsing and PromQL sanity checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAFANA_DASHBOARD = REPO_ROOT / "docker" / "grafana" / "dashboards" / "shatra.json"

# Long-window increase() on sparse counters shows 0 while games actually happened.
FORBIDDEN_SPARSE_INCREASE = re.compile(
    r"increase\(\s*shatra_(games|rooms)_[a-z_]+(\{[^}]*\})?\s*\[\s*[1-9][0-9]*h\s*\]",
    re.IGNORECASE,
)

SPARSE_COUNTERS = (
    "shatra_games_finished_total",
    "shatra_games_started_total",
    "shatra_rooms_created_total",
)

REDIS_GAUGES = (
    "shatra_redis_rooms_active",
    "shatra_redis_games_active",
    "shatra_redis_rooms_waiting",
)

FORBIDDEN_REDIS_GAUGE_INCREASE = re.compile(
    r"increase\(\s*shatra_redis_[a-z_]+",
    re.IGNORECASE,
)


def get_metrics_text(client) -> str:
    """GET /metrics with Bearer token when METRICS_TOKEN is configured."""
    from backend.config import settings

    headers: dict[str, str] = {}
    token = (settings.metrics_token or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = client.get("/metrics", headers=headers)
    assert response.status_code == 200, response.text
    return response.text


def parse_gauge(body: str, name: str, labels: dict[str, str] | None = None) -> float:
    """Parse a Prometheus text exposition gauge line."""
    return parse_counter(body, name, labels)


def parse_counter(body: str, name: str, labels: dict[str, str] | None = None) -> float:
    """Parse a Prometheus text exposition counter line."""
    label_parts = ""
    if labels:
        label_parts = "{" + ",".join(
            f'{key}="{value}"' for key, value in sorted(labels.items())
        ) + "}"
    pattern = rf"^{re.escape(name)}{re.escape(label_parts)} (\d+(?:\.\d+)?)$"
    total = 0.0
    for line in body.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        match = re.match(pattern, line.strip())
        if match:
            total += float(match.group(1))
    return total


def promql_increase_flat_counter(samples: list[float]) -> float:
    """Model PromQL increase() when counter stayed flat in the selected window."""
    if len(samples) < 2:
        return 0.0
    return max(0.0, samples[-1] - samples[0])


def load_dashboard_exprs() -> list[tuple[str, str]]:
    """Return (panel_title, expr) pairs from the Shatra Grafana dashboard."""
    data = json.loads(GRAFANA_DASHBOARD.read_text(encoding="utf-8"))
    pairs: list[tuple[str, str]] = []
    for panel in data.get("panels", []):
        title = panel.get("title", "")
        for target in panel.get("targets", []):
            expr = target.get("expr")
            if expr:
                pairs.append((title, expr))
    return pairs


def load_dashboard_sql() -> list[tuple[str, str]]:
    """Return (panel_title, rawSql) pairs from Postgres panels."""
    data = json.loads(GRAFANA_DASHBOARD.read_text(encoding="utf-8"))
    pairs: list[tuple[str, str]] = []
    for panel in data.get("panels", []):
        title = panel.get("title", "")
        for target in panel.get("targets", []):
            sql = target.get("rawSql")
            if sql:
                pairs.append((title, sql))
    return pairs


def sparse_counter_panel_exprs() -> list[tuple[str, str]]:
    """Panels that track low-frequency game/room counters."""
    result = []
    for title, expr in load_dashboard_exprs():
        if any(name in expr for name in SPARSE_COUNTERS):
            result.append((title, expr))
    return result


def redis_gauge_panel_exprs() -> list[tuple[str, str]]:
    """Panels that display Redis gauge metrics."""
    result = []
    for title, expr in load_dashboard_exprs():
        if any(name in expr for name in REDIS_GAUGES):
            result.append((title, expr))
    return result
