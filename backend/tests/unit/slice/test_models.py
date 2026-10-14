"""Data-model validation tests (Step 9; AC0.4, BR2.2, BR3.4)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from portfolio_api.slice.models import (
    CreateProjectRequest,
    ProjectView,
    PublishRequest,
    SliceProject,
    SlicePublishedVersion,
    SliceStatus,
    UpdateProjectRequest,
    derive_status,
    propose_slug,
    with_suffix,
)
from pydantic import ValidationError

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


def _project(revision: int = 1) -> SliceProject:
    return SliceProject(
        project_id="p1", title="Title", slug="title", revision=revision, updated_at=NOW
    )


def _version(source_revision: int) -> SlicePublishedVersion:
    return SlicePublishedVersion(
        version_id="v1",
        project_id="p1",
        source_revision=source_revision,
        snapshot={},
        published_at=NOW,
    )


@pytest.mark.parametrize("title", ["", "   ", "x" * 121])
def test_ac0_4_title_must_be_1_to_120_characters(title: str) -> None:
    """AC0.4: an empty or over-long title is refused with the reason."""
    with pytest.raises(ValidationError, match="title"):
        CreateProjectRequest(title=title)


def test_ac0_4_title_boundaries_are_accepted() -> None:
    assert CreateProjectRequest(title="x").title == "x"
    assert CreateProjectRequest(title="x" * 120).title == "x" * 120


def test_ac0_4_summary_over_1200_characters_is_refused() -> None:
    """AC0.4: a summary over 1200 characters is refused."""
    assert len(CreateProjectRequest(title="t", summary="s" * 1200).summary) == 1200
    with pytest.raises(ValidationError, match="1200"):
        CreateProjectRequest(title="t", summary="s" * 1201)
    with pytest.raises(ValidationError):
        UpdateProjectRequest(summary="s" * 1201)


@pytest.mark.parametrize("slug", ["Upper", "two--hyphens", "-lead", "trail-", "sp ace", "a" * 61])
def test_ac0_4_slug_format_is_enforced(slug: str) -> None:
    """AC0.4: slugs are lowercase words joined by single hyphens, at most 60 characters."""
    with pytest.raises(ValidationError):
        UpdateProjectRequest(slug=slug)


def test_request_bodies_are_closed() -> None:
    """C1: request bodies reject unknown fields."""
    with pytest.raises(ValidationError, match="extra"):
        CreateProjectRequest.model_validate({"title": "t", "privateNotes": "x"})
    with pytest.raises(ValidationError, match="extra"):
        PublishRequest.model_validate({"revision": 1, "force": True})


def test_update_changes_only_lists_set_fields() -> None:
    assert UpdateProjectRequest(summary="new").changes() == {"summary": "new"}
    assert UpdateProjectRequest().changes() == {}
    with pytest.raises(ValidationError):
        UpdateProjectRequest(title="")


def test_stored_project_validates_its_title() -> None:
    with pytest.raises(ValidationError):
        SliceProject(project_id="p", title=" ", slug="s", revision=1, updated_at=NOW)


@pytest.mark.parametrize(
    ("title", "slug"),
    [
        ("Hello, World!", "hello-world"),
        ("  Spaces   and_underscores ", "spaces-and-underscores"),
        ("<script>", "script"),
        ("!!!", "project"),
        ("a" * 59 + " b", "a" * 59),
    ],
)
def test_propose_slug(title: str, slug: str) -> None:
    assert propose_slug(title) == slug


def test_with_suffix_stays_within_the_limit() -> None:
    assert with_suffix("demo", 2) == "demo-2"
    assert len(with_suffix("a" * 60, 12)) == 60


def test_status_is_derived_never_stored() -> None:
    """BR3.4: Draft, Published, Changes since last publish."""
    assert derive_status(_project(1), None) is SliceStatus.DRAFT
    assert derive_status(_project(2), _version(2)) is SliceStatus.PUBLISHED
    assert derive_status(_project(3), _version(2)) is SliceStatus.CHANGED


def test_project_view_serializes_camel_case() -> None:
    view = ProjectView.build(_project(2), _version(2)).model_dump(by_alias=True, mode="json")
    assert view["projectId"] == "p1"
    assert view["publishedRevision"] == 2
    assert view["status"] == "Published"
    assert ProjectView.build(_project(), None).published_revision is None
