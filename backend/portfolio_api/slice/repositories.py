"""Repository interfaces for the slice (BR2.1, BR2.2, BR3.1).

The MongoDB implementations live in ``mongo.py``. Unit tests use in-memory doubles that
implement these same protocols.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from portfolio_api.slice.models import SliceProject, SlicePublishedVersion


class ProjectRepository(Protocol):
    """Stores SliceProject drafts."""

    def create(self, project: SliceProject) -> None:
        """Insert a new project; raise SlugTakenError when the slug is in use."""
        ...

    def get(self, project_id: str) -> SliceProject | None:
        """Return the project, or None."""
        ...

    def list(self) -> list[SliceProject]:
        """Return every project, most recently updated first."""
        ...

    def slug_exists(self, slug: str) -> bool:
        """Return True when any project uses ``slug``."""
        ...

    def save(
        self,
        project_id: str,
        base_revision: int,
        changes: Mapping[str, str],
        updated_at: datetime,
    ) -> SliceProject:
        """Compare-and-set save (BR2.1): apply ``changes`` only at ``base_revision``.

        Raises NotFoundError, StaleRevisionError, SlugTakenError, or ValidationFailedError when
        the slug changes after the first publish.
        """
        ...


class PublicationRepository(Protocol):
    """Stores SlicePublishedVersions and the project's current version (BR3.1)."""

    def commit_publish(
        self,
        project_id: str,
        revision: int,
        previous_version_id: str | None,
        version: SlicePublishedVersion,
    ) -> None:
        """In one transaction, compare-and-set the project's revision and current version,
        then insert ``version``. Raise StaleRevisionError and write nothing on a mismatch."""
        ...

    def compensate(self, project_id: str, version_id: str, previous_version_id: str | None) -> bool:
        """Conditionally restore ``previous_version_id`` and remove ``version_id``.

        Return True when the restore applied, False when the project had moved on.
        """
        ...

    def next_sequence(self) -> int:
        """Return the next publish sequence number, strictly greater than every earlier one."""
        ...

    def get_version(self, version_id: str) -> SlicePublishedVersion | None:
        """Return one published version, or None."""
        ...

    def current_versions(self) -> list[SlicePublishedVersion]:
        """Return every project's current published version."""
        ...
