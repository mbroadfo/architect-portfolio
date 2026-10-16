"""MongoDB repositories (Step 8 and Step 10; BR2.1, BR2.2, BR3.1; REL-0.1).

MongoDB runs as a single-node replica set so Publish can use a multi-document transaction.
Collections: ``slice_projects`` (unique index on ``slug``) and ``slice_published_versions``.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from pymongo import ASCENDING, MongoClient, ReturnDocument
from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from portfolio_api.slice.errors import (
    NotFoundError,
    SliceError,
    SlugTakenError,
    StaleRevisionError,
    ValidationFailedError,
)
from portfolio_api.slice.models import SliceProject, SlicePublishedVersion

PROJECTS = "slice_projects"
VERSIONS = "slice_published_versions"
COUNTERS = "slice_counters"
PUBLISH_SEQUENCE = "publish_sequence"
SERVER_SELECTION_TIMEOUT_MS = 5000

Document = dict[str, Any]


class DatabaseUnavailableError(SliceError):
    """MongoDB could not be reached or refused the operation."""


def connect(uri: str) -> MongoClient[Document]:
    """Create a client for the replica set, with UTC-aware datetimes."""
    return MongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=SERVER_SELECTION_TIMEOUT_MS)


def ensure_indexes(database: Database[Document]) -> None:
    """Create the slug uniqueness index (BR2.2) and the version lookup index."""
    database[PROJECTS].create_index([("slug", ASCENDING)], unique=True, name="slug_unique")
    database[VERSIONS].create_index([("projectId", ASCENDING)], name="project_lookup")


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _project_from(document: Document) -> SliceProject:
    return SliceProject(
        project_id=document["_id"],
        title=document["title"],
        summary=document.get("summary", ""),
        slug=document["slug"],
        revision=document["revision"],
        updated_at=_utc(document["updatedAt"]),
        current_version_id=document.get("currentVersionId"),
    )


def _version_from(document: Document) -> SlicePublishedVersion:
    return SlicePublishedVersion(
        version_id=document["_id"],
        project_id=document["projectId"],
        source_revision=document["sourceRevision"],
        snapshot=document["snapshot"],
        published_at=_utc(document["publishedAt"]),
        sequence=int(document.get("sequence", 0)),
    )


class MongoProjectRepository:
    """ProjectRepository on MongoDB."""

    def __init__(self, database: Database[Document]) -> None:
        self._projects: Collection[Document] = database[PROJECTS]

    def create(self, project: SliceProject) -> None:
        try:
            self._projects.insert_one(
                {
                    "_id": project.project_id,
                    "title": project.title,
                    "summary": project.summary,
                    "slug": project.slug,
                    "revision": project.revision,
                    "updatedAt": project.updated_at,
                    "currentVersionId": project.current_version_id,
                }
            )
        except DuplicateKeyError as error:
            raise SlugTakenError(f"the slug '{project.slug}' is already in use") from error

    def get(self, project_id: str) -> SliceProject | None:
        document = self._projects.find_one({"_id": project_id})
        return _project_from(document) if document else None

    def list(self) -> list[SliceProject]:
        cursor = self._projects.find().sort("updatedAt", -1)
        return [_project_from(document) for document in cursor]

    def slug_exists(self, slug: str) -> bool:
        return self._projects.count_documents({"slug": slug}, limit=1) > 0

    def save(
        self,
        project_id: str,
        base_revision: int,
        changes: Mapping[str, str],
        updated_at: datetime,
    ) -> SliceProject:
        condition: Document = {"_id": project_id, "revision": base_revision}
        if "slug" in changes:
            condition["currentVersionId"] = None
        try:
            document = self._projects.find_one_and_update(
                condition,
                {"$set": {**changes, "updatedAt": updated_at}, "$inc": {"revision": 1}},
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError as error:
            raise SlugTakenError(f"the slug '{changes.get('slug')}' is already in use") from error
        if document is not None:
            return _project_from(document)
        current = self.get(project_id)
        if current is None:
            raise NotFoundError(f"project {project_id} not found")
        if current.revision != base_revision:
            raise StaleRevisionError(
                f"project {project_id} is at revision {current.revision}, not {base_revision}"
            )
        raise ValidationFailedError("the slug is fixed after the first publish")


class MongoPublicationRepository:
    """PublicationRepository on MongoDB, using multi-document transactions."""

    def __init__(self, client: MongoClient[Document], database: Database[Document]) -> None:
        self._client = client
        self._projects: Collection[Document] = database[PROJECTS]
        self._versions: Collection[Document] = database[VERSIONS]
        self._counters: Collection[Document] = database[COUNTERS]

    def next_sequence(self) -> int:
        """Atomically increment the publish counter; values never repeat or go backwards."""
        try:
            document = self._counters.find_one_and_update(
                {"_id": PUBLISH_SEQUENCE},
                {"$inc": {"value": 1}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as error:
            raise DatabaseUnavailableError(f"cannot take a publish sequence: {error}") from error
        return int(document["value"]) if document else 1

    def _run_transaction(self, operation: Any) -> Any:
        try:
            with self._client.start_session() as session:
                return session.with_transaction(
                    operation,
                    read_concern=ReadConcern("snapshot"),
                    write_concern=WriteConcern("majority"),
                )
        except SliceError:
            raise
        except PyMongoError as error:
            raise DatabaseUnavailableError(f"database transaction failed: {error}") from error

    def commit_publish(
        self,
        project_id: str,
        revision: int,
        previous_version_id: str | None,
        version: SlicePublishedVersion,
    ) -> None:
        def operation(session: ClientSession) -> None:
            result = self._projects.update_one(
                {"_id": project_id, "revision": revision, "currentVersionId": previous_version_id},
                {"$set": {"currentVersionId": version.version_id}},
                session=session,
            )
            if result.matched_count != 1:
                raise StaleRevisionError(
                    f"project {project_id} is no longer at revision {revision}; nothing published"
                )
            self._versions.insert_one(
                {
                    "_id": version.version_id,
                    "projectId": version.project_id,
                    "sourceRevision": version.source_revision,
                    "snapshot": version.snapshot,
                    "publishedAt": version.published_at,
                    "sequence": version.sequence,
                },
                session=session,
            )

        self._run_transaction(operation)

    def compensate(self, project_id: str, version_id: str, previous_version_id: str | None) -> bool:
        def operation(session: ClientSession) -> bool:
            result = self._projects.update_one(
                {"_id": project_id, "currentVersionId": version_id},
                {"$set": {"currentVersionId": previous_version_id}},
                session=session,
            )
            if result.matched_count != 1:
                return False
            self._versions.delete_one({"_id": version_id}, session=session)
            return True

        return bool(self._run_transaction(operation))

    def get_version(self, version_id: str) -> SlicePublishedVersion | None:
        document = self._versions.find_one({"_id": version_id})
        return _version_from(document) if document else None

    def current_versions(self) -> list[SlicePublishedVersion]:
        ids = [
            document["currentVersionId"]
            for document in self._projects.find(
                {"currentVersionId": {"$ne": None}}, {"currentVersionId": 1}
            )
        ]
        if not ids:
            return []
        return [_version_from(d) for d in self._versions.find({"_id": {"$in": ids}})]
