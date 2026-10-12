"""Request ids and JSON request logs with redaction (NFR11.1).

Every request is logged once as a JSON line with ``request_id``, ``method``, ``route``,
``status`` and ``duration_ms``. Tokens, keys and personal data are never logged: a redaction
step removes bearer tokens, JWT-like values and any field named like a credential.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response

LOGGER_NAME = "portfolio_api.slice"
REQUEST_ID_HEADER = "X-Request-Id"
VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
REDACTED = "[REDACTED]"
SENSITIVE_KEY = re.compile(r"authorization|token|secret|password|cookie|key", re.IGNORECASE)
SENSITIVE_VALUE = (
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"eyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]*"),
)

request_logger = logging.getLogger(f"{LOGGER_NAME}.requests")


def redact(value: Any) -> Any:
    """Return ``value`` with credentials removed, recursively."""
    if isinstance(value, str):
        for pattern in SENSITIVE_VALUE:
            value = pattern.sub(REDACTED, value)
        return value
    if isinstance(value, dict):
        return {
            key: REDACTED if SENSITIVE_KEY.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    """One JSON object per line, redacted."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            entry.update(fields)
        if record.exc_info and record.exc_info[0] is not None:
            entry["error"] = record.exc_info[0].__name__
        return json.dumps(redact(entry), default=str, sort_keys=True)


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Attach the JSON formatter to the slice logger once."""
    logger = logging.getLogger(LOGGER_NAME)
    if not any(getattr(h, "_slice_json", False) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        handler._slice_json = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def request_id_for(request: Request) -> str:
    """The request id the middleware assigned, or a fresh one."""
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else uuid.uuid4().hex


async def request_logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Assign or echo the request id, then log the request as one JSON line."""
    incoming = request.headers.get(REQUEST_ID_HEADER, "")
    request_id = incoming if VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
    request.state.request_id = request_id
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
    finally:
        route = request.scope.get("route")
        request_logger.info(
            "request",
            extra={
                "fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "route": getattr(route, "path", "unmatched"),
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            },
        )
