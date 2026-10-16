"""Build C2 PublicSiteSnapshot 1.0 documents from slice projects (functional-spec mapping).

A Publish builds the snapshot like this:

- ``title``, ``summary`` and ``slug`` come from the project;
- ``leadImage`` holds the bundled fixture image, with its real width, height and alt text;
- ``sections`` is ``{}``; ``images``, ``attachments``, ``links``, ``badges`` and
  ``publicRepositories`` are ``[]``;
- ``featured`` is false, so ``featuredOrder`` is ``[]``; no ``primaryCategory``, so
  ``categories`` is ``[]``;
- ``publishedAt`` is the commit time T; ``site`` comes from local configuration.

The snapshot is checked against a closed model of the C2 allow-list here (BR3.2); the
renderer validates it again with the full JSON Schema (Ajv) before rendering.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from portfolio_api.slice.errors import ValidationFailedError
from portfolio_api.slice.models import SLUG_PATTERN, SliceProject

FIXTURE_MANIFEST = "fixture.json"
ASSET_REF_PATTERN = r"^ast_[A-Za-z0-9]{16,32}$"
GITHUB_PROFILE_PATTERN = r"^https://github\.com/[A-Za-z0-9-]+$"


@dataclass(frozen=True)
class FixtureImage:
    """The one bundled, metadata-free fixture image (C8 derivatives on disk)."""

    asset_ref: str
    alt_text: str
    width: int
    height: int
    directory: Path

    @classmethod
    def load(cls, fixture_dir: Path) -> FixtureImage:
        """Read ``fixture.json`` from the fixture directory."""
        manifest = json.loads((fixture_dir / FIXTURE_MANIFEST).read_text(encoding="utf-8"))
        return cls(
            asset_ref=str(manifest["assetRef"]),
            alt_text=str(manifest["altText"]),
            width=int(manifest["width"]),
            height=int(manifest["height"]),
            directory=fixture_dir,
        )

    def as_c2(self) -> dict[str, Any]:
        return {
            "assetRef": self.asset_ref,
            "altText": self.alt_text,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class SiteConfig:
    """C2 ``site`` from local configuration (placeholder owner name and GitHub URL)."""

    owner_name: str
    github_profile_url: str

    def as_c2(self) -> dict[str, Any]:
        return {
            "ownerName": self.owner_name,
            "githubProfileUrl": self.github_profile_url,
            "contactEmail": None,
        }


def format_timestamp(moment: datetime) -> str:
    """RFC 3339 UTC with second precision, as C2 ``publishedAt``."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_exhibit(
    project: SliceProject, published_at: datetime, fixture: FixtureImage
) -> dict[str, Any]:
    """Map one SliceProject to a C2 Exhibit."""
    return {
        "slug": project.slug,
        "title": project.title,
        "summary": project.summary,
        "sections": {},
        "leadImage": fixture.as_c2(),
        "images": [],
        "attachments": [],
        "links": [],
        "badges": [],
        "publicRepositories": [],
        "featured": False,
        "publishedAt": format_timestamp(published_at),
    }


def build_site_snapshot(
    exhibits: list[dict[str, Any]], site: SiteConfig, generation: int
) -> dict[str, Any]:
    """Assemble the whole-site snapshot, newest exhibit first, then validate it (BR3.2)."""
    ordered = sorted(exhibits, key=lambda e: (e["publishedAt"], e["slug"]), reverse=True)
    snapshot = {
        "schemaVersion": "1.0",
        "generation": generation,
        "site": site.as_c2(),
        "exhibits": ordered,
        "featuredOrder": [],
        "categories": [],
    }
    validate_snapshot(snapshot)
    return snapshot


# --- the C2 allow-list as closed models (BR3.2) ------------------------------------------

_Closed = ConfigDict(extra="forbid", strict=True)
_Slug = Annotated[str, StringConstraints(pattern=SLUG_PATTERN, max_length=60)]
_AssetRef = Annotated[str, StringConstraints(pattern=ASSET_REF_PATTERN)]
_Timestamp = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")]


class _Image(BaseModel):
    model_config = _Closed
    assetRef: _AssetRef  # noqa: N815 - C2 field name
    altText: Annotated[str, StringConstraints(min_length=1, max_length=300)]  # noqa: N815
    caption: Annotated[str, StringConstraints(max_length=300)] | None = None
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class _Sections(BaseModel):
    model_config = _Closed


class _Exhibit(BaseModel):
    model_config = _Closed
    slug: _Slug
    title: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    summary: Annotated[str, StringConstraints(max_length=1200)]
    sections: _Sections
    leadImage: _Image  # noqa: N815
    images: list[_Image] = Field(max_length=40)
    attachments: list[Any] = Field(max_length=0)
    links: list[Any] = Field(max_length=0)
    badges: list[Any] = Field(max_length=0)
    publicRepositories: list[Any] = Field(max_length=0)  # noqa: N815
    featured: bool
    publishedAt: _Timestamp  # noqa: N815


class _Site(BaseModel):
    model_config = _Closed
    ownerName: Annotated[str, StringConstraints(max_length=120)]  # noqa: N815
    githubProfileUrl: Annotated[str, StringConstraints(pattern=GITHUB_PROFILE_PATTERN)]  # noqa: N815
    contactEmail: None = None  # noqa: N815


class _Snapshot(BaseModel):
    model_config = _Closed
    schemaVersion: Literal["1.0"]  # noqa: N815
    generation: int = Field(ge=0)
    site: _Site
    exhibits: list[_Exhibit] = Field(max_length=200)
    featuredOrder: list[_Slug] = Field(max_length=0)  # noqa: N815
    categories: list[Any] = Field(max_length=0)


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    """Refuse a snapshot outside the slice's C2 subset (BR3.2)."""
    try:
        _Snapshot.model_validate(snapshot)
    except ValidationError as error:
        raise ValidationFailedError(f"the snapshot is not valid against C2: {error}") from error
