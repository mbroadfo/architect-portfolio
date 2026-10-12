"""C2 snapshot mapping tests (Step 18; BR3.2; functional-spec "Mapping a SliceProject to C2")."""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from portfolio_api.slice.errors import ValidationFailedError
from portfolio_api.slice.models import SliceProject
from portfolio_api.slice.snapshot import (
    FixtureImage,
    SiteConfig,
    build_exhibit,
    build_site_snapshot,
    format_timestamp,
    validate_snapshot,
)

from tests.unit.slice.conftest import ASSET_REF

T = datetime(2026, 10, 11, 12, 30, 45, 123456, tzinfo=UTC)
SITE = SiteConfig("Placeholder Owner", "https://github.com/example")


def _project(slug: str = "placeholder", title: str = "Placeholder") -> SliceProject:
    return SliceProject(
        project_id="p1", title=title, summary="Summary", slug=slug, revision=3, updated_at=T
    )


def test_fixture_manifest_is_loaded(fixture_dir: Path) -> None:
    fixture = FixtureImage.load(fixture_dir)
    assert (fixture.asset_ref, fixture.width, fixture.height) == (ASSET_REF, 400, 300)
    assert fixture.as_c2() == {
        "assetRef": ASSET_REF,
        "altText": "Placeholder illustration",
        "width": 400,
        "height": 300,
    }


def test_exhibit_mapping(fixture_dir: Path) -> None:
    exhibit = build_exhibit(_project(), T, FixtureImage.load(fixture_dir))
    assert exhibit["slug"] == "placeholder"
    assert exhibit["sections"] == {}
    for key in ("images", "attachments", "links", "badges", "publicRepositories"):
        assert exhibit[key] == []
    assert exhibit["featured"] is False
    assert exhibit["publishedAt"] == "2026-10-11T12:30:45Z"
    assert "primaryCategory" not in exhibit and "liveUrl" not in exhibit


def test_site_snapshot_orders_newest_first_and_validates(fixture_dir: Path) -> None:
    fixture = FixtureImage.load(fixture_dir)
    older = build_exhibit(_project("older"), T, fixture)
    newer = build_exhibit(_project("newer"), T + timedelta(minutes=1), fixture)
    snapshot = build_site_snapshot([older, newer], SITE, generation=4)
    assert [e["slug"] for e in snapshot["exhibits"]] == ["newer", "older"]
    assert snapshot["site"] == {
        "ownerName": "Placeholder Owner",
        "githubProfileUrl": "https://github.com/example",
        "contactEmail": None,
    }
    assert (snapshot["featuredOrder"], snapshot["categories"], snapshot["generation"]) == (
        [],
        [],
        4,
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s["exhibits"][0].update(privateNotes="internal"),
        lambda s: s["site"].update(githubProfileUrl="https://gitlab.com/example"),
        lambda s: s["exhibits"][0].update(
            links=[{"kind": "demo", "label": "x", "url": "https://x"}]
        ),
        lambda s: s.update(schemaVersion="2.0"),
        lambda s: s["exhibits"][0]["leadImage"].update(assetRef="not-an-asset"),
    ],
)
def test_snapshots_outside_the_c2_allow_list_are_refused(fixture_dir: Path, mutate: object) -> None:
    """BR3.2: refuse and write nothing."""
    snapshot = build_site_snapshot(
        [build_exhibit(_project(), T, FixtureImage.load(fixture_dir))], SITE, 1
    )
    broken = copy.deepcopy(snapshot)
    mutate(broken)  # type: ignore[operator]
    with pytest.raises(ValidationFailedError, match="not valid against C2"):
        validate_snapshot(broken)


def test_timestamps_are_utc_seconds() -> None:
    eastern = timezone(timedelta(hours=-4))
    assert (
        format_timestamp(datetime(2026, 10, 11, 8, 0, 1, 999, tzinfo=eastern))
        == "2026-10-11T12:00:01Z"
    )
