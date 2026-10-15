"""Studio errors, each with an HTTP status and a stable code for the Studio page."""

from __future__ import annotations


class StudioError(Exception):
    """Base class: an error the Studio reports with a stable code."""

    status_code = 500
    code = "INTERNAL"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(StudioError):
    status_code = 404
    code = "NOT_FOUND"


class ValidationFailedError(StudioError):
    status_code = 422
    code = "VALIDATION_FAILED"


class ConflictError(StudioError):
    """The draft changed since the caller read it (FR3.4, ADR-012)."""

    status_code = 409
    code = "STALE_REVISION"


class SlugTakenError(StudioError):
    status_code = 409
    code = "SLUG_TAKEN"


class PublishBlockedError(StudioError):
    """Publish is blocked by FR7.3 (title, lead image, alt text, rights review)."""

    status_code = 422
    code = "PUBLISH_BLOCKED"


class InvalidTransitionError(StudioError):
    """A status transition FR3.2 does not allow."""

    status_code = 409
    code = "INVALID_TRANSITION"


class ImageRejectedError(StudioError):
    """An upload failed content validation (FR4.2)."""

    status_code = 422
    code = "IMAGE_REJECTED"


class UploadTooLargeError(StudioError):
    status_code = 413
    code = "TOO_LARGE"


class ContentLocationError(StudioError):
    """The content directory is not an allowed private location (ADR-013)."""

    code = "CONTENT_LOCATION"


class GitError(StudioError):
    """A Git command in the content repository failed."""

    code = "GIT_FAILED"


class BuildFailedError(StudioError):
    """The site build failed; the previous output is left in place."""

    code = "BUILD_FAILED"


class LockedError(StudioError):
    """Another Studio process holds the content repository."""

    status_code = 423
    code = "LOCKED"
