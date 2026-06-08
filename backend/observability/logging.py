"""Centralized logging setup with optional JSON output."""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

from pythonjsonlogger import json as json_logger

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "-"
        return True


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.request_id = getattr(record, "request_id", request_id_ctx.get() or "-")
        return super().format(record)


def setup_logging(*, level: str, log_format: str) -> None:
    """Configure root logger once at application startup."""
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestContextFilter())

    if log_format == "json":
        formatter = json_logger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
            static_fields={"service": "shatra"},
        )
    else:
        formatter = TextFormatter(
            "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def log_extra(**fields: Any) -> dict[str, Any]:
    """Build structured `extra` dict for logger calls."""
    extra = dict(fields)
    rid = request_id_ctx.get()
    if rid:
        extra.setdefault("request_id", rid)
    return extra


def bind_request_id(request_id: str):
    return request_id_ctx.set(request_id)


def reset_request_id(token) -> None:
    request_id_ctx.reset(token)
