"""The Studio's operations on the private content repository.

Every operation that changes content runs under one lock and ends in one Git commit:

- create, save and image upload change the draft and its revision (FR3, FR4);
- the Publish review prepares the exact exhibit that would become public and lists it
  (FR7.2); confirming publishes that prepared exhibit only if the draft is still at the
  reviewed revision (ADR-012), so what Michael reviewed is what is frozen;
- take down removes the published version and its media (FR8);
- the featured order is published only through its own confirmation (FR9.7).

Nothing here builds the public site; ``build.SiteBuilder`` reads only published versions.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from portfolio_studio import c2
from portfolio_studio.errors import (
    ConflictError,
    ImageRejectedError,
    InvalidTransitionError,
    PublishBlockedError,
    SlugTakenError,
    StudioError,
    ValidationFailedError,
)
from portfolio_studio.github import RepositoryCheck, RepositoryChecker
from portfolio_studio.images import ProcessedImage, new_asset_ref, process_image
from portfolio_studio.model import (
    CATEGORIES,
    FEATURED_MAX,
    SECTION_KEYS,
    CreateRequest,
    Draft,
    DraftImage,
    FeaturedOrder,
    FeaturedOrderRequest,
    PublishedVersion,
    PublishRequest,
    SaveRequest,
    Status,
    Withdrawn,
    derive_status,
    format_timestamp,
    propose_slug,
    utc_now,
    with_suffix,
)
from portfolio_studio.renderer import RenderFailedError, StudioRenderer
from portfolio_studio.store import FEATURED_ORDER, PUBLISHED_MEDIA, ContentStore

REVIEW_SECONDS = 30 * 60
PLACEHOLDER_TIME = "1970-01-01T00:00:00Z"

logger = logging.getLogger("portfolio_studio.service")


@dataclass(frozen=True)
class Blocker:
    """A reason Publish is blocked (FR7.3), with the editor field to fix it."""

    message: str
    field: str


@dataclass
class Review:
    """A prepared Publish: the exact exhibit the confirmation lists (ADR-012)."""

    review_id: str
    project_id: str
    revision: int
    exhibit: dict[str, Any]
    created: float
    checks: list[RepositoryCheck] = field(default_factory=list)


def blockers(draft: Draft) -> list[Blocker]:
    """FR7.3: empty title, no lead image, missing alt text, outstanding rights review."""
    found: list[Blocker] = []
    if not draft.title.strip():
        found.append(Blocker("Add a title", "title"))
    if draft.lead_image() is None:
        found.append(Blocker("Choose a lead image", "images"))
    for index, image in enumerate(draft.images, start=1):
        if not image.altText.strip():
            found.append(Blocker(f"Add alt text to image {index}", f"alt-{image.assetRef}"))
    if draft.rightsReviewRequired and not draft.rightsReviewComplete:
        found.append(Blocker("Complete the rights review (FR10.6)", "rightsReviewComplete"))
    return found


def derivative_digests(images: Sequence[DraftImage]) -> dict[str, str]:
    """The published key and SHA-256 of every derivative of ``images``."""
    return {
        f"media/{image.assetRef}/{name}": digest
        for image in images
        for name, digest in sorted(image.derivatives.items())
    }


class StudioService:
    """Studio operations; one instance per content repository."""

    def __init__(
        self,
        store: ContentStore,
        renderer: StudioRenderer,
        checker: RepositoryChecker,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.store = store
        self.renderer = renderer
        self.checker = checker
        self._clock = clock
        self._lock = threading.RLock()
        self._reviews: dict[str, Review] = {}

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    # --- views -------------------------------------------------------------------------------

    def status(self, draft: Draft) -> Status:
        return derive_status(draft, self.store.published(draft.id), self.store.withdrawn(draft.id))

    def view(self, draft: Draft) -> dict[str, Any]:
        """The draft as the Studio page sees it, with its derived status."""
        published = self.store.published(draft.id)
        document = draft.to_json()
        document.pop("schema", None)
        for image in document["images"]:
            image.pop("originalFile", None)
            image.pop("derivatives", None)
        document["status"] = str(self.status(draft))
        document["publishedRevision"] = published.sourceRevision if published else None
        document["blockers"] = [b.__dict__ for b in blockers(draft)]
        return document

    def list_projects(self) -> list[dict[str, Any]]:
        order = self.store.featured_order().order
        projects = []
        for project_id in self.store.project_ids():
            draft = self.store.draft(project_id)
            lead = draft.lead_image()
            projects.append(
                {
                    "id": draft.id,
                    "title": draft.title,
                    "slug": draft.slug,
                    "status": str(self.status(draft)),
                    "category": CATEGORIES[draft.primaryCategory][0]
                    if draft.primaryCategory
                    else None,
                    "featured": draft.featured,
                    "featuredPosition": order.index(draft.id) + 1 if draft.id in order else None,
                    "revision": draft.revision,
                    "updatedAt": draft.updatedAt,
                    "leadImage": lead.assetRef if lead else None,
                    "repositories": len(draft.repositories),
                }
            )
        return projects

    def get(self, project_id: str) -> dict[str, Any]:
        return self.view(self.store.draft(project_id))

    # --- create and save -----------------------------------------------------------------------

    def _taken_slugs(self, except_id: str | None) -> set[str]:
        taken: set[str] = set()
        for project_id in self.store.project_ids():
            if project_id == except_id:
                continue
            taken.add(self.store.draft(project_id).slug)
            published = self.store.published(project_id)
            if published is not None:
                taken.add(str(published.exhibit["slug"]))
        return taken

    def create(self, request: CreateRequest) -> dict[str, Any]:
        """FR3: a project can start with just a title; it starts as a Draft."""
        with self._lock:
            base = propose_slug(request.title)
            existing = set(self.store.project_ids())
            taken = self._taken_slugs(None) | existing
            project_id, number = base, 2
            while project_id in taken:
                project_id, number = with_suffix(base, number), number + 1
            now = format_timestamp(utc_now())
            draft = Draft(
                id=project_id,
                slug=project_id,
                title=request.title.strip(),
                revision=1,
                createdAt=now,
                updatedAt=now,
            )
            paths = [self.store.relative(self.store.project_dir(project_id))]
            with self.store.transaction(paths, f"Create project {draft.title}") as commit:
                self.store.write_draft(draft)
                commit()
            logger.info("project created", extra={"fields": {"project": project_id}})
            return self.view(draft)

    def _check_revision(self, draft: Draft, revision: int) -> None:
        if draft.revision != revision:
            raise ConflictError(
                f"this project was saved elsewhere (now revision {draft.revision}); "
                "reload it before saving"
            )

    def _featured_count(self, except_id: str) -> int:
        return sum(
            1
            for project_id in self.store.project_ids()
            if project_id != except_id and self.store.draft(project_id).featured
        )

    def _apply_image_edits(self, draft: Draft, request: SaveRequest) -> list[DraftImage]:
        current = {image.assetRef: image for image in draft.images}
        requested = [edit.assetRef for edit in request.images]
        if len(set(requested)) != len(requested) or not set(requested) <= set(current):
            raise ValidationFailedError("the image list does not match this project's images")
        if sum(1 for edit in request.images if edit.lead) > 1:
            raise ValidationFailedError("choose one lead image")
        return [
            current[edit.assetRef].model_copy(
                update={"altText": edit.altText, "caption": edit.caption, "lead": edit.lead}
            )
            for edit in request.images
        ]

    def save(self, project_id: str, request: SaveRequest) -> dict[str, Any]:
        """Save the whole draft at the revision the editor loaded (FR3.4: no silent overwrite)."""
        with self._lock:
            draft = self.store.draft(project_id)
            self._check_revision(draft, request.revision)
            if request.slug in self._taken_slugs(project_id):
                raise SlugTakenError(f"the address /work/{request.slug} is already in use")
            if request.featured and self._featured_count(project_id) >= FEATURED_MAX:
                raise ValidationFailedError(
                    f"up to {FEATURED_MAX} projects can be featured; unfeature one first"
                )
            images = self._apply_image_edits(draft, request)
            kept = {image.assetRef for image in images}
            removed = [image for image in draft.images if image.assetRef not in kept]
            fields = request.model_dump(exclude={"revision", "images"})
            updated = Draft.model_validate(
                {
                    **draft.to_json(),
                    **fields,
                    "images": [image.model_dump() for image in images],
                    "revision": draft.revision + 1,
                    "updatedAt": format_timestamp(utc_now()),
                }
            )
            paths = [self.store.relative(self.store.project_dir(project_id))]
            title = updated.title or "Untitled"
            message = f"Save {title} (revision {updated.revision})"
            with self.store.transaction(paths, message) as commit:
                for image in removed:
                    self.store.remove(self.store.derived_dir(project_id, image.assetRef))
                    self.store.remove(self.store.original_path(project_id, image.originalFile))
                self.store.write_draft(updated)
                commit()
            return self.view(updated)

    # --- images --------------------------------------------------------------------------------

    def upload_image(self, project_id: str, revision: int, data: bytes) -> dict[str, Any]:
        """FR4.2: validate, re-encode the derivatives, keep the original privately."""
        with self._lock:
            draft = self.store.draft(project_id)
            self._check_revision(draft, revision)
            if len(draft.images) >= 41:
                raise ImageRejectedError("an exhibit can have at most 41 images")
            processed = process_image(data)
            asset_ref = new_asset_ref()
            image = self._image_record(asset_ref, processed, lead=draft.lead_image() is None)
            updated = draft.model_copy(
                update={
                    "images": [*draft.images, image],
                    "revision": draft.revision + 1,
                    "updatedAt": format_timestamp(utc_now()),
                }
            )
            paths = [self.store.relative(self.store.project_dir(project_id))]
            message = (
                f"Upload an image to {draft.title or 'Untitled'} (revision {updated.revision})"
            )
            with self.store.transaction(paths, message) as commit:
                self.store.original_path(project_id, image.originalFile).parent.mkdir(
                    parents=True, exist_ok=True
                )
                self.store.original_path(project_id, image.originalFile).write_bytes(data)
                folder = self.store.derived_dir(project_id, asset_ref)
                folder.mkdir(parents=True, exist_ok=True)
                for derivative in processed.derivatives:
                    (folder / derivative.key).write_bytes(derivative.data)
                self.store.write_draft(updated)
                commit()
            logger.info("image uploaded", extra={"fields": {"project": project_id}})
            return self.view(updated)

    @staticmethod
    def _image_record(asset_ref: str, processed: ProcessedImage, lead: bool) -> DraftImage:
        return DraftImage(
            assetRef=asset_ref,
            width=processed.width,
            height=processed.height,
            lead=lead,
            originalFile=f"{asset_ref}.{processed.original_extension}",
            derivatives={d.key: d.sha256 for d in processed.derivatives},
        )

    # --- preview -------------------------------------------------------------------------------

    def _checks(self, draft: Draft, fresh: bool) -> list[RepositoryCheck]:
        return [self.checker.check(repository, fresh=fresh) for repository in draft.repositories]

    def _snapshot_with(self, project_id: str, exhibit: dict[str, Any] | None) -> dict[str, Any]:
        """Published exhibits of every other project, plus ``exhibit`` for this one."""
        exhibits = [
            version.exhibit
            for version in self.store.published_versions()
            if version.projectId != project_id
        ]
        order = list(self.store.featured_order().order)
        if exhibit is not None:
            exhibits.append(exhibit)
            if exhibit["featured"] and project_id not in order:
                order.append(project_id)
        slugs = self._slugs_by_id(project_id, exhibit)
        return c2.build_snapshot(
            exhibits,
            [slugs[i] for i in order if i in slugs],
            self.store.settings(),
            c2.PUBLIC_GENERATION,
        )

    def _slugs_by_id(self, project_id: str, exhibit: dict[str, Any] | None) -> dict[str, str]:
        slugs = {
            version.projectId: str(version.exhibit["slug"])
            for version in self.store.published_versions()
        }
        slugs.pop(project_id, None)
        if exhibit is not None:
            slugs[project_id] = str(exhibit["slug"])
        return slugs

    def preview(self, project_id: str) -> dict[str, str]:
        """FR6: render the draft with the shared renderer in preview mode (never public)."""
        draft = self.store.draft(project_id)
        hard = [b for b in blockers(draft) if b.field != "rightsReviewComplete"]
        if hard:
            raise PublishBlockedError("to preview, first: " + "; ".join(b.message for b in hard))
        exhibit = c2.build_exhibit(draft, self._checks(draft, fresh=False), self._now())
        snapshot = self._snapshot_with(project_id, exhibit)
        try:
            output = self.renderer.render(snapshot, "preview", preview_slug=draft.slug)
        except RenderFailedError as error:
            raise StudioError(f"the preview could not be rendered: {error}") from error
        return {page.path: page.html for page in output.pages}

    def _now(self) -> str:
        return format_timestamp(utc_now())

    # --- publish -------------------------------------------------------------------------------

    def _expire_reviews(self) -> None:
        now = self._clock()
        for review_id in [k for k, r in self._reviews.items() if now - r.created > REVIEW_SECONDS]:
            del self._reviews[review_id]

    def prepare_review(self, project_id: str) -> dict[str, Any]:
        """FR7.2: everything that becomes public, prepared once and bound to this revision."""
        with self._lock:
            draft = self.store.draft(project_id)
            found = blockers(draft)
            checks = self._checks(draft, fresh=True)
            status = self.status(draft)
            inventory = self._inventory(draft, checks, status)
            if found:
                return {**inventory, "blockers": [b.__dict__ for b in found], "reviewId": None}
            exhibit = c2.build_exhibit(draft, checks, PLACEHOLDER_TIME)
            self._expire_reviews()
            review = Review(
                review_id=secrets.token_hex(16),
                project_id=project_id,
                revision=draft.revision,
                exhibit=exhibit,
                created=self._clock(),
                checks=checks,
            )
            self._reviews[review.review_id] = review
            return {
                **inventory,
                "blockers": [],
                "reviewId": review.review_id,
                "badges": exhibit["badges"],
                "publicRepositories": exhibit["publicRepositories"],
            }

    def _inventory(
        self, draft: Draft, checks: Sequence[RepositoryCheck], status: Status
    ) -> dict[str, Any]:
        text = [
            {"label": "Title", "value": draft.title},
            {"label": "Summary", "value": draft.summary},
        ]
        text += [
            {"label": key, "value": getattr(draft.sections, key)}
            for key in SECTION_KEYS
            if getattr(draft.sections, key).strip()
        ]
        if not c2.live_url_published(draft):
            live = {"url": None, "reason": self._live_reason(draft)}
        else:
            live = {"url": draft.liveUrl, "reason": "included and authorized"}
        return {
            "projectId": draft.id,
            "title": draft.title,
            "revision": draft.revision,
            "status": str(status),
            "isUpdate": status in (Status.PUBLISHED, Status.CHANGED),
            "address": f"/work/{draft.slug}",
            "text": [entry for entry in text if entry["value"].strip()],
            "images": [
                {"assetRef": i.assetRef, "altText": i.altText, "caption": i.caption, "lead": i.lead}
                for i in draft.images
            ],
            "links": [link.model_dump() for link in draft.links],
            "liveUrl": live,
            "repositories": [
                {
                    "url": check.url if check.confirmed_public else None,
                    "confirmedPublic": check.confirmed_public,
                    "licence": check.licence if check.confirmed_public else None,
                    "note": check.note,
                    "checkedAt": format_timestamp_from_epoch(check.checked_at),
                }
                for check in checks
            ],
            "badges": c2.derive_badges(draft, checks),
            "publicRepositories": c2.public_repositories(checks),
            "category": CATEGORIES[draft.primaryCategory][0] if draft.primaryCategory else None,
            "featured": draft.featured,
            "rightsReview": "complete"
            if draft.rightsReviewComplete
            else ("outstanding" if draft.rightsReviewRequired else "not required"),
        }

    @staticmethod
    def _live_reason(draft: Draft) -> str:
        if not draft.liveUrl:
            return "no live URL"
        if not draft.liveUrlAuthorized:
            return "not authorized (FR10.7)"
        return "not included at this Publish"

    def publish(self, project_id: str, request: PublishRequest) -> dict[str, Any]:
        """Freeze the reviewed exhibit as the published version (ADR-002, ADR-012)."""
        with self._lock:
            draft = self.store.draft(project_id)
            published = self.store.published(project_id)
            if published is not None and published.sourceRevision == request.revision:
                return self._publish_result(draft, published)  # FR7.6: safe to repeat
            self._expire_reviews()
            review = self._reviews.get(request.reviewId)
            if review is None or review.project_id != project_id:
                raise ConflictError("this review has expired; open the Publish review again")
            if review.revision != request.revision:
                raise ConflictError("this review is for another revision; open it again")
            self._check_revision(draft, request.revision)
            if blockers(draft):
                raise PublishBlockedError("Publish is blocked; open the review to see why")
            version = self._freeze(draft, review)
            update = published is not None
            self._write_publication(draft, version, published, update)
            del self._reviews[request.reviewId]
            logger.info("published", extra={"fields": {"project": project_id}})
            return self._publish_result(draft, version)

    def _freeze(self, draft: Draft, review: Review) -> PublishedVersion:
        used = [i for i in draft.images if i.assetRef in _asset_refs(review.exhibit)]
        exhibit = {**review.exhibit, "publishedAt": self._now()}
        c2.validate_exhibit(exhibit)
        return PublishedVersion(
            projectId=draft.id,
            sourceRevision=draft.revision,
            publishedAt=exhibit["publishedAt"],
            exhibit=exhibit,
            derivatives=derivative_digests(used),
        )

    def _write_publication(
        self,
        draft: Draft,
        version: PublishedVersion,
        previous: PublishedVersion | None,
        update: bool,
    ) -> None:
        new_refs = _asset_refs(version.exhibit)
        old_refs = _asset_refs(previous.exhibit) if previous else set()
        paths = [
            self.store.relative(self.store.published_path(draft.id)),
            self.store.relative(self.store.withdrawn_path(draft.id)),
            FEATURED_ORDER,
            *(f"{PUBLISHED_MEDIA}/{ref}" for ref in sorted(new_refs | old_refs)),
        ]
        verb = "Update the public exhibit" if update else "Publish"
        message = f"{verb} {draft.title} (revision {draft.revision})"
        with self.store.transaction(paths, message) as commit:
            for ref in sorted(old_refs - new_refs):
                self.store.remove(self.store.published_media_dir(ref))
            for key, digest in version.derivatives.items():
                self._copy_derivative(draft.id, key, digest)
            self.store.write_published(version)
            self.store.remove(self.store.withdrawn_path(draft.id))
            self._update_featured(draft.id, bool(version.exhibit["featured"]))
            commit()

    def _copy_derivative(self, project_id: str, key: str, digest: str) -> None:
        _, asset_ref, name = key.split("/")
        source = self.store.derived_dir(project_id, asset_ref) / name
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise StudioError(f"the derivative {asset_ref}/{name} changed since it was made")
        target = self.store.published_media_dir(asset_ref) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def _update_featured(self, project_id: str, featured: bool) -> None:
        order = [i for i in self.store.featured_order().order if i != project_id]
        if featured:
            order.append(project_id)
        self.store.write_featured_order(FeaturedOrder(order=order[:FEATURED_MAX]))

    def _publish_result(self, draft: Draft, version: PublishedVersion) -> dict[str, Any]:
        return {
            "projectId": draft.id,
            "sourceRevision": version.sourceRevision,
            "publishedAt": version.publishedAt,
            "status": str(self.status(draft)),
        }

    # --- take down -----------------------------------------------------------------------------

    def take_down(self, project_id: str, confirm_title: str) -> dict[str, Any]:
        """FR8: remove the published version and its media; keep the Studio content."""
        with self._lock:
            draft = self.store.draft(project_id)
            published = self.store.published(project_id)
            if published is None:
                raise InvalidTransitionError("only a published exhibit can be taken down")
            public_title = str(published.exhibit["title"])
            if confirm_title != public_title:
                raise ValidationFailedError("the confirmation does not name this exhibit")
            refs = _asset_refs(published.exhibit)
            paths = [
                self.store.relative(self.store.published_path(project_id)),
                self.store.relative(self.store.withdrawn_path(project_id)),
                FEATURED_ORDER,
                *(f"{PUBLISHED_MEDIA}/{ref}" for ref in sorted(refs)),
            ]
            with self.store.transaction(paths, f"Take down {public_title}") as commit:
                self.store.remove(self.store.published_path(project_id))
                for ref in refs:
                    self.store.remove(self.store.published_media_dir(ref))
                self.store.write_withdrawn(
                    Withdrawn(
                        projectId=project_id,
                        takenDownAt=self._now(),
                        lastPublishedRevision=published.sourceRevision,
                    )
                )
                self._update_featured(project_id, featured=False)
                commit()
            logger.info("taken down", extra={"fields": {"project": project_id}})
            return self.view(draft)

    # --- featured order ------------------------------------------------------------------------

    def featured(self) -> dict[str, Any]:
        order = self.store.featured_order().order
        entries = []
        for project_id in order:
            published = self.store.published(project_id)
            if published is not None:
                entries.append({"id": project_id, "title": published.exhibit["title"]})
        pending = [
            {"id": p["id"], "title": p["title"], "status": p["status"]}
            for p in self.list_projects()
            if p["featured"] and p["id"] not in order
        ]
        return {"order": entries, "notYetPublished": pending, "max": FEATURED_MAX}

    def update_featured_order(self, request: FeaturedOrderRequest) -> dict[str, Any]:
        """FR9.7: reorder the published carousel through an explicit confirmation."""
        with self._lock:
            current = self.store.featured_order().order
            if sorted(request.order) != sorted(current) or len(set(request.order)) != len(
                request.order
            ):
                raise ValidationFailedError("the new order must list the featured exhibits once")
            if request.order == current:
                return self.featured()  # FR7.6: confirming the same order changes nothing
            with self.store.transaction([FEATURED_ORDER], "Update featured order") as commit:
                self.store.write_featured_order(FeaturedOrder(order=request.order))
                commit()
            return self.featured()

    # --- activity ------------------------------------------------------------------------------

    def activity(self) -> list[dict[str, str]]:
        """FR7.7: the content repository's Git history is the activity log."""
        return [{"time": c.time, "action": c.subject} for c in self.store.git.log()]


def _asset_refs(exhibit: dict[str, Any]) -> set[str]:
    return {str(image["assetRef"]) for image in [exhibit["leadImage"], *exhibit["images"]]}


def format_timestamp_from_epoch(epoch: float) -> str:
    return format_timestamp(datetime.fromtimestamp(epoch, UTC))
