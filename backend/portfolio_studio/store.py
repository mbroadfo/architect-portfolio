"""The private content repository on disk (ADR-013).

Layout::

    README.md                         private; never push to a public remote
    .gitignore                        build output and the Studio lock
    studio.json                       the public C2 ``site`` block (owner name, GitHub profile)
    projects/<id>/project.json        the draft
    projects/<id>/originals/<ref>.<ext>             private original uploads, never published
    projects/<id>/derived/<ref>/<variant>.<fmt>     sanitized derivatives (WebP and JPEG)
    published/<id>.json               the frozen published version (C2 exhibit + digests)
    published/media/<ref>/<variant>.<fmt>           the derivatives a published version uses
    published/featured-order.json     the published carousel order (project ids)
    withdrawn/<id>.json               the take-down record
    build/                            generated site output (ignored by Git)

Files are written to a temporary name and renamed into place. Each operation then commits the
paths it touched; if the commit fails, those paths are restored from the last commit.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from portfolio_studio.errors import NotFoundError, StudioError, ValidationFailedError
from portfolio_studio.gitrepo import ContentRepo
from portfolio_studio.model import (
    ASSET_REF_PATTERN,
    ID_PATTERN,
    Draft,
    FeaturedOrder,
    PublishedVersion,
    SiteSettings,
    Withdrawn,
)

PROJECTS = "projects"
PUBLISHED = "published"
PUBLISHED_MEDIA = "published/media"
WITHDRAWN = "withdrawn"
FEATURED_ORDER = "published/featured-order.json"
SETTINGS = "studio.json"
BUILD = "build"
ID_REGEX = re.compile(ID_PATTERN)
ASSET_REGEX = re.compile(ASSET_REF_PATTERN)
DERIVATIVE_NAME = re.compile(r"^w(480|960|1600)\.(webp|jpg)$")

README = """# Architect Portfolio — private content

This repository is **private**. It holds the Studio's drafts, the original image uploads
(which may contain camera metadata such as GPS location), sanitized derivatives and the
frozen published versions.

- **Never push it to a public remote**, and never copy it into the public code repository
  (`github.com/mbroadfo/architect-portfolio`). The Studio refuses to run on a content
  directory inside the code repository or with a remote pointing at it.
- A private remote for off-machine backup needs Michael's explicit authorization first.
- Every save, upload, publish and take-down is a commit: `git log` is the activity log.
- Back up with `python -m portfolio_studio backup --content <this dir> --to <file>.bundle`.
- `build/` holds the generated public site and is not committed.

Layout: see `docs/LOCAL-STUDIO.md` in the code repository.
"""

GITIGNORE = """# Generated public site output and its work files
/build/
# The Studio's single-writer lock
/.studio.lock
# Temporary files from interrupted writes
*.tmp
"""

DEFAULT_SETTINGS = SiteSettings(
    ownerName="Michael Broadfoot", githubProfileUrl="https://github.com/mbroadfo"
)


def check_id(project_id: str) -> str:
    if not ID_REGEX.match(project_id) or len(project_id) > 60:
        raise NotFoundError("no such project")
    return project_id


def check_asset_ref(asset_ref: str) -> str:
    if not ASSET_REGEX.match(asset_ref):
        raise NotFoundError("no such image")
    return asset_ref


def write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def write_json_atomic(path: Path, document: Any) -> None:
    text = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    write_bytes_atomic(path, text.encode("utf-8"))


def read_model[ModelT: BaseModel](path: Path, model: type[ModelT]) -> ModelT:
    try:
        return model.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise ValidationFailedError(f"{path.name} is unreadable or invalid: {error}") from error


class ContentStore:
    """Reads and writes the content repository's files."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.git = ContentRepo(root)

    # --- paths -----------------------------------------------------------------------------

    def project_dir(self, project_id: str) -> Path:
        return self.root / PROJECTS / check_id(project_id)

    def draft_path(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "project.json"

    def derived_dir(self, project_id: str, asset_ref: str) -> Path:
        return self.project_dir(project_id) / "derived" / check_asset_ref(asset_ref)

    def original_path(self, project_id: str, file_name: str) -> Path:
        return self.project_dir(project_id) / "originals" / file_name

    def published_path(self, project_id: str) -> Path:
        return self.root / PUBLISHED / f"{check_id(project_id)}.json"

    def published_media_dir(self, asset_ref: str) -> Path:
        return self.root / PUBLISHED_MEDIA / check_asset_ref(asset_ref)

    def withdrawn_path(self, project_id: str) -> Path:
        return self.root / WITHDRAWN / f"{check_id(project_id)}.json"

    # --- reads -----------------------------------------------------------------------------

    def settings(self) -> SiteSettings:
        path = self.root / SETTINGS
        return read_model(path, SiteSettings) if path.is_file() else DEFAULT_SETTINGS

    def project_ids(self) -> list[str]:
        folder = self.root / PROJECTS
        if not folder.is_dir():
            return []
        return sorted(
            path.name
            for path in folder.iterdir()
            if path.is_dir() and ID_REGEX.match(path.name) and (path / "project.json").is_file()
        )

    def draft(self, project_id: str) -> Draft:
        path = self.draft_path(project_id)
        if not path.is_file():
            raise NotFoundError("no such project")
        return read_model(path, Draft)

    def published(self, project_id: str) -> PublishedVersion | None:
        path = self.published_path(project_id)
        return read_model(path, PublishedVersion) if path.is_file() else None

    def published_versions(self) -> list[PublishedVersion]:
        """Every frozen published version (the only input to the site build, ADR-002)."""
        folder = self.root / PUBLISHED
        if not folder.is_dir():
            return []
        versions = []
        for path in sorted(folder.glob("*.json")):
            if path.name == Path(FEATURED_ORDER).name:
                continue
            if not ID_REGEX.match(path.stem):
                raise ValidationFailedError(f"unexpected file published/{path.name}")
            version = read_model(path, PublishedVersion)
            if version.projectId != path.stem:
                raise ValidationFailedError(f"published/{path.name} names another project")
            versions.append(version)
        return versions

    def withdrawn(self, project_id: str) -> Withdrawn | None:
        path = self.withdrawn_path(project_id)
        return read_model(path, Withdrawn) if path.is_file() else None

    def featured_order(self) -> FeaturedOrder:
        path = self.root / FEATURED_ORDER
        return read_model(path, FeaturedOrder) if path.is_file() else FeaturedOrder()

    def derivative_file(self, asset_ref: str, name: str) -> Path | None:
        """Find a derivative by asset reference (drafts first, then published media)."""
        if not DERIVATIVE_NAME.match(name):
            return None
        check_asset_ref(asset_ref)
        for project_id in self.project_ids():
            candidate = self.project_dir(project_id) / "derived" / asset_ref / name
            if candidate.is_file():
                return candidate
        candidate = self.published_media_dir(asset_ref) / name
        return candidate if candidate.is_file() else None

    # --- writes ----------------------------------------------------------------------------

    def write_draft(self, draft: Draft) -> None:
        write_json_atomic(self.draft_path(draft.id), draft.to_json())

    def write_published(self, version: PublishedVersion) -> None:
        write_json_atomic(self.published_path(version.projectId), version.to_json())

    def write_withdrawn(self, record: Withdrawn) -> None:
        write_json_atomic(self.withdrawn_path(record.projectId), record.model_dump())

    def write_featured_order(self, order: FeaturedOrder) -> None:
        write_json_atomic(self.root / FEATURED_ORDER, order.model_dump())

    def remove(self, path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    @contextmanager
    def transaction(self, paths: Sequence[str], message: str) -> Iterator[Callable[[], str]]:
        """Run file writes, then commit ``paths``; on any failure restore them.

        Usage: ``with store.transaction([...], "Save STARS") as commit: ...; sha = commit()``.
        The body must call ``commit()`` once its writes are complete.
        """
        committed: list[str] = []

        def commit() -> str:
            sha = self.git.commit(paths, message)
            committed.append(sha)
            return sha

        try:
            yield commit
        except BaseException:
            if not committed:
                self.git.restore(paths)
            raise
        if not committed:
            self.git.restore(paths)
            raise StudioError("internal error: the operation did not commit")

    def initialize(self) -> None:
        """Write the README, .gitignore and settings of a new content repository."""
        (self.root / README_NAME).write_text(README, encoding="utf-8", newline="\n")
        (self.root / ".gitignore").write_text(GITIGNORE, encoding="utf-8", newline="\n")
        write_json_atomic(self.root / SETTINGS, DEFAULT_SETTINGS.model_dump())
        for folder in (PROJECTS, PUBLISHED, WITHDRAWN):
            (self.root / folder).mkdir(parents=True, exist_ok=True)
            (self.root / folder / ".gitkeep").write_text("", encoding="utf-8")


README_NAME = "README.md"
