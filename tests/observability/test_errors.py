"""Tests for Sentry error reporting wrapper."""

from unittest.mock import patch

from backend.config import Settings
from backend.observability.errors import capture_exception, init_sentry


def test_init_sentry_noop_without_dsn():
    settings = Settings(sentry_dsn="")
    with patch("backend.observability.errors.sentry_sdk.init") as init_mock:
        init_sentry(settings)
    init_mock.assert_not_called()


def test_init_sentry_with_dsn():
    settings = Settings(
        sentry_dsn="https://example@sentry.io/1",
        app_env="test",
        app_version="1.2.3",
        sentry_traces_sample_rate=0.2,
    )
    with patch("backend.observability.errors.sentry_sdk.init") as init_mock:
        init_sentry(settings)
    init_mock.assert_called_once()
    kwargs = init_mock.call_args.kwargs
    assert kwargs["dsn"] == settings.sentry_dsn
    assert kwargs["environment"] == "test"
    assert kwargs["release"] == "1.2.3"
    assert kwargs["traces_sample_rate"] == 0.2
    assert kwargs["integrations"]


def test_capture_exception_delegates():
    with patch("backend.observability.errors.sentry_sdk.capture_exception") as capture_mock:
        capture_exception()
    capture_mock.assert_called_once()
