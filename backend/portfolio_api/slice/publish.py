"""Publish (W4; BR3.1, BR3.2, BR3.3, BR3.4; REL-0.1).

Sequence, serialized by one lock in the single API process:

1. reconcile the ``public`` link with the database;
2. refuse unless the reviewed revision is still the project's current revision;
3. take the timestamp T (the commit time recorded with the version);
4. build the whole-site C2 snapshot from the SliceProject mapping and validate it;
5. render it with the shared renderer, in public mode;
6. write ``releases/<versionId>/`` (a render or write failure writes nothing);
7. in one transaction, compare-and-set the project's revision and previous current version,
   and insert the SlicePublishedVersion (a mismatch is 409 STALE_REVISION; the release is
   removed);
8. swap the relative ``public`` link;
9. if the swap fails, conditionally compensate (restore the previous current version and
   remove the new one); if compensation itself fails, it is logged and reconciliation repairs
   the state on the next Publish or start-up.

The database is the source of truth: the site shows the most recently published current
version among all projects, which holds every published exhibit.
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from portfolio_api.slice.errors import NotFoundError, PublishFailedError, StaleRevisionError
from portfolio_api.slice.models import SliceProject, SlicePublishedVersion
from portfolio_api.slice.renderer import Renderer
from portfolio_api.slice.repositories import ProjectRepository, PublicationRepository
from portfolio_api.slice.site_store import EMPTY_RELEASE, SiteStore
from portfolio_api.slice.snapshot import (
    FixtureImage,
    SiteConfig,
    build_exhibit,
    build_site_snapshot,
)

KEEP_RELEASES = 3

logger = logging.getLogger("portfolio_api.slice.publish")


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_version_id() -> str:
    return uuid.uuid4().hex


@dataclass(frozen=True)
class PublishResult:
    version_id: str
    source_revision: int
    published_at: datetime


class PublishService:
    """Serialized, conditional Publish with compensation and reconciliation."""

    def __init__(
        self,
        projects: ProjectRepository,
        publications: PublicationRepository,
        renderer: Renderer,
        site: SiteStore,
        site_config: SiteConfig,
        fixture: FixtureImage,
        clock: Callable[[], datetime] = utc_now,
        new_id: Callable[[], str] = new_version_id,
    ) -> None:
        self._projects = projects
        self._publications = publications
        self._renderer = renderer
        self._site = site
        self._site_config = site_config
        self._fixture = fixture
        self._clock = clock
        self._new_id = new_id
        self._lock = threading.Lock()

    def site_version(self) -> SlicePublishedVersion | None:
        """The version the public site should show: the newest current version.

        Ordered by the publish sequence, then by time, so two Publishes in the same second
        never tie (R-09).
        """
        versions = self._publications.current_versions()
        return max(versions, key=lambda v: (v.sequence, v.published_at)) if versions else None

    def reconcile(self) -> str:
        """Point ``public`` at the database's site version, re-rendering it if missing."""
        with self._lock:
            return self._reconcile()

    def _reconcile(self) -> str:
        self._site.ensure_initial()
        current = self.site_version()
        target = current.version_id if current else EMPTY_RELEASE
        if self._site.current_release() == target and self._site.has_release(target):
            return target
        if current is not None and not self._site.has_release(target):
            self._site.write_release(target, self._renderer.render(current.snapshot, "public"))
        self._site.swap_public(target)
        logger.warning("reconciled the public folder", extra={"fields": {"release": target}})
        return target

    def _other_exhibits(self, project_id: str) -> list[dict[str, Any]]:
        exhibits: list[dict[str, Any]] = []
        for version in self._publications.current_versions():
            if version.project_id == project_id:
                continue
            owner = self._projects.get(version.project_id)
            exhibits.extend(
                e
                for e in version.snapshot.get("exhibits", [])
                if owner and e.get("slug") == owner.slug
            )
        return exhibits

    def _build_snapshot(self, project: SliceProject, published_at: datetime) -> dict[str, Any]:
        previous = self.site_version()
        generation = int(previous.snapshot.get("generation", 0)) + 1 if previous else 1
        exhibits = [
            *self._other_exhibits(project.project_id),
            build_exhibit(project, published_at, self._fixture),
        ]
        return build_site_snapshot(exhibits, self._site_config, generation)

    def publish(self, project_id: str, reviewed_revision: int) -> PublishResult:
        """Publish ``reviewed_revision`` of the project, or refuse and change nothing."""
        with self._lock:
            self._reconcile()
            project = self._projects.get(project_id)
            if project is None:
                raise NotFoundError(f"project {project_id} not found")
            if project.revision != reviewed_revision:
                raise StaleRevisionError(
                    f"revision {reviewed_revision} is not current "
                    f"(the project is at {project.revision})"
                )
            published_at = self._clock().astimezone(UTC).replace(microsecond=0)
            version_id = self._new_id()
            snapshot = self._build_snapshot(project, published_at)
            self._site.write_release(version_id, self._renderer.render(snapshot, "public"))
            version = SlicePublishedVersion(
                version_id=version_id,
                project_id=project_id,
                source_revision=reviewed_revision,
                snapshot=snapshot,
                published_at=published_at,
                sequence=self._publications.next_sequence(),
            )
            self._commit(project, version)
            self._swap_or_compensate(project, version)
            self._site.prune(KEEP_RELEASES, protect={version_id})
            logger.info(
                "published",
                extra={
                    "fields": {
                        "project_id": project_id,
                        "version_id": version_id,
                        "revision": reviewed_revision,
                    }
                },
            )
            return PublishResult(version_id, reviewed_revision, published_at)

    def _commit(self, project: SliceProject, version: SlicePublishedVersion) -> None:
        try:
            self._publications.commit_publish(
                project.project_id, version.source_revision, project.current_version_id, version
            )
        except Exception:
            self._site.delete_release(version.version_id)
            raise

    def _swap_or_compensate(self, project: SliceProject, version: SlicePublishedVersion) -> None:
        stored = self._projects.get(project.project_id)
        try:
            if stored is None or stored.current_version_id != version.version_id:
                raise PublishFailedError("the project changed during Publish")
            self._site.swap_public(version.version_id)
        except Exception as error:
            self._compensate(project, version)
            raise PublishFailedError(
                "Publish failed while switching the public folder; the previous version is kept"
            ) from error

    def _compensate(self, project: SliceProject, version: SlicePublishedVersion) -> None:
        try:
            restored = self._publications.compensate(
                project.project_id, version.version_id, project.current_version_id
            )
        except Exception:
            logger.exception(
                "compensation failed; reconciliation will repair the public folder",
                extra={"fields": {"version_id": version.version_id}},
            )
            return
        if restored:
            self._site.delete_release(version.version_id)
