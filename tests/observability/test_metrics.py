"""Tests for Prometheus metric helpers."""

import pytest
from prometheus_client import CONTENT_TYPE_LATEST

from backend.observability import metrics as m


def test_metrics_payload():
    body, content_type = m.metrics_payload()
    assert isinstance(body, bytes)
    assert content_type == CONTENT_TYPE_LATEST
    assert b"shatra_ws_connections_active" in body


def test_record_ws_connect_and_disconnect():
    gauge_before = m.WS_CONNECTIONS_ACTIVE._value.get()
    connect_before = m.WS_EVENTS_TOTAL.labels(event="connect", reason="ok")._value.get()
    disconnect_before = m.WS_EVENTS_TOTAL.labels(event="disconnect", reason="ok")._value.get()

    m.record_ws_connect()
    assert m.WS_CONNECTIONS_ACTIVE._value.get() == gauge_before + 1
    assert m.WS_EVENTS_TOTAL.labels(event="connect", reason="ok")._value.get() == connect_before + 1

    m.record_ws_disconnect()
    assert m.WS_CONNECTIONS_ACTIVE._value.get() == gauge_before
    assert m.WS_EVENTS_TOTAL.labels(event="disconnect", reason="ok")._value.get() == disconnect_before + 1


def test_record_ws_reject_does_not_change_gauge():
    gauge_before = m.WS_CONNECTIONS_ACTIVE._value.get()
    reject_before = m.WS_EVENTS_TOTAL.labels(event="reject", reason="room_full")._value.get()

    m.record_ws_reject("room_full")
    assert m.WS_CONNECTIONS_ACTIVE._value.get() == gauge_before
    assert (
        m.WS_EVENTS_TOTAL.labels(event="reject", reason="room_full")._value.get()
        == reject_before + 1
    )


@pytest.mark.parametrize(
    ("helper", "args", "metric", "labels"),
    [
        (m.record_room_created, ("public",), m.ROOMS_CREATED_TOTAL, {"room_type": "public"}),
        (m.record_game_started, ("ai",), m.GAMES_STARTED_TOTAL, {"room_type": "ai"}),
        (m.record_move, ("player",), m.MOVES_TOTAL, {"source": "player"}),
        (m.record_move_rejected, ("move.impossible",), m.MOVES_REJECTED_TOTAL, {"reason": "move.impossible"}),
        (m.record_timeout, ("clock",), m.TIMEOUTS_TOTAL, {"type": "clock"}),
    ],
)
def test_record_helpers_increment_counters(helper, args, metric, labels):
    label = metric.labels(**labels)
    before = label._value.get()
    helper(*args)
    assert label._value.get() == before + 1


def test_record_archive_error():
    before = m.ARCHIVE_ERRORS_TOTAL._value.get()
    m.record_archive_error()
    assert m.ARCHIVE_ERRORS_TOTAL._value.get() == before + 1


def test_record_game_finished():
    label = m.GAMES_FINISHED_TOTAL.labels(reason="resign", room_type="public")
    before = label._value.get()
    m.record_game_finished(reason="resign", room_type="public")
    assert label._value.get() == before + 1


def test_record_game_finished_observes_histograms():
    plies_label = m.GAME_PLIES.labels(reason="resign", room_type="public")
    duration_label = m.GAME_DURATION_SECONDS.labels(reason="resign", room_type="public")
    plies_before = plies_label._sum.get()
    duration_before = duration_label._sum.get()

    m.record_game_finished(
        reason="resign",
        room_type="public",
        plies=25,
        duration_seconds=180.0,
    )

    assert plies_label._sum.get() == plies_before + 25
    assert duration_label._sum.get() == duration_before + 180.0


def test_metrics_payload_includes_redis_gauges():
    body, content_type = m.metrics_payload()
    assert b"shatra_redis_rooms_active" in body
    assert b"shatra_redis_games_active" in body
    assert b"shatra_game_duration_seconds_bucket" in body
