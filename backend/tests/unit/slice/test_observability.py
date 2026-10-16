"""Request log format and redaction tests (Step 18; NFR11.1)."""

from __future__ import annotations

import io
import json
import logging

from portfolio_api.slice.observability import (
    REDACTED,
    JsonFormatter,
    configure_logging,
    redact,
)

from tests.unit.slice import tokens
from tests.unit.slice.conftest import Harness


def _capture(logger_name: str) -> tuple[logging.Logger, io.StringIO, logging.Handler]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger(logger_name)
    logger.addHandler(handler)
    return logger, stream, handler


def test_nfr11_1_request_log_line_has_the_required_fields(harness: Harness) -> None:
    logger, stream, handler = _capture("portfolio_api.slice.requests")
    try:
        harness.client.get(
            "/slice/projects/missing", headers=harness.headers(**{"X-Request-Id": "rid-1"})
        )
    finally:
        logger.removeHandler(handler)
    entry = json.loads(stream.getvalue().strip().splitlines()[-1])
    assert entry["request_id"] == "rid-1"
    assert entry["method"] == "GET"
    assert entry["route"] == "/slice/projects/{project_id}"
    assert entry["status"] == 404
    assert isinstance(entry["duration_ms"], float)


def test_nfr11_1_tokens_never_reach_the_log(harness: Harness) -> None:
    logger, stream, handler = _capture("portfolio_api.slice.requests")
    token = harness.token()
    try:
        harness.client.get("/slice/projects", headers={"Authorization": f"Bearer {token}"})
        harness.client.get("/slice/projects", headers={"Authorization": "Bearer not-a-valid-token"})
    finally:
        logger.removeHandler(handler)
    output = stream.getvalue()
    assert token not in output
    assert "not-a-valid-token" not in output


def test_redaction_of_values_and_credential_fields() -> None:
    token = tokens.sign(tokens.ec_key())
    entry = {
        "message": f"got Authorization: Bearer {token}",
        "raw": f"jwt {token} trailing",
        "headers": {"Authorization": "Bearer abc", "Accept": "application/json"},
        "items": ["ok", f"Bearer {token}"],
        "count": 3,
        "access_token": "plain-value",
    }
    cleaned = redact(entry)
    serialized = json.dumps(cleaned)
    assert token not in serialized
    assert cleaned["headers"] == {"Authorization": REDACTED, "Accept": "application/json"}
    assert cleaned["access_token"] == REDACTED
    assert cleaned["count"] == 3
    assert cleaned["items"][0] == "ok"


def test_formatter_redacts_the_message_and_names_the_error() -> None:
    record = logging.LogRecord(
        "x", logging.ERROR, __file__, 1, "Bearer %s", ("secret.jwt.value",), None
    )
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record.exc_info = sys.exc_info()
    record.fields = {"token": "abc"}
    entry = json.loads(JsonFormatter().format(record))
    assert entry["message"] == REDACTED
    assert entry["token"] == REDACTED
    assert entry["error"] == "ValueError"
    assert "boom" not in json.dumps(entry)


def test_configure_logging_is_idempotent() -> None:
    logger = configure_logging()
    count = len(logger.handlers)
    configure_logging()
    assert len(logger.handlers) == count
    assert logger.propagate is False
