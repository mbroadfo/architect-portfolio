"""Domain errors, each mapped to a C1 ``Error`` code and HTTP status."""

from __future__ import annotations


class SliceError(Exception):
    """Base class: an error the API reports with a closed C1 error code."""

    status_code = 500
    code = "INTERNAL"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(SliceError):
    status_code = 404
    code = "NOT_FOUND"


class ValidationFailedError(SliceError):
    status_code = 422
    code = "VALIDATION_FAILED"


class RevisionRequiredError(SliceError):
    status_code = 428
    code = "REVISION_REQUIRED"


class StaleRevisionError(SliceError):
    """BR2.1 / BR3.1: the request was based on a revision that is no longer current."""

    status_code = 409
    code = "STALE_REVISION"


class SlugTakenError(SliceError):
    """BR2.2: another project already uses the slug."""

    status_code = 409
    code = "SLUG_TAKEN"


class PublishFailedError(SliceError):
    """Publish failed partway; the previous output and current version are kept (BR3.3)."""

    status_code = 500
    code = "INTERNAL"
