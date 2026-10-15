"""Studio operations on a real temporary content repository (FR3, FR4, FR7, FR8, FR9.7)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from portfolio_studio.errors import (
    ConflictError,
    InvalidTransitionError,
    PublishBlockedError,
    SlugTakenError,
    StudioError,
    ValidationFailedError,
)
from portfolio_studio.model import (
    CreateRequest,
    FeaturedOrderRequest,
    PublishRequest,
    SaveRequest,
)
from portfolio_studio.service import StudioService
from portfolio_studio.store import ContentStore

from .conftest import PUBLIC_REPO, make_image, publish, ready_project

C2_EXHIBIT_KEYS = {
    "slug",
    "title",
    "summary",
    "sections",
    "leadImage",
    "images",
    "attachments",
    "links",
    "liveUrl",
    "badges",
    "publicRepositories",
    "primaryCategory",
    "featured",
    "publishedAt",
}


def save(service: StudioService, project_id: str, **changes: Any) -> dict[str, Any]:
    view = service.get(project_id)
    fields = {
        key: view[key]
        for key in (
            "title",
            "slug",
            "summary",
            "sections",
            "primaryCategory",
            "featured",
            "links",
            "liveUrl",
            "liveUrlIncluded",
            "liveUrlAuthorized",
            "access",
            "phone",
            "repositories",
            "rightsReviewRequired",
            "rightsReviewComplete",
        )
    }
    fields["images"] = [
        {k: image[k] for k in ("assetRef", "altText", "caption", "lead")}
        for image in view["images"]
    ]
    fields["revision"] = view["revision"]
    fields.update(changes)
    return service.save(project_id, SaveRequest.model_validate(fields))


def test_create_starts_a_draft_with_a_commit(service: StudioService) -> None:
    """FR3.1/FR3.2: a title is enough; the project starts as a Draft; Git records it."""
    view = service.create(CreateRequest(title="My Work!"))
    assert view["id"] == "my-work" and view["status"] == "Draft" and view["revision"] == 1
    second = service.create(CreateRequest(title="My work"))
    assert second["id"] == "my-work-2"
    assert service.activity()[0]["action"] == "Create project My work"
    assert [p["id"] for p in service.list_projects()] == ["my-work", "my-work-2"]


def test_save_with_a_stale_revision_is_refused(service: StudioService) -> None:
    """FR3.4: a save from a second tab at an old revision is refused, not merged."""
    view = service.create(CreateRequest(title="STARS"))
    save(service, view["id"], summary="first tab")
    with pytest.raises(ConflictError):
        save(service, view["id"], summary="second tab", revision=view["revision"])
    assert service.get(view["id"])["summary"] == "first tab"


def test_slug_must_be_unique_including_published_slugs(service: StudioService) -> None:
    ready_project(service, "Alpha")
    publish(service, "alpha")
    save(service, "alpha", slug="alpha-renamed")  # the published version keeps /work/alpha
    beta = service.create(CreateRequest(title="Beta"))
    with pytest.raises(SlugTakenError):
        save(service, beta["id"], slug="alpha")
    with pytest.raises(SlugTakenError):
        save(service, beta["id"], slug="alpha-renamed")


def test_at_most_five_projects_can_be_featured(service: StudioService) -> None:
    """FR9.7: drafts count towards the limit of five."""
    for number in range(5):
        view = service.create(CreateRequest(title=f"P{number}"))
        save(service, view["id"], featured=True)
    extra = service.create(CreateRequest(title="Extra"))
    with pytest.raises(ValidationFailedError, match="featured"):
        save(service, extra["id"], featured=True)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"title": ""}, "Add a title"),
        ({"images": []}, "Choose a lead image"),
        ({"rightsReviewRequired": True}, "rights review"),
    ],
)
def test_publish_is_blocked_with_the_reason(
    service: StudioService, change: dict[str, Any], message: str
) -> None:
    """FR7.3: empty title, no lead image, outstanding rights review block Publish."""
    ready_project(service)
    save(service, "stars", **change)
    review = service.prepare_review("stars")
    assert review["reviewId"] is None
    assert any(message in b["message"] for b in review["blockers"])
    with pytest.raises(ConflictError):
        service.publish("stars", PublishRequest(revision=99, reviewId="0" * 32))


def test_missing_alt_text_and_no_lead_block_publish(service: StudioService) -> None:
    """FR7.3, D-19: every image needs alt text, and one is the lead image."""
    view = ready_project(service)
    image = view["images"][0]
    save(service, "stars", images=[{"assetRef": image["assetRef"], "altText": "", "lead": False}])
    messages = [b["message"] for b in service.prepare_review("stars")["blockers"]]
    assert "Add alt text to image 1" in messages and "Choose a lead image" in messages
    with pytest.raises(PublishBlockedError):
        service.preview("stars")


def test_rights_review_complete_unblocks(service: StudioService) -> None:
    ready_project(service, rightsReviewRequired=True, rightsReviewComplete=True)
    assert service.prepare_review("stars")["reviewId"]


def test_publish_freezes_exactly_the_c2_fields(service: StudioService) -> None:
    """ADR-002/NFR2: the published version holds only C2 exhibit fields and digests."""
    ready_project(
        service,
        repositories=[{"url": "https://github.com/mbroadfo/stars"}],
        liveUrl="https://stars.example.org",
        links=[{"kind": "demo", "label": "Demo", "url": "https://demo.example.org"}],
        phone="desktop",
        featured=True,
    )
    result = publish(service, "stars")
    assert result["status"] == "Published" and result["sourceRevision"] == 3
    path = service.store.published_path("stars")
    document = json.loads(path.read_text(encoding="utf-8"))
    assert set(document) == {
        "schema",
        "projectId",
        "sourceRevision",
        "publishedAt",
        "exhibit",
        "derivatives",
    }
    exhibit = document["exhibit"]
    assert set(exhibit) <= C2_EXHIBIT_KEYS
    assert "liveUrl" not in exhibit  # not included and not authorized (FR10.7)
    assert exhibit["sections"] == {"inspiration": "STARS inspiration"}
    assert {"kind": "sourceAvailable"} in exhibit["badges"]  # no licence (FR4.10)
    assert {"kind": "bestOnDesktop"} in exhibit["badges"]
    assert exhibit["publicRepositories"] == [
        {"name": "stars", "url": "https://github.com/mbroadfo/stars"}
    ]
    lead = exhibit["leadImage"]["assetRef"]
    assert all(key.startswith(f"media/{lead}/") for key in document["derivatives"])
    for key in document["derivatives"]:
        assert (service.store.root / "published" / key).is_file()
    text = path.read_text(encoding="utf-8")
    for private in ("originalFile", "liveUrlAuthorized", "rightsReview", 'revision"'):
        assert private not in text
    assert service.store.featured_order().order == ["stars"]
    assert service.activity()[0]["action"] == "Publish STARS (revision 3)"


def test_live_url_is_published_only_when_included_and_authorized(
    service: StudioService,
) -> None:
    """FR10.7: included at this Publish AND authorized; then the access badge appears."""
    ready_project(service, liveUrl="https://stars.example.org", liveUrlIncluded=True)
    review = service.prepare_review("stars")
    assert review["liveUrl"] == {"url": None, "reason": "not authorized (FR10.7)"}
    save(service, "stars", liveUrlAuthorized=True)
    review = service.prepare_review("stars")
    assert review["liveUrl"]["url"] == "https://stars.example.org"
    publish(service, "stars")
    exhibit = service.store.published("stars").exhibit  # type: ignore[union-attr]
    assert exhibit["liveUrl"] == "https://stars.example.org"
    assert {"kind": "inBrowser"} in exhibit["badges"]


@pytest.mark.parametrize(
    "answer",
    [
        (404, None),
        (403, None),
        (500, None),
        (200, {**PUBLIC_REPO, "private": True, "visibility": "private"}),
        (200, {**PUBLIC_REPO, "full_name": "someone/else"}),
        (200, ["not", "an", "object"]),
    ],
)
def test_repository_badges_fail_closed(
    service: StudioService, github: dict[str, Any], answer: tuple[int, Any]
) -> None:
    """FR4.10, A1-P04: any GitHub error, refusal or odd answer counts as private."""
    github["mbroadfo/stars"] = answer
    ready_project(service, repositories=[{"url": "https://github.com/mbroadfo/stars"}])
    review = service.prepare_review("stars")
    assert review["badges"] == [{"kind": "sourcePrivate"}]
    assert review["publicRepositories"] == []
    assert review["repositories"][0]["url"] is None
    publish(service, "stars")
    text = service.store.published_path("stars").read_text(encoding="utf-8")
    assert "github.com" not in text and "mbroadfo/stars" not in text


def test_repository_badge_fails_closed_without_network(service: StudioService) -> None:
    ready_project(service, repositories=[{"url": "https://github.com/mbroadfo/unknown"}])
    review = service.prepare_review("stars")
    assert review["badges"] == [{"kind": "sourcePrivate"}]
    assert review["repositories"][0]["note"] == "GitHub could not be reached"


def test_osi_licence_earns_open_source(service: StudioService, github: dict[str, Any]) -> None:
    github["mbroadfo/stars"] = (200, {**PUBLIC_REPO, "license": {"spdx_id": "MIT"}})
    ready_project(service, repositories=[{"url": "https://github.com/mbroadfo/stars"}])
    review = service.prepare_review("stars")
    assert review["badges"] == [{"kind": "openSource", "spdx": "MIT"}]
    assert review["publicRepositories"][0]["licence"] == "MIT"


def test_confirmation_is_bound_to_the_reviewed_revision(service: StudioService) -> None:
    """ADR-012: a save after the review makes the confirmation stale."""
    ready_project(service)
    review = service.prepare_review("stars")
    save(service, "stars", summary="changed after review")
    with pytest.raises(ConflictError):
        service.publish(
            "stars", PublishRequest(revision=review["revision"], reviewId=review["reviewId"])
        )
    assert service.store.published("stars") is None


def test_publish_is_safe_to_repeat(service: StudioService) -> None:
    """FR7.6: a repeated confirmation returns the same published version."""
    ready_project(service)
    review = service.prepare_review("stars")
    request = PublishRequest(revision=review["revision"], reviewId=review["reviewId"])
    first = service.publish("stars", request)
    again = service.publish("stars", request)
    assert first == again
    assert len([a for a in service.activity() if a["action"].startswith("Publish")]) == 1


def test_edit_after_publish_shows_changes_and_update_replaces_media(
    service: StudioService,
) -> None:
    """FR7.5: edits stay private until 'Update the public exhibit'."""
    view = ready_project(service)
    publish(service, "stars")
    old_ref = view["images"][0]["assetRef"]
    uploaded = service.upload_image(
        "stars", service.get("stars")["revision"], make_image((500, 500))
    )
    new_ref = uploaded["images"][1]["assetRef"]
    save(
        service,
        "stars",
        summary="new summary",
        images=[{"assetRef": new_ref, "altText": "new lead", "lead": True}],
    )
    assert service.get("stars")["status"] == "Changes since last publish"
    assert service.store.published("stars").exhibit["summary"] == "STARS summary"  # type: ignore[union-attr]
    publish(service, "stars")
    assert service.get("stars")["status"] == "Published"
    assert not service.store.published_media_dir(old_ref).exists()
    assert service.store.published_media_dir(new_ref).is_dir()
    assert not service.store.derived_dir("stars", old_ref).exists()  # removed from the draft
    assert service.activity()[0]["action"].startswith("Update the public exhibit STARS")


def test_take_down_removes_the_published_version_and_media(service: StudioService) -> None:
    """FR8.2/FR8.3: the published version and media go; the Studio content stays."""
    view = ready_project(service, featured=True)
    publish(service, "stars")
    ref = view["images"][0]["assetRef"]
    with pytest.raises(ValidationFailedError):
        service.take_down("stars", "Wrong title")
    result = service.take_down("stars", "STARS")
    assert result["status"] == "Taken down"
    assert service.store.published("stars") is None
    assert not service.store.published_media_dir(ref).exists()
    assert service.store.derived_dir("stars", ref).is_dir()
    assert service.store.featured_order().order == []  # FR8.2: slot released
    with pytest.raises(InvalidTransitionError):
        service.take_down("stars", "STARS")
    save(service, "stars", summary="edited while taken down")
    assert service.get("stars")["status"] == "Taken down"
    publish(service, "stars")
    assert service.get("stars")["status"] == "Published"
    assert service.store.withdrawn("stars") is None


def test_featured_order_changes_only_through_its_confirmation(service: StudioService) -> None:
    """FR9.7: reorder the published carousel; the list must name the featured ones once."""
    for title in ("Alpha", "Beta"):
        ready_project(service, title, featured=True)
        publish(service, title.lower())
    assert [e["id"] for e in service.featured()["order"]] == ["alpha", "beta"]
    with pytest.raises(ValidationFailedError):
        service.update_featured_order(FeaturedOrderRequest(order=["alpha"]))
    result = service.update_featured_order(FeaturedOrderRequest(order=["beta", "alpha"]))
    assert [e["id"] for e in result["order"]] == ["beta", "alpha"]
    gamma = service.create(CreateRequest(title="Gamma"))
    save(service, gamma["id"], featured=True)
    assert service.featured()["notYetPublished"][0]["id"] == "gamma"


def test_preview_renders_the_draft_in_preview_mode(service: StudioService, renderer: Any) -> None:
    """FR6: preview uses the shared renderer in preview mode with the draft's slug."""
    ready_project(service)
    pages = service.preview("stars")
    assert "Preview — not public" in pages["/work/stars"]
    assert renderer.calls[-1] == ("preview", "stars")
    assert service.store.published("stars") is None


def test_preview_failure_is_reported(service: StudioService, renderer: Any) -> None:
    from portfolio_studio.renderer import RenderFailedError

    ready_project(service)

    def broken(*_: Any, **__: Any) -> Any:
        raise RenderFailedError("boom")

    renderer.render = broken
    with pytest.raises(StudioError, match="could not be rendered"):
        service.preview("stars")


def test_failed_commit_restores_the_files(service: StudioService, content: ContentStore) -> None:
    """A failed Git commit leaves the working files as they were (no half-saved draft)."""
    view = service.create(CreateRequest(title="STARS"))
    before = content.draft_path("stars").read_text(encoding="utf-8")

    def fail(*_: Any, **__: Any) -> str:
        raise StudioError("commit failed")

    content.git.commit = fail  # type: ignore[method-assign]
    with pytest.raises(StudioError):
        save(service, view["id"], summary="never committed")
    assert content.draft_path("stars").read_text(encoding="utf-8") == before


def test_image_list_must_match_the_project(service: StudioService) -> None:
    ready_project(service)
    with pytest.raises(ValidationFailedError):
        save(service, "stars", images=[{"assetRef": "ast_" + "x" * 24, "altText": "a"}])
    view = service.get("stars")
    ref = view["images"][0]["assetRef"]
    with pytest.raises(ValidationFailedError):
        save(
            service,
            "stars",
            images=[{"assetRef": ref, "lead": True}, {"assetRef": ref, "lead": True}],
        )


def test_upload_is_refused_at_a_stale_revision(service: StudioService) -> None:
    view = service.create(CreateRequest(title="STARS"))
    save(service, view["id"], summary="moved on")
    with pytest.raises(ConflictError):
        service.upload_image(view["id"], view["revision"], make_image())
