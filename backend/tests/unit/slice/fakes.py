"""LOCAL-ONLY FAKES for the slice unit tests. Never used by production code.

- InMemoryProjectRepository / InMemoryPublicationRepository implement the repository
  protocols with the same compare-and-set semantics as the MongoDB versions, plus failure
  injection.
- FixedRenderer stands in for the renderer subprocess with a fixed-shape RenderOutput.
- PointerFileOps stands in for symbolic links only on hosts that cannot create them (Windows
  without Developer Mode); everywhere else the tests use the real SymlinkOps.
"""

from __future__ import annotations

import copy
import os
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from portfolio_api.slice.errors import (
    NotFoundError,
    SlugTakenError,
    StaleRevisionError,
    ValidationFailedError,
)
from portfolio_api.slice.models import SliceProject, SlicePublishedVersion
from portfolio_api.slice.renderer import (
    RenderedPage,
    RenderFailedError,
    RenderOutput,
    RequiredImage,
)

STATIC_ASSET = "/assets/site.{hash}.css"


class InMemoryProjectRepository:
    """LOCAL-ONLY FAKE: ProjectRepository in memory."""

    def __init__(self) -> None:
        self.items: dict[str, SliceProject] = {}

    def create(self, project: SliceProject) -> None:
        if self.slug_exists(project.slug):
            raise SlugTakenError(f"the slug '{project.slug}' is already in use")
        self.items[project.project_id] = project

    def get(self, project_id: str) -> SliceProject | None:
        return self.items.get(project_id)

    def list(self) -> list[SliceProject]:
        return sorted(self.items.values(), key=lambda p: p.updated_at, reverse=True)

    def slug_exists(self, slug: str) -> bool:
        return any(p.slug == slug for p in self.items.values())

    def save(
        self, project_id: str, base_revision: int, changes: Mapping[str, str], updated_at: datetime
    ) -> SliceProject:
        current = self.items.get(project_id)
        if current is None:
            raise NotFoundError(f"project {project_id} not found")
        if current.revision != base_revision:
            raise StaleRevisionError(f"project is at revision {current.revision}")
        if "slug" in changes and current.current_version_id is not None:
            raise ValidationFailedError("the slug is fixed after the first publish")
        slug = changes.get("slug")
        if slug and any(p.slug == slug and p.project_id != project_id for p in self.items.values()):
            raise SlugTakenError(f"the slug '{slug}' is already in use")
        updated = current.model_copy(
            update={**changes, "revision": current.revision + 1, "updated_at": updated_at}
        )
        self.items[project_id] = updated
        return updated

    def set_current(self, project_id: str, version_id: str | None) -> None:
        self.items[project_id] = self.items[project_id].model_copy(
            update={"current_version_id": version_id}
        )


class InMemoryPublicationRepository:
    """LOCAL-ONLY FAKE: PublicationRepository in memory, with failure injection."""

    def __init__(self, projects: InMemoryProjectRepository) -> None:
        self.projects = projects
        self.versions: dict[str, SlicePublishedVersion] = {}
        self.fail_commit: Exception | None = None
        self.fail_compensate: Exception | None = None
        self.sequence = 0

    def next_sequence(self) -> int:
        self.sequence += 1
        return self.sequence

    def commit_publish(
        self,
        project_id: str,
        revision: int,
        previous_version_id: str | None,
        version: SlicePublishedVersion,
    ) -> None:
        if self.fail_commit is not None:
            raise self.fail_commit
        project = self.projects.get(project_id)
        if (
            project is None
            or project.revision != revision
            or project.current_version_id != previous_version_id
        ):
            raise StaleRevisionError("the project is no longer at the reviewed revision")
        self.versions[version.version_id] = version
        self.projects.set_current(project_id, version.version_id)

    def compensate(self, project_id: str, version_id: str, previous_version_id: str | None) -> bool:
        if self.fail_compensate is not None:
            raise self.fail_compensate
        project = self.projects.get(project_id)
        if project is None or project.current_version_id != version_id:
            return False
        self.projects.set_current(project_id, previous_version_id)
        self.versions.pop(version_id, None)
        return True

    def get_version(self, version_id: str) -> SlicePublishedVersion | None:
        return self.versions.get(version_id)

    def current_versions(self) -> list[SlicePublishedVersion]:
        ids = {p.current_version_id for p in self.projects.items.values() if p.current_version_id}
        return [v for k, v in self.versions.items() if k in ids]


class FixedRenderer:
    """LOCAL-ONLY FAKE: the renderer subprocess, returning a fixed-shape RenderOutput.

    Each page's HTML names the exhibit titles it was given, so tests can tell releases apart.
    """

    def __init__(self, asset_hash: str) -> None:
        self.asset_hash = asset_hash
        self.calls: list[tuple[dict[str, Any], str]] = []
        self.fail: Exception | None = None

    def render(self, snapshot: dict[str, Any], mode: str) -> RenderOutput:
        self.calls.append((copy.deepcopy(snapshot), mode))
        if self.fail is not None:
            raise self.fail
        titles = " | ".join(e["title"] for e in snapshot["exhibits"]) or "empty"
        pages = [RenderedPage("/", 200, f"<html>home {titles}</html>")]
        pages += [
            RenderedPage(f"/work/{e['slug']}", 200, f"<html>{e['title']}</html>")
            for e in snapshot["exhibits"]
        ]
        pages.append(RenderedPage("/404.html", 404, "<html>not found</html>"))
        images = tuple(
            RequiredImage(e["leadImage"]["assetRef"], "w480", fmt)
            for e in snapshot["exhibits"][:1]
            for fmt in ("webp", "jpg")
        )
        return RenderOutput(tuple(pages), images, (STATIC_ASSET.format(hash=self.asset_hash),))


class PointerFileOps:
    """LOCAL-ONLY FAKE: a pointer file in place of a symbolic link, for hosts without symlinks."""

    def replace_link(self, link: Path, target: str, temporary: Path) -> None:
        temporary.write_text(target, encoding="utf-8")
        os.replace(temporary, link)

    def read_link(self, link: Path) -> str | None:
        return link.read_text(encoding="utf-8") if link.is_file() else None


__all__ = [
    "FixedRenderer",
    "InMemoryProjectRepository",
    "InMemoryPublicationRepository",
    "PointerFileOps",
    "RenderFailedError",
]
