"""Create, save and preview (W1, W2, W3; BR2.1, BR2.2, BR3.4, BR4.1)."""

from __future__ import annotations

import base64
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from portfolio_api.slice.errors import NotFoundError, SlugTakenError, ValidationFailedError
from portfolio_api.slice.models import (
    CreateProjectRequest,
    ProjectView,
    SliceProject,
    UpdateProjectRequest,
    propose_slug,
    with_suffix,
)
from portfolio_api.slice.publish import utc_now
from portfolio_api.slice.repositories import ProjectRepository, PublicationRepository
from portfolio_api.slice.snapshot import (
    FixtureImage,
    SiteConfig,
    build_exhibit,
    build_site_snapshot,
)

MAX_SLUG_ATTEMPTS = 20
MEDIA_TYPES = {"jpg": "image/jpeg", "webp": "image/webp"}


def new_project_id() -> str:
    return uuid.uuid4().hex


class ProjectService:
    """W1 create and W2 save, with derived status (BR3.4)."""

    def __init__(
        self,
        projects: ProjectRepository,
        publications: PublicationRepository,
        clock: Callable[[], datetime] = utc_now,
        new_id: Callable[[], str] = new_project_id,
    ) -> None:
        self._projects = projects
        self._publications = publications
        self._clock = clock
        self._new_id = new_id

    def view(self, project: SliceProject) -> ProjectView:
        published = (
            self._publications.get_version(project.current_version_id)
            if project.current_version_id
            else None
        )
        return ProjectView.build(project, published)

    def get(self, project_id: str) -> SliceProject:
        project = self._projects.get(project_id)
        if project is None:
            raise NotFoundError(f"project {project_id} not found")
        return project

    def list(self) -> list[ProjectView]:
        return [self.view(project) for project in self._projects.list()]

    def _free_slug(self, title: str) -> str:
        base = propose_slug(title)
        if not self._projects.slug_exists(base):
            return base
        for number in range(2, MAX_SLUG_ATTEMPTS + 2):
            candidate = with_suffix(base, number)
            if not self._projects.slug_exists(candidate):
                return candidate
        raise SlugTakenError(f"no free slug near '{base}'")

    def create(self, request: CreateProjectRequest) -> SliceProject:
        """W1: store the project at revision 1 with a proposed, unique slug (Draft)."""
        project = SliceProject(
            project_id=self._new_id(),
            title=request.title,
            summary=request.summary,
            slug=self._free_slug(request.title),
            revision=1,
            updated_at=self._clock(),
        )
        self._projects.create(project)
        return project

    def save(
        self, project_id: str, base_revision: int, request: UpdateProjectRequest
    ) -> SliceProject:
        """W2: compare-and-set save at ``base_revision`` (BR2.1); revision becomes N+1."""
        changes = request.changes()
        if not changes:
            raise ValidationFailedError("nothing to save: set title, summary or slug")
        return self._projects.save(project_id, base_revision, changes, self._clock())


@dataclass(frozen=True)
class PreviewCandidate:
    revision: int
    snapshot: dict[str, Any]
    image_addresses: dict[str, str]


class PreviewService:
    """W3: the candidate snapshot of the current revision; nothing is written (BR4.1)."""

    def __init__(
        self,
        projects: ProjectService,
        site_config: SiteConfig,
        fixture: FixtureImage,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._projects = projects
        self._site_config = site_config
        self._fixture = fixture
        self._clock = clock

    def _image_addresses(self) -> dict[str, str]:
        """Data addresses for the fixture derivatives, so the sandboxed frame can show them."""
        addresses: dict[str, str] = {}
        folder = self._fixture.directory / self._fixture.asset_ref
        for path in sorted(folder.glob("*.*")):
            image_format = path.suffix.lstrip(".")
            if image_format in MEDIA_TYPES:
                encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                key = f"{self._fixture.asset_ref}/{path.name}"
                addresses[key] = f"data:{MEDIA_TYPES[image_format]};base64,{encoded}"
        return addresses

    def candidate(self, project_id: str) -> PreviewCandidate:
        project = self._projects.get(project_id)
        exhibit = build_exhibit(project, self._clock(), self._fixture)
        snapshot = build_site_snapshot([exhibit], self._site_config, generation=0)
        return PreviewCandidate(project.revision, snapshot, self._image_addresses())
