"""MongoDB repository integration tests (Steps 9 and 11; AC0.3, AC0.4, AC0.6, AC0.7, AC0.9;
BR2.1, BR2.2, BR3.1; REL-0.1). They run against the single-node replica set, so the Publish
transaction is real."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from portfolio_api.slice.errors import (
    NotFoundError,
    SlugTakenError,
    StaleRevisionError,
    ValidationFailedError,
)
from portfolio_api.slice.models import SliceProject, SlicePublishedVersion
from portfolio_api.slice.mongo import (
    PROJECTS,
    VERSIONS,
    MongoProjectRepository,
    MongoPublicationRepository,
)
from pymongo import MongoClient
from pymongo.database import Database

pytestmark = pytest.mark.integration

T0 = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
Document = dict[str, Any]


def _project(project_id: str = "p1", slug: str = "alpha", revision: int = 1) -> SliceProject:
    return SliceProject(
        project_id=project_id,
        title="Alpha",
        summary="",
        slug=slug,
        revision=revision,
        updated_at=T0,
    )


def _version(version_id: str, project_id: str = "p1", revision: int = 1) -> SlicePublishedVersion:
    return SlicePublishedVersion(
        version_id=version_id,
        project_id=project_id,
        source_revision=revision,
        snapshot={"schemaVersion": "1.0", "generation": 1, "exhibits": []},
        published_at=T0 + timedelta(minutes=revision),
    )


@pytest.fixture
def projects(database: Database[Document]) -> MongoProjectRepository:
    return MongoProjectRepository(database)


@pytest.fixture
def publications(
    mongo_client: MongoClient[Document], database: Database[Document]
) -> MongoPublicationRepository:
    return MongoPublicationRepository(mongo_client, database)


# --- Step 9: data model and database behaviour --------------------------------------------------


def test_ac0_4_duplicate_slug_is_refused_by_the_unique_index(
    projects: MongoProjectRepository,
) -> None:
    """AC0.4 / BR2.2: the unique index on slug refuses a duplicate."""
    projects.create(_project("p1", "alpha"))
    with pytest.raises(SlugTakenError):
        projects.create(_project("p2", "alpha"))
    projects.create(_project("p3", "beta"))
    with pytest.raises(SlugTakenError):
        projects.save("p3", 1, {"slug": "alpha"}, T0)
    assert projects.slug_exists("alpha") and not projects.slug_exists("gamma")


def test_round_trip_and_listing(projects: MongoProjectRepository) -> None:
    projects.create(_project("p1", "alpha"))
    projects.create(_project("p2", "beta"))
    projects.save("p2", 1, {"title": "Beta"}, T0 + timedelta(minutes=5))
    stored = projects.get("p1")
    assert stored is not None
    assert (stored.slug, stored.revision, stored.updated_at) == ("alpha", 1, T0)
    assert [p.project_id for p in projects.list()] == ["p2", "p1"]
    assert projects.get("missing") is None


# --- Step 11: repository and data access ---------------------------------------------------


def test_ac0_3_stale_save_gets_stale_revision(
    projects: MongoProjectRepository, database: Database[Document]
) -> None:
    """AC0.3 / BR2.1: compare-and-set on the revision; nothing changes on a conflict."""
    projects.create(_project())
    saved = projects.save("p1", 1, {"title": "Second"}, T0 + timedelta(minutes=1))
    assert (saved.revision, saved.title) == (2, "Second")
    with pytest.raises(StaleRevisionError):
        projects.save("p1", 1, {"title": "Lost update"}, T0 + timedelta(minutes=2))
    document = database[PROJECTS].find_one({"_id": "p1"})
    assert document is not None
    assert (document["title"], document["revision"]) == ("Second", 2)
    with pytest.raises(NotFoundError):
        projects.save("missing", 1, {"title": "x"}, T0)


def test_publish_transaction_compare_and_sets_revision_and_previous_version(
    projects: MongoProjectRepository,
    publications: MongoPublicationRepository,
    database: Database[Document],
) -> None:
    """AC0.6 / AC0.7 / BR3.1: the commit needs the reviewed revision and previous version."""
    projects.create(_project())
    publications.commit_publish("p1", 1, None, _version("v1"))
    stored = projects.get("p1")
    assert stored is not None and stored.current_version_id == "v1"
    assert publications.get_version("v1") == _version("v1")
    projects.save("p1", 1, {"summary": "changed"}, T0)
    with pytest.raises(StaleRevisionError):
        publications.commit_publish("p1", 1, "v1", _version("v-stale"))
    with pytest.raises(StaleRevisionError):
        publications.commit_publish("p1", 2, None, _version("v-wrong-previous", revision=2))
    assert database[VERSIONS].count_documents({}) == 1
    publications.commit_publish("p1", 2, "v1", _version("v2", revision=2))
    assert [v.version_id for v in publications.current_versions()] == ["v2"]


def test_r09_publish_sequence_is_monotonic_and_stored(
    projects: MongoProjectRepository, publications: MongoPublicationRepository
) -> None:
    """R-09: the counter only grows, and each version keeps the sequence it was given."""
    numbers = [publications.next_sequence() for _ in range(3)]
    assert numbers == sorted(numbers) and len(set(numbers)) == 3
    projects.create(_project())
    version = _version("v1").model_copy(update={"sequence": publications.next_sequence()})
    publications.commit_publish("p1", 1, None, version)
    stored = publications.get_version("v1")
    assert stored is not None and stored.sequence == numbers[-1] + 1
    assert publications.current_versions()[0].sequence == stored.sequence


def test_slug_is_fixed_after_the_first_publish(
    projects: MongoProjectRepository, publications: MongoPublicationRepository
) -> None:
    projects.create(_project())
    publications.commit_publish("p1", 1, None, _version("v1"))
    with pytest.raises(ValidationFailedError, match="fixed after the first publish"):
        projects.save("p1", 1, {"slug": "renamed"}, T0)
    assert projects.save("p1", 1, {"title": "Still editable"}, T0).revision == 2


def test_ac0_9_compensation_restores_the_previous_state(
    projects: MongoProjectRepository,
    publications: MongoPublicationRepository,
    database: Database[Document],
) -> None:
    """AC0.9 / REL-0.1: conditional compensation removes the new version, restores the old."""
    projects.create(_project())
    publications.commit_publish("p1", 1, None, _version("v1"))
    publications.commit_publish("p1", 1, "v1", _version("v2"))
    assert publications.compensate("p1", "v2", "v1") is True
    stored = projects.get("p1")
    assert stored is not None and stored.current_version_id == "v1"
    assert database[VERSIONS].find_one({"_id": "v2"}) is None
    assert publications.compensate("p1", "v2", "v1") is False
    assert publications.current_versions()[0].version_id == "v1"


def test_concurrent_publishes_of_the_same_revision_exactly_one_wins(
    projects: MongoProjectRepository,
    publications: MongoPublicationRepository,
    database: Database[Document],
) -> None:
    """BR3.1: concurrent commits of one revision: exactly one succeeds, the rest are stale."""
    for round_number in range(5):
        project_id = f"p{round_number}"
        projects.create(_project(project_id, f"slug-{round_number}"))
        barrier = threading.Barrier(4)
        outcomes: list[str] = []
        lock = threading.Lock()

        def attempt(
            index: int,
            pid: str = project_id,
            gate: threading.Barrier = barrier,
            results: list[str] = outcomes,
            guard: threading.Lock = lock,
        ) -> None:
            gate.wait()
            try:
                publications.commit_publish(pid, 1, None, _version(f"{pid}-v{index}", pid))
                result = "won"
            except StaleRevisionError:
                result = "stale"
            with guard:
                results.append(result)

        threads = [threading.Thread(target=attempt, args=(i,)) for i in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        assert sorted(outcomes) == ["stale", "stale", "stale", "won"]
        assert database[VERSIONS].count_documents({"projectId": project_id}) == 1
