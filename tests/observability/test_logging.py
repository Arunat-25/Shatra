"""Tests for centralized logging setup."""

import json
import logging

from backend.observability.logging import (
    bind_request_id,
    log_extra,
    reset_request_id,
    setup_logging,
)


def test_setup_logging_text_includes_request_id_in_format():
    setup_logging(level="DEBUG", log_format="text")
    root = logging.getLogger()
    assert root.handlers
    formatter = root.handlers[0].formatter
    assert "request_id" in formatter._fmt


def test_setup_logging_json_emits_parseable_json(capsys):
    setup_logging(level="INFO", log_format="json")
    logger = logging.getLogger("test.observability")
    logger.info("hello json")
    captured = capsys.readouterr()
    line = captured.out.strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["message"] == "hello json"
    assert payload["service"] == "shatra"


def test_log_extra_includes_bound_request_id():
    token = bind_request_id("req-abc")
    try:
        extra = log_extra(room_id="room1")
        assert extra["request_id"] == "req-abc"
        assert extra["room_id"] == "room1"
    finally:
        reset_request_id(token)
