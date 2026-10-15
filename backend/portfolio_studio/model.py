"""The content model stored in the private repository.

``projects/<id>/project.json`` holds the draft (``Draft``). ``published/<id>.json`` holds the
frozen published version (``PublishedVersion``): exactly the C2 exhibit fields plus the
SHA-256 digests of the derivatives it uses, bound to the confirmed draft revision (ADR-002,
ADR-012). Status is derived, never stored (ADR-003).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
SLUG_PATTERN = ID_PATTERN
ASSET_REF_PATTERN = r"^ast_[A-Za-z0-9]{16,32}$"
ORIGINAL_FILE_PATTERN = r"^ast_[A-Za-z0-9]{16,32}\.(jpg|png|webp)$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"
GITHUB_REPOSITORY = re.compile(
    r"^https://github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9._-]+?)(\.git)?/?$"
)
REPOSITORY_HOST = re.compile(
    r"^https?://([A-Za-z0-9-]+\.)*(github\.com|githubusercontent\.com|gitlab\.com|bitbucket\.org)"
    r"(:[0-9]+)?(/|$)",
    re.IGNORECASE,
)
SECTION_KEYS: tuple[str, ...] = (
    "inspiration",
    "designChallenges",
    "architecturalDecisions",
    "implementation",
    "outcomes",
    "lessonsLearned",
)
# FR9.8: four fixed categories, each with a fixed address and position.
CATEGORIES: dict[str, tuple[str, int]] = {
    "games": ("Games & AI Arenas", 0),
    "astronomy": ("Astronomy & Exploration", 1),
    "woodworking": ("Woodworking", 2),
    "software": ("Software & Tools", 3),
}
FEATURED_MAX = 5
IMAGES_MAX = 41  # the lead image plus C2's 40 further images

Id = Annotated[str, StringConstraints(pattern=ID_PATTERN, max_length=60)]
Slug = Annotated[str, StringConstraints(pattern=SLUG_PATTERN, max_length=60)]
AssetRef = Annotated[str, StringConstraints(pattern=ASSET_REF_PATTERN)]
Sha256 = Annotated[str, StringConstraints(pattern=SHA256_PATTERN)]
Text300 = Annotated[str, StringConstraints(max_length=300)]
Text8000 = Annotated[str, StringConstraints(max_length=8000)]
CategorySlug = Literal["games", "astronomy", "woodworking", "software"]
Access = Literal["open", "sign-in", "invitation"]
Phone = Literal["suitable", "desktop", "unknown"]
LinkKind = Literal["demo", "documentation", "other"]


class Status(StrEnum):
    """FR3.2 statuses, shown in words."""

    DRAFT = "Draft"
    PUBLISHED = "Published"
    CHANGED = "Changes since last publish"
    TAKEN_DOWN = "Taken down"


def utc_now() -> datetime:
    return datetime.now(UTC)


def format_timestamp(moment: datetime) -> str:
    """RFC 3339 UTC with second precision (C2 ``publishedAt``)."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_https_non_repository(value: str, what: str) -> str:
    """C2 NonRepositoryHttpsUrl: https, at most 2048 characters, not a repository host."""
    if len(value) > 2048 or not value.startswith("https://") or any(c.isspace() for c in value):
        raise ValueError(f"{what} must be an https:// address without spaces")
    if len(value) <= len("https://"):
        raise ValueError(f"{what} must name a host")
    if REPOSITORY_HOST.match(value):
        raise ValueError(f"{what} must not point at a repository host; add it as a repository")
    return value


class Link(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: LinkKind = "other"
    label: Annotated[str, StringConstraints(min_length=1, max_length=80)]
    url: str

    @field_validator("url")
    @classmethod
    def _url(cls, value: str) -> str:
        return check_https_non_repository(value, "a link")


class Repository(BaseModel):
    """An owner-entered GitHub repository address; visibility is read at preparation time."""

    model_config = ConfigDict(extra="forbid")
    url: str

    @field_validator("url")
    @classmethod
    def _url(cls, value: str) -> str:
        if not GITHUB_REPOSITORY.match(value):
            raise ValueError("a repository must be https://github.com/<owner>/<name>")
        return value.removesuffix("/").removesuffix(".git")

    def owner_and_name(self) -> tuple[str, str]:
        match = GITHUB_REPOSITORY.match(self.url)
        if match is None:  # pragma: no cover - validated on construction
            raise ValueError("invalid repository address")
        return match.group(1), match.group(2)


class DraftImage(BaseModel):
    """An uploaded image: its original stays private, its derivatives may be published."""

    model_config = ConfigDict(extra="forbid")
    assetRef: AssetRef  # noqa: N815 - stored with the C2 field name
    altText: Text300 = ""  # noqa: N815
    caption: Text300 = ""
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    lead: bool = False
    originalFile: Annotated[str, StringConstraints(pattern=ORIGINAL_FILE_PATTERN)]  # noqa: N815
    derivatives: dict[str, Sha256] = Field(default_factory=dict)


class Sections(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inspiration: Text8000 = ""
    designChallenges: Text8000 = ""  # noqa: N815
    architecturalDecisions: Text8000 = ""  # noqa: N815
    implementation: Text8000 = ""
    outcomes: Text8000 = ""
    lessonsLearned: Text8000 = ""  # noqa: N815


class DraftFields(BaseModel):
    """Everything the owner edits. Used both for storage and for the save request."""

    model_config = ConfigDict(extra="forbid")
    title: Annotated[str, StringConstraints(max_length=120)] = ""
    slug: Slug
    summary: Annotated[str, StringConstraints(max_length=1200)] = ""
    sections: Sections = Field(default_factory=Sections)
    primaryCategory: CategorySlug | None = None  # noqa: N815
    featured: bool = False
    links: list[Link] = Field(default_factory=list, max_length=10)
    liveUrl: str = ""  # noqa: N815
    liveUrlIncluded: bool = False  # noqa: N815 - include the live URL at this Publish (FR10.7)
    liveUrlAuthorized: bool = False  # noqa: N815 - authorized after a privacy review (FR10.7)
    access: Access = "open"
    phone: Phone = "unknown"
    repositories: list[Repository] = Field(default_factory=list, max_length=10)
    rightsReviewRequired: bool = False  # noqa: N815 - FR10.6
    rightsReviewComplete: bool = False  # noqa: N815 - FR10.6

    @field_validator("liveUrl")
    @classmethod
    def _live_url(cls, value: str) -> str:
        value = value.strip()
        return check_https_non_repository(value, "the live URL") if value else ""


class ImageEdit(BaseModel):
    """Per-image fields the editor saves: alt text, caption and the lead flag, in order."""

    model_config = ConfigDict(extra="forbid")
    assetRef: AssetRef  # noqa: N815
    altText: Text300 = ""  # noqa: N815
    caption: Text300 = ""
    lead: bool = False


class SaveRequest(DraftFields):
    """PUT /api/projects/{id}: the full editable draft, plus image edits, at a revision."""

    revision: int = Field(ge=1)
    images: list[ImageEdit] = Field(default_factory=list, max_length=IMAGES_MAX)


class Draft(DraftFields):
    """``projects/<id>/project.json``."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_: Literal["portfolio-project/1"] = Field(default="portfolio-project/1", alias="schema")
    id: Id
    revision: int = Field(ge=1)
    createdAt: str  # noqa: N815
    updatedAt: str  # noqa: N815
    images: list[DraftImage] = Field(default_factory=list, max_length=IMAGES_MAX)

    def lead_image(self) -> DraftImage | None:
        return next((image for image in self.images if image.lead), None)

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")


class CreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Annotated[str, StringConstraints(min_length=1, max_length=120)]

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("give the project a title")
        return value


class PublishRequest(BaseModel):
    """The confirmation: the reviewed revision and the review the owner saw (ADR-012)."""

    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    reviewId: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{32}$")]  # noqa: N815


class TakeDownRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmTitle: str  # noqa: N815 - FR8.1: the confirmation names the exhibit


class FeaturedOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order: list[Id] = Field(max_length=FEATURED_MAX)


class PublishedVersion(BaseModel):
    """``published/<id>.json``: the frozen published version."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_: Literal["portfolio-published-version/1"] = Field(
        default="portfolio-published-version/1", alias="schema"
    )
    projectId: Id  # noqa: N815
    sourceRevision: int = Field(ge=1)  # noqa: N815
    publishedAt: str  # noqa: N815
    exhibit: dict[str, Any]
    derivatives: dict[str, Sha256]

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")


class Withdrawn(BaseModel):
    """``withdrawn/<id>.json``: the record that a project was taken down (FR3.2, FR8.3)."""

    model_config = ConfigDict(extra="forbid")
    projectId: Id  # noqa: N815
    takenDownAt: str  # noqa: N815
    lastPublishedRevision: int = Field(ge=1)  # noqa: N815


class FeaturedOrder(BaseModel):
    """``published/featured-order.json``: the published carousel order, by project id."""

    model_config = ConfigDict(extra="forbid")
    order: list[Id] = Field(default_factory=list, max_length=FEATURED_MAX)


class SiteSettings(BaseModel):
    """``studio.json``: the public C2 ``site`` block."""

    model_config = ConfigDict(extra="forbid")
    ownerName: Annotated[str, StringConstraints(max_length=120)]  # noqa: N815
    githubProfileUrl: Annotated[  # noqa: N815
        str, StringConstraints(pattern=r"^https://github\.com/[A-Za-z0-9-]+$")
    ]


def derive_status(
    draft: Draft, published: PublishedVersion | None, withdrawn: Withdrawn | None
) -> Status:
    """ADR-003: status from the draft revision, the published version and take-down."""
    if published is not None:
        return Status.PUBLISHED if published.sourceRevision == draft.revision else Status.CHANGED
    if withdrawn is not None:
        return Status.TAKEN_DOWN
    return Status.DRAFT


def propose_slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:60].strip("-") or "project"


def with_suffix(slug: str, number: int) -> str:
    suffix = f"-{number}"
    return f"{slug[: 60 - len(suffix)].rstrip('-')}{suffix}"
