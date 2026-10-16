"""Fault injection against the real MongoDB replica set (Codex review R5; AC0.7, AC0.9,
REL-0.1, BR3.1).

Every test uses the real repositories (``mongo.py``) on the single-node replica set, so the
Publish and compensation transactions are real MongoDB multi-document transactions. Faults
are injected *inside* those transactions by wrapping one collection handle: the wrapper
delegates every call to the real collection and only raises at the chosen operation, after
the earlier write in the same transaction has really been applied. The tests then prove the
transaction rolled that earlier write back.

The Publish and restart tests also use a real site folder with real relative symbolic links
(``SymlinkOps``). Hosts that cannot create symbolic links (Windows without Developer Mode)
skip them; ``scripts/verify.py`` therefore runs this suite in a Linux container on the
verification stack's network (``local/it.Dockerfile``), where nothing is skipped, and CI runs
it on Linux.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from portfolio_api.slice.errors import PublishFailedError
from portfolio_api.slice.models import SliceProject, SlicePublishedVersion
from portfolio_api.slice.mongo import (
    PROJECTS,
    VERSIONS,
    DatabaseUnavailableError,
    MongoProjectRepository,
    MongoPublicationRepository,
)
from portfolio_api.slice.publish import PublishService
from portfolio_api.slice.site_store import SiteStore, SymlinkOps
from portfolio_api.slice.snapshot import FixtureImage, SiteConfig
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import OperationFailure

from tests.unit.slice.fakes import FixedRenderer

pytestmark = pytest.mark.integration

T0 = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
ASSET_REF = "ast_FaultInjectionAsset01"
CSS = b"body{margin:0}\n"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00placeholder"
WEBP = b"RIFF\x10\x00\x00\x00WEBPVP8 placeholder"
Document = dict[str, Any]


def _symlinks_supported() -> bool:
    with tempfile.TemporaryDirectory() as directory:
        try:
            os.symlink("target", Path(directory) / "link", target_is_directory=True)
        except OSError:
            return False
    return True


needs_symlinks = pytest.mark.skipif(
    not _symlinks_supported(),
    reason="this host cannot create symbolic links; scripts/verify.py runs this suite in Linux",
)


# --- fault injection: wrappers around the real collections ------------------------------------


class RecordingCollection:
    """Delegates to the real collection and records what each update really changed."""

    def __init__(self, real: Any) -> None:
        self._real = real
        self.updates: list[tuple[int, int]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)

    def update_one(self, *args: Any, **kwargs: Any) -> Any:
        result = self._real.update_one(*args, **kwargs)
        self.updates.append((result.matched_count, result.modified_count))
        return result


class FailingDeleteCollection:
    """Delegates to the real collection, but the delete fails (an injected server error)."""

    def __init__(self, real: Any) -> None:
        self._real = real
        self.delete_attempts = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)

    def delete_one(self, *args: Any, **kwargs: Any) -> Any:
        self.delete_attempts += 1
        raise OperationFailure("injected fault: the version delete failed", code=8000)


class FailingSwapLinks(SymlinkOps):
    """Real symbolic links; the next swap to a non-placeholder release fails once."""

    def __init__(self) -> None:
        self.fail_next = False

    def replace_link(self, link: Path, target: str, temporary: Path) -> None:
        if self.fail_next and target != "releases/empty":
            self.fail_next = False
            raise OSError("injected fault: the public link could not be swapped")
        super().replace_link(link, target, temporary)


# --- helpers --------------------------------------------------------------------------------


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


def _state(database: Database[Document]) -> tuple[list[Document], list[Document]]:
    """Every project and version document, in a stable order."""
    projects = list(database[PROJECTS].find({}).sort("_id", 1))
    versions = list(database[VERSIONS].find({}).sort("_id", 1))
    return projects, versions


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


class Ids:
    def __init__(self, *ids: str) -> None:
        self.ids = list(ids)

    def __call__(self) -> str:
        return self.ids.pop(0)


@pytest.fixture
def projects(database: Database[Document]) -> MongoProjectRepository:
    return MongoProjectRepository(database)


@pytest.fixture
def publications(
    mongo_client: MongoClient[Document], database: Database[Document]
) -> MongoPublicationRepository:
    return MongoPublicationRepository(mongo_client, database)


@pytest.fixture
def fixture_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "fixtures"
    (directory / ASSET_REF).mkdir(parents=True)
    (directory / ASSET_REF / "w480.jpg").write_bytes(JPEG)
    (directory / ASSET_REF / "w480.webp").write_bytes(WEBP)
    manifest = {"assetRef": ASSET_REF, "altText": "Placeholder", "width": 400, "height": 300}
    (directory / "fixture.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "static"
    directory.mkdir()
    (directory / "site.css").write_bytes(CSS)
    return directory


ServiceFactory = Callable[..., PublishService]


@pytest.fixture
def make_service(
    mongo_client: MongoClient[Document],
    database: Database[Document],
    tmp_path: Path,
    fixture_dir: Path,
    static_dir: Path,
) -> ServiceFactory:
    """Build a PublishService on fresh real repositories: a new process, as after a restart."""

    def factory(links: SymlinkOps | None = None, new_id: Callable[[], str] | None = None) -> Any:
        site = SiteStore(tmp_path / "site", fixture_dir, static_dir, links=links or SymlinkOps())
        return PublishService(
            MongoProjectRepository(database),
            MongoPublicationRepository(mongo_client, database),
            FixedRenderer(hashlib.sha256(CSS).hexdigest()[:10]),
            site,
            SiteConfig("Placeholder Owner", "https://github.com/example"),
            FixtureImage.load(fixture_dir),
            clock=Clock(),
            new_id=new_id or Ids("v0001", "v0002", "v0003"),
        )

    return factory


def _served(tmp_path: Path) -> str:
    """The release the real ``public`` symbolic link points at."""
    link = tmp_path / "site" / "public"
    assert link.is_symlink(), "public must be a real symbolic link"
    return Path(os.readlink(link)).name


# --- R5.1: rollback after a partial write inside the Publish transaction ------------------------


def test_r5_ac0_7_a_failed_version_insert_rolls_back_the_pointer_update(
    projects: MongoProjectRepository,
    publications: MongoPublicationRepository,
    database: Database[Document],
) -> None:
    """AC0.7 / REL-0.1 / BR3.1: ``commit_publish`` first moves the project's pointer, then
    inserts the version. A version document that already uses the new id makes the insert
    fail *after* the pointer update succeeded in the same transaction. The transaction must
    roll the update back: the pointer, the revision and the versions collection are unchanged.
    """
    projects.create(_project())
    publications.commit_publish("p1", 1, None, _version("v1"))
    database[VERSIONS].insert_one(
        {
            "_id": "v2",
            "projectId": "another-project",
            "sourceRevision": 7,
            "snapshot": {"marker": "pre-existing document with the colliding id"},
            "publishedAt": T0,
            "sequence": 0,
        }
    )
    before = _state(database)
    recorder = RecordingCollection(publications._projects)
    publications._projects = recorder  # type: ignore[assignment]

    with pytest.raises(DatabaseUnavailableError, match=r"E11000|duplicate key"):
        publications.commit_publish("p1", 1, "v1", _version("v2"))

    assert recorder.updates == [(1, 1)], "the pointer update really ran inside the transaction"
    assert _state(database) == before
    stored = projects.get("p1")
    assert stored is not None
    assert (stored.current_version_id, stored.revision) == ("v1", 1)
    assert publications.current_versions()[0].version_id == "v1"


@needs_symlinks
def test_r5_ac0_9_a_failed_commit_writes_nothing_public(
    make_service: ServiceFactory,
    projects: MongoProjectRepository,
    database: Database[Document],
    tmp_path: Path,
) -> None:
    """AC0.9 / REL-0.1: the same rolled-back commit, through Publish: the new release folder is
    removed, ``public`` still serves the previous release and the database is unchanged."""
    service = make_service(new_id=Ids("v0001", "v0002"))
    projects.create(_project())
    service.publish("p1", 1)
    projects.save("p1", 1, {"summary": "second"}, T0 + timedelta(minutes=5))
    database[VERSIONS].insert_one(
        {
            "_id": "v0002",
            "projectId": "another-project",
            "sourceRevision": 1,
            "snapshot": {},
            "publishedAt": T0,
        }
    )
    before = _state(database)

    with pytest.raises(DatabaseUnavailableError):
        service.publish("p1", 2)

    assert _state(database) == before
    assert _served(tmp_path) == "v0001"
    assert not (tmp_path / "site" / "releases" / "v0002").exists()


# --- R5.2: compensation where the restore succeeds and the delete fails --------------------------


def test_r5_ac0_9_compensation_with_a_failed_delete_rolls_back_and_is_surfaced(
    projects: MongoProjectRepository,
    publications: MongoPublicationRepository,
    mongo_client: MongoClient[Document],
    database: Database[Document],
) -> None:
    """AC0.9 / REL-0.1: compensation restores the previous pointer and then deletes the new
    version, in one transaction. Here the restore really applies and the delete fails. The
    error is raised to the caller (not swallowed), the restore is rolled back, so the state is
    still the consistent "new version is current" state, and a retry converges."""
    projects.create(_project())
    publications.commit_publish("p1", 1, None, _version("v1"))
    publications.commit_publish("p1", 1, "v1", _version("v2"))
    before = _state(database)
    recorder = RecordingCollection(publications._projects)
    failing = FailingDeleteCollection(publications._versions)
    publications._projects = recorder  # type: ignore[assignment]
    publications._versions = failing  # type: ignore[assignment]

    with pytest.raises(DatabaseUnavailableError, match="injected fault"):
        publications.compensate("p1", "v2", "v1")

    assert recorder.updates[0] == (1, 1), "the pointer restore really ran first"
    assert failing.delete_attempts >= 1
    assert _state(database) == before, "the restore was rolled back with the failed delete"
    stored = projects.get("p1")
    assert stored is not None and stored.current_version_id == "v2"

    retry = MongoPublicationRepository(mongo_client, database)
    assert retry.compensate("p1", "v2", "v1") is True
    stored = projects.get("p1")
    assert stored is not None and stored.current_version_id == "v1"
    assert database[VERSIONS].find_one({"_id": "v2"}) is None
    assert retry.compensate("p1", "v2", "v1") is False


# --- R5.3: swap failure after the commit, then a restart reconciles -----------------------------


@needs_symlinks
def test_r5_ac0_9_swap_failure_compensates_and_a_restart_agrees(
    make_service: ServiceFactory,
    projects: MongoProjectRepository,
    database: Database[Document],
    tmp_path: Path,
) -> None:
    """AC0.9 / REL-0.1 / BR3.1: the commit succeeds, the ``public`` swap fails, compensation
    restores the previous version. A fresh service (a restart) reconciles: the database's
    current version and the served release agree."""
    links = FailingSwapLinks()
    service = make_service(links=links, new_id=Ids("v0001", "v0002"))
    projects.create(_project())
    service.publish("p1", 1)
    projects.save("p1", 1, {"summary": "second"}, T0 + timedelta(minutes=5))
    links.fail_next = True

    with pytest.raises(PublishFailedError, match="previous version is kept"):
        service.publish("p1", 2)

    stored = projects.get("p1")
    assert stored is not None and stored.current_version_id == "v0001"
    assert database[VERSIONS].find_one({"_id": "v0002"}) is None
    assert not (tmp_path / "site" / "releases" / "v0002").exists()

    restarted = make_service()
    assert restarted.reconcile() == "v0001"
    current = restarted.site_version()
    assert current is not None and current.version_id == _served(tmp_path) == "v0001"


@needs_symlinks
def test_r5_ac0_9_swap_and_compensation_failures_are_repaired_on_restart(
    make_service: ServiceFactory,
    projects: MongoProjectRepository,
    database: Database[Document],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC0.9 / REL-0.1: the swap fails *and* the compensation's delete fails. Publish raises
    (the failure is surfaced) and logs that compensation failed; the compensation transaction
    rolled back, so the database still names the new version while ``public`` still serves
    the old release. A restart reconciles ``public`` to the database's current version."""
    links = FailingSwapLinks()
    service = make_service(links=links, new_id=Ids("v0001", "v0002"))
    projects.create(_project())
    service.publish("p1", 1)
    projects.save("p1", 1, {"summary": "second"}, T0 + timedelta(minutes=5))
    publications = service._publications
    assert isinstance(publications, MongoPublicationRepository)
    failing = FailingDeleteCollection(publications._versions)
    publications._versions = failing  # type: ignore[assignment]
    links.fail_next = True

    with (
        caplog.at_level(logging.ERROR, logger="portfolio_api.slice.publish"),
        pytest.raises(PublishFailedError),
    ):
        service.publish("p1", 2)
    assert failing.delete_attempts >= 1
    assert any("compensation failed" in record.getMessage() for record in caplog.records)

    stored = projects.get("p1")
    assert stored is not None and stored.current_version_id == "v0002"
    assert database[VERSIONS].find_one({"_id": "v0002"}) is not None
    assert _served(tmp_path) == "v0001", "the swap failed, so the old release is still served"

    restarted = make_service()
    assert restarted.reconcile() == "v0002"
    current = restarted.site_version()
    assert current is not None and current.version_id == _served(tmp_path) == "v0002"
    index = (tmp_path / "site" / "public" / "index.html").read_text(encoding="utf-8")
    assert "Alpha" in index
