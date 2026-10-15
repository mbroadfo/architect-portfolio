"""C2 PublicSiteSnapshot 1.0: exhibits from drafts, badges, the whole-site snapshot.

The exhibit is the only thing a published version carries to the public site, so it is built
here from an explicit allow-list (FR4.10 export allow-list, NFR2):

- text: title, summary and the non-empty narrative sections;
- the lead image and the further images, with alt text and optional captions;
- links; the live URL only when the owner included it at this Publish AND it is authorized;
- badges derived from the access fields and the repository checks, never typed;
- name, URL and OSI licence of each repository GitHub confirmed public at preparation time;
- the primary category and featured flag.

Everything is validated against closed models of the C2 schema (``validate_snapshot``); the
renderer validates it again with the JSON Schema before rendering.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from portfolio_studio.errors import ValidationFailedError
from portfolio_studio.github import RepositoryCheck
from portfolio_studio.model import (
    ASSET_REF_PATTERN,
    CATEGORIES,
    SECTION_KEYS,
    SLUG_PATTERN,
    Draft,
    DraftImage,
    SiteSettings,
    check_https_non_repository,
)

LIVE_BADGES: dict[str, str] = {
    "open": "inBrowser",
    "sign-in": "signInRequired",
    "invitation": "byInvitation",
}
BADGES_MAX = 6
# C2 ``generation``. The renderer does not use it, and it must not carry anything from the
# private repository: before security review LS-7 it was the content repository's commit
# count, which moves with every private draft save. It is a fixed, non-identifying value.
PUBLIC_GENERATION = 0


def live_url_published(draft: Draft) -> bool:
    """FR10.7: the live URL is public only when included at this Publish and authorized."""
    return bool(draft.liveUrl) and draft.liveUrlIncluded and draft.liveUrlAuthorized


def c2_image(image: DraftImage) -> dict[str, Any]:
    result: dict[str, Any] = {
        "assetRef": image.assetRef,
        "altText": image.altText,
        "width": image.width,
        "height": image.height,
    }
    if image.caption.strip():
        result["caption"] = image.caption
    return result


def derive_badges(draft: Draft, checks: Sequence[RepositoryCheck]) -> list[dict[str, Any]]:
    """FR4.10 badges, consistent with the renderer's rules S4 to S6.

    A repository that is not confirmed public earns "Source private" only when no linked
    repository is confirmed public (C2 rule S6), and never exposes its name or address.
    """
    badges: list[dict[str, Any]] = []
    if live_url_published(draft):
        badges.append({"kind": LIVE_BADGES[draft.access]})
    if draft.phone == "desktop":
        badges.append({"kind": "bestOnDesktop"})
    public = [check for check in checks if check.confirmed_public]
    for check in public:
        spdx = check.open_source_licence()
        badge = {"kind": "openSource", "spdx": spdx} if spdx else {"kind": "sourceAvailable"}
        if badge not in badges:
            badges.append(badge)
    if checks and not public:
        badges.append({"kind": "sourcePrivate"})
    return badges[:BADGES_MAX]


def public_repositories(checks: Sequence[RepositoryCheck]) -> list[dict[str, Any]]:
    """Name, URL and OSI licence of each repository confirmed public; nothing else."""
    result: list[dict[str, Any]] = []
    for check in checks:
        if not check.confirmed_public or check.name is None:
            continue
        entry: dict[str, Any] = {"name": check.name, "url": check.url}
        licence = check.open_source_licence()
        if licence:
            entry["licence"] = licence
        if entry not in result:
            result.append(entry)
    return result


def category(slug: str) -> dict[str, Any]:
    name, position = CATEGORIES[slug]
    return {"slug": slug, "name": name, "position": position}


def build_exhibit(
    draft: Draft, checks: Sequence[RepositoryCheck], published_at: str
) -> dict[str, Any]:
    """Map a draft to a C2 Exhibit. The caller has already checked the publish blockers."""
    lead = draft.lead_image()
    if lead is None:
        raise ValidationFailedError("choose a lead image")
    sections = {
        key: getattr(draft.sections, key)
        for key in SECTION_KEYS
        if getattr(draft.sections, key).strip()
    }
    exhibit: dict[str, Any] = {
        "slug": draft.slug,
        "title": draft.title,
        "summary": draft.summary,
        "sections": sections,
        "leadImage": c2_image(lead),
        "images": [c2_image(image) for image in draft.images if not image.lead],
        "attachments": [],
        "links": [link.model_dump() for link in draft.links],
        "badges": derive_badges(draft, checks),
        "publicRepositories": public_repositories(checks),
        "featured": draft.featured,
        "publishedAt": published_at,
    }
    if live_url_published(draft):
        exhibit["liveUrl"] = draft.liveUrl
    if draft.primaryCategory:
        exhibit["primaryCategory"] = category(draft.primaryCategory)
    validate_exhibit(exhibit)
    return exhibit


def build_snapshot(
    exhibits: Iterable[Mapping[str, Any]],
    featured_slugs: Sequence[str],
    site: SiteSettings,
    generation: int,
) -> dict[str, Any]:
    """The whole-site snapshot, newest exhibit first, validated against C2 (closed)."""
    ordered = sorted(
        (dict(exhibit) for exhibit in exhibits),
        key=lambda e: (e["publishedAt"], e["slug"]),
        reverse=True,
    )
    featured = {e["slug"] for e in ordered if e["featured"]}
    counts: dict[str, int] = {}
    for exhibit in ordered:
        primary = exhibit.get("primaryCategory")
        if primary:
            counts[primary["slug"]] = counts.get(primary["slug"], 0) + 1
    categories = [
        {**category(slug), "count": counts[slug]}
        for slug in sorted(counts, key=lambda s: CATEGORIES[s][1])
    ]
    snapshot = {
        "schemaVersion": "1.0",
        "generation": generation,
        "site": {
            "ownerName": site.ownerName,
            "githubProfileUrl": site.githubProfileUrl,
            "contactEmail": None,
        },
        "exhibits": ordered,
        "featuredOrder": [slug for slug in featured_slugs if slug in featured][:5],
        "categories": categories,
    }
    validate_snapshot(snapshot)
    return snapshot


# --- the C2 schema as closed models -------------------------------------------------------

_Closed = ConfigDict(extra="forbid", strict=True)
_Slug = Annotated[str, StringConstraints(pattern=SLUG_PATTERN, max_length=60)]
_AssetRef = Annotated[str, StringConstraints(pattern=ASSET_REF_PATTERN)]
_Spdx = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9.+-]{1,40}$")]
_Timestamp = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")]
_Section = Annotated[str, StringConstraints(max_length=8000)]
_CategorySlug = Literal["games", "astronomy", "woodworking", "software"]


class _Image(BaseModel):
    model_config = _Closed
    assetRef: _AssetRef  # noqa: N815 - C2 field names
    altText: Annotated[str, StringConstraints(min_length=1, max_length=300)]  # noqa: N815
    caption: Annotated[str, StringConstraints(max_length=300)] | None = None
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class _Sections(BaseModel):
    model_config = _Closed
    inspiration: _Section | None = None
    designChallenges: _Section | None = None  # noqa: N815
    architecturalDecisions: _Section | None = None  # noqa: N815
    implementation: _Section | None = None
    outcomes: _Section | None = None
    lessonsLearned: _Section | None = None  # noqa: N815


class _Link(BaseModel):
    model_config = _Closed
    kind: Literal["demo", "documentation", "other"]
    label: Annotated[str, StringConstraints(max_length=80)]
    url: str


class _Badge(BaseModel):
    model_config = _Closed
    kind: Literal[
        "inBrowser",
        "signInRequired",
        "byInvitation",
        "bestOnDesktop",
        "openSource",
        "sourceAvailable",
        "sourcePrivate",
    ]
    spdx: _Spdx | None = None


class _Repository(BaseModel):
    model_config = _Closed
    name: Annotated[str, StringConstraints(max_length=100)]
    url: Annotated[
        str, StringConstraints(pattern=r"^https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
    ]
    licence: _Spdx | None = None


class _Category(BaseModel):
    model_config = _Closed
    slug: _CategorySlug
    name: Annotated[str, StringConstraints(max_length=60)]
    position: int = Field(ge=0)


class _CategoryWithCount(_Category):
    count: int = Field(ge=1)


class _Exhibit(BaseModel):
    model_config = _Closed
    slug: _Slug
    title: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    summary: Annotated[str, StringConstraints(max_length=1200)]
    sections: _Sections
    leadImage: _Image  # noqa: N815
    images: list[_Image] = Field(max_length=40)
    attachments: list[Any] = Field(max_length=0)
    links: list[_Link] = Field(max_length=10)
    liveUrl: str | None = None  # noqa: N815
    badges: list[_Badge] = Field(max_length=6)
    publicRepositories: list[_Repository] = Field(max_length=10)  # noqa: N815
    primaryCategory: _Category | None = None  # noqa: N815
    featured: bool
    publishedAt: _Timestamp  # noqa: N815


class _Site(BaseModel):
    model_config = _Closed
    ownerName: Annotated[str, StringConstraints(max_length=120)]  # noqa: N815
    githubProfileUrl: Annotated[  # noqa: N815
        str, StringConstraints(pattern=r"^https://github\.com/[A-Za-z0-9-]+$")
    ]
    contactEmail: None = None  # noqa: N815


class _Snapshot(BaseModel):
    model_config = _Closed
    schemaVersion: Literal["1.0"]  # noqa: N815
    generation: int = Field(ge=0)
    site: _Site
    exhibits: list[_Exhibit] = Field(max_length=200)
    featuredOrder: list[_Slug] = Field(max_length=5)  # noqa: N815
    categories: list[_CategoryWithCount] = Field(max_length=4)


def _check_urls(exhibit: Mapping[str, Any]) -> None:
    for link in exhibit.get("links", []):
        check_https_non_repository(link["url"], "a link")
    if "liveUrl" in exhibit:
        check_https_non_repository(exhibit["liveUrl"], "the live URL")


def validate_exhibit(exhibit: Mapping[str, Any]) -> None:
    """Refuse an exhibit outside the C2 allow-list."""
    try:
        _Exhibit.model_validate(exhibit)
        _check_urls(exhibit)
    except (ValidationError, ValueError) as error:
        raise ValidationFailedError(f"the exhibit is not valid against C2: {error}") from error


def validate_snapshot(snapshot: Mapping[str, Any]) -> None:
    """Refuse a snapshot outside the C2 allow-list."""
    try:
        _Snapshot.model_validate(snapshot)
        for exhibit in snapshot["exhibits"]:
            _check_urls(exhibit)
    except (ValidationError, ValueError) as error:
        raise ValidationFailedError(f"the snapshot is not valid against C2: {error}") from error
    slugs = [exhibit["slug"] for exhibit in snapshot["exhibits"]]
    if len(set(slugs)) != len(slugs):
        raise ValidationFailedError("two published exhibits share a slug")
