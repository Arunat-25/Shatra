"""Prometheus alert rule regression tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ALERTS_FILE = REPO_ROOT / "docker" / "prometheus" / "alerts.yml"
PROMETHEUS_CONFIG = REPO_ROOT / "docker" / "prometheus" / "prometheus.yml"

FORBIDDEN_SPARSE_INCREASE_IN_ALERTS = re.compile(
    r"increase\(\s*shatra_games_[a-z_]+\[1h\]",
    re.IGNORECASE,
)

REQUIRED_ALERTS = {
    "ShatraTargetDown": r"up\{job=\"shatra\"\}",
    "ShatraArchiveErrors": r"shatra_archive_errors_total",
    "ShatraHighMoveRejectRate": r"shatra_moves_rejected_total",
    "ShatraRedisRoomsLeak": r"shatra_redis_rooms_active",
}


def _load_alert_rules() -> list[dict]:
    data = yaml.safe_load(ALERTS_FILE.read_text(encoding="utf-8"))
    groups = data.get("groups", [])
    rules: list[dict] = []
    for group in groups:
        rules.extend(group.get("rules", []))
    return rules


def test_alerts_file_exists():
    assert ALERTS_FILE.is_file()


def test_prometheus_config_loads_alerts():
    config = yaml.safe_load(PROMETHEUS_CONFIG.read_text(encoding="utf-8"))
    assert "alerts.yml" in config.get("rule_files", [])


@pytest.mark.parametrize("alert_name,pattern", list(REQUIRED_ALERTS.items()))
def test_required_alerts_present(alert_name, pattern):
    rules = {rule["alert"]: rule for rule in _load_alert_rules()}
    assert alert_name in rules, f"missing alert {alert_name!r}"
    assert re.search(pattern, rules[alert_name]["expr"]), (
        f"alert {alert_name!r} expr unexpected: {rules[alert_name]['expr']}"
    )


def test_alerts_do_not_use_bad_sparse_game_increase():
    violations = []
    for rule in _load_alert_rules():
        expr = rule.get("expr", "")
        if FORBIDDEN_SPARSE_INCREASE_IN_ALERTS.search(expr):
            violations.append(f"{rule['alert']}: {expr}")
    assert not violations, (
        "increase(shatra_games_*[1h]) hides finished games in sparse counters:\n"
        + "\n".join(violations)
    )
