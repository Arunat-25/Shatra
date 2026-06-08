"""Prometheus metrics registry and helpers."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

WS_CONNECTIONS_ACTIVE = Gauge(
    "shatra_ws_connections_active",
    "Active WebSocket connections",
)

WS_EVENTS_TOTAL = Counter(
    "shatra_ws_events_total",
    "WebSocket lifecycle events",
    ["event", "reason"],
)

ROOMS_CREATED_TOTAL = Counter(
    "shatra_rooms_created_total",
    "Rooms created",
    ["room_type"],
)

GAMES_STARTED_TOTAL = Counter(
    "shatra_games_started_total",
    "Games started",
    ["room_type"],
)

GAMES_FINISHED_TOTAL = Counter(
    "shatra_games_finished_total",
    "Games finished",
    ["reason", "room_type"],
)

MOVES_TOTAL = Counter(
    "shatra_moves_total",
    "Moves processed",
    ["source"],
)

MOVES_REJECTED_TOTAL = Counter(
    "shatra_moves_rejected_total",
    "Rejected move attempts",
    ["reason"],
)

TIMEOUTS_TOTAL = Counter(
    "shatra_timeouts_total",
    "Game timeouts and disconnect forfeits",
    ["type"],
)

ARCHIVE_ERRORS_TOTAL = Counter(
    "shatra_archive_errors_total",
    "Failed game archive attempts",
)

REDIS_ROOMS_ACTIVE = Gauge(
    "shatra_redis_rooms_active",
    "Room keys currently stored in Redis",
    ["room_type"],
)

REDIS_GAMES_ACTIVE = Gauge(
    "shatra_redis_games_active",
    "Game keys currently stored in Redis",
    ["game_over"],
)

REDIS_ROOMS_WAITING = Gauge(
    "shatra_redis_rooms_waiting",
    "Public rooms waiting for a second player",
    ["room_type"],
)

GAME_PLIES = Histogram(
    "shatra_game_plies",
    "Plies in finished games",
    ["room_type", "reason"],
    buckets=(1, 5, 10, 20, 40, 60, 100, 150, 200),
)

GAME_DURATION_SECONDS = Histogram(
    "shatra_game_duration_seconds",
    "Wall-clock duration of finished games",
    ["room_type", "reason"],
    buckets=(30, 60, 120, 300, 600, 1200, 1800, 3600),
)


def metrics_payload() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


def record_ws_connect(*, reason: str = "") -> None:
    WS_CONNECTIONS_ACTIVE.inc()
    WS_EVENTS_TOTAL.labels(event="connect", reason=reason or "ok").inc()


def record_ws_disconnect(*, reason: str = "") -> None:
    WS_CONNECTIONS_ACTIVE.dec()
    WS_EVENTS_TOTAL.labels(event="disconnect", reason=reason or "ok").inc()


def record_ws_reject(reason: str) -> None:
    WS_EVENTS_TOTAL.labels(event="reject", reason=reason).inc()


def record_game_started(room_type: str) -> None:
    GAMES_STARTED_TOTAL.labels(room_type=room_type or "unknown").inc()


def record_room_created(room_type: str) -> None:
    ROOMS_CREATED_TOTAL.labels(room_type=room_type or "unknown").inc()


def record_move(source: str) -> None:
    MOVES_TOTAL.labels(source=source).inc()


def record_move_rejected(reason: str) -> None:
    MOVES_REJECTED_TOTAL.labels(reason=reason or "unknown").inc()


def record_timeout(timeout_type: str) -> None:
    TIMEOUTS_TOTAL.labels(type=timeout_type).inc()


def record_archive_error() -> None:
    ARCHIVE_ERRORS_TOTAL.inc()


def record_game_finished(
    *,
    reason: str,
    room_type: str,
    plies: int = 0,
    duration_seconds: float | None = None,
) -> None:
    labels = {
        "reason": reason or "unknown",
        "room_type": room_type or "unknown",
    }
    GAMES_FINISHED_TOTAL.labels(**labels).inc()
    if plies > 0:
        GAME_PLIES.labels(**labels).observe(plies)
    if duration_seconds is not None and duration_seconds >= 0:
        GAME_DURATION_SECONDS.labels(**labels).observe(duration_seconds)
