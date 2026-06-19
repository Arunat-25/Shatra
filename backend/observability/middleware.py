"""HTTP observability middleware."""

from __future__ import annotations

import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.observability.logging import bind_request_id, log_extra, reset_request_id
from backend.observability.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
)

logger = logging.getLogger(__name__)

_SKIP_PREFIXES = ("/assets/", "/sounds/", "/images/")
_SKIP_EXACT = frozenset({"/metrics", "/health"})

_PATH_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^/rooms/[^/]+/join$"), "/rooms/{room_id}/join"),
    (re.compile(r"^/rooms/[^/]+/status$"), "/rooms/{room_id}/status"),
    (re.compile(r"^/ws/v2/[^/]+/?$"), "/ws/v2/{room_id}/"),
    (re.compile(r"^/api/admin/bug-reports/[^/]+$"), "/api/admin/bug-reports/{id}"),
    (re.compile(r"^/api/admin/stats/[^/]+/series$"), "/api/admin/stats/{name}/series"),
    (re.compile(r"^/api/admin/stats/[^/]+$"), "/api/admin/stats/{name}"),
]


def normalize_path(path: str) -> str:
    for pattern, template in _PATH_PATTERNS:
        if pattern.match(path):
            return template
    return path


def _should_skip(path: str) -> bool:
    if path in _SKIP_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _SKIP_PREFIXES)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if _should_skip(path):
            return await call_next(request)

        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = bind_request_id(request_id)
        method = request.method
        metric_path = normalize_path(path)
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration = time.perf_counter() - start
            HTTP_REQUESTS_TOTAL.labels(method=method, path=metric_path, status="500").inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=metric_path).observe(duration)
            logger.exception(
                "HTTP request failed",
                extra=log_extra(
                    method=method,
                    path=path,
                    metric_path=metric_path,
                    duration_ms=round(duration * 1000, 2),
                    request_id=request_id,
                ),
            )
            raise
        finally:
            reset_request_id(token)

        duration = time.perf_counter() - start
        status = str(response.status_code)
        HTTP_REQUESTS_TOTAL.labels(method=method, path=metric_path, status=status).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=metric_path).observe(duration)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "HTTP %s %s -> %s (%.0fms)",
            method,
            path,
            status,
            duration * 1000,
            extra=log_extra(
                method=method,
                path=path,
                metric_path=metric_path,
                status=int(response.status_code),
                duration_ms=round(duration * 1000, 2),
                request_id=request_id,
            ),
        )
        return response
