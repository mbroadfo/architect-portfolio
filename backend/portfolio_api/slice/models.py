"""Slice entities and request models (entities.md; BR2.1, BR2.2, BR3.4).

SliceProject is a thin subset of Project (U3); SlicePublishedVersion is a thin subset of
PublishedVersion (U9). Status is derived, never stored (ADR-003).
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

TITLE_MAX = 120
SUMMARY_MAX = 1200
SLUG_MAX = 60
SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
SLUG_REGEX = re.compile(SLUG_PATTERN)

Slug = Annotated[str, StringConstraints(pattern=SLUG_PATTERN, max_length=SLUG_MAX)]
Summary = Annotated[str, StringConstraints(max_length=SUMMARY_MAX)]


class SliceStatus(StrEnum):
    """Derived project status (BR3.4)."""

    DRAFT = "Draft"
    PUBLISHED = "Published"
    CHANGED = "Changes since last publish"


def _check_title(value: str) -> str:
    if not value.strip():
        raise ValueError("title must not be empty")
    if len(value) > TITLE_MAX:
        raise ValueError(f"title must be at most {TITLE_MAX} characters")
    return value


class SliceProject(BaseModel):
    """The draft and its revision (stored)."""

    model_config = ConfigDict(frozen=True)

    project_id: str
    title: str
    summary: Summary = ""
    slug: Slug
    revision: int = Field(ge=1)
    updated_at: datetime
    current_version_id: str | None = None

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _check_title(value)


class SlicePublishedVersion(BaseModel):
    """A frozen, C2-valid projection of one project revision (stored)."""

    model_config = ConfigDict(frozen=True)

    version_id: str
    project_id: str
    source_revision: int = Field(ge=1)
    snapshot: dict[str, Any]
    published_at: datetime
    # Monotonically increasing across all Publishes, assigned inside the serialized Publish.
    # It orders versions published within the same second (published_at has 1 s precision).
    sequence: int = Field(default=0, ge=0)


def derive_status(project: SliceProject, published: SlicePublishedVersion | None) -> SliceStatus:
    """BR3.4: Draft without a published version; Published when the revisions match."""
    if published is None:
        return SliceStatus.DRAFT
    if published.source_revision == project.revision:
        return SliceStatus.PUBLISHED
    return SliceStatus.CHANGED


def propose_slug(title: str) -> str:
    """Propose a slug from a title: lowercase words joined by hyphens, at most 60 characters."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = slug[:SLUG_MAX].strip("-")
    return slug or "project"


def with_suffix(slug: str, number: int) -> str:
    """Return ``slug`` with a numeric suffix that keeps it within the length limit."""
    suffix = f"-{number}"
    return f"{slug[: SLUG_MAX - len(suffix)].rstrip('-')}{suffix}"


class CreateProjectRequest(BaseModel):
    """POST /slice/projects body (closed, BR2.2)."""

    model_config = ConfigDict(extra="forbid")

    title: str
    summary: Summary = ""

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _check_title(value)


class UpdateProjectRequest(BaseModel):
    """PATCH /slice/projects/{id} body (closed, BR2.2)."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    summary: Summary | None = None
    slug: Slug | None = None

    @field_validator("title")
    @classmethod
    def _title(cls, value: str | None) -> str | None:
        return None if value is None else _check_title(value)

    def changes(self) -> dict[str, str]:
        """Return only the fields the request sets."""
        return {key: value for key, value in self.model_dump().items() if value is not None}


class PublishRequest(BaseModel):
    """POST /slice/projects/{id}/publish body: the revision the owner reviewed (BR3.1)."""

    model_config = ConfigDict(extra="forbid")

    revision: int = Field(ge=1)


class ProjectView(BaseModel):
    """The project as the Studio sees it."""

    project_id: str = Field(serialization_alias="projectId")
    title: str
    summary: str
    slug: str
    revision: int
    status: SliceStatus
    updated_at: datetime = Field(serialization_alias="updatedAt")
    published_revision: int | None = Field(serialization_alias="publishedRevision")

    @classmethod
    def build(cls, project: SliceProject, published: SlicePublishedVersion | None) -> ProjectView:
        """Combine the stored project with its current published version."""
        return cls(
            project_id=project.project_id,
            title=project.title,
            summary=project.summary,
            slug=project.slug,
            revision=project.revision,
            status=derive_status(project, published),
            updated_at=project.updated_at,
            published_revision=published.source_revision if published else None,
        )
