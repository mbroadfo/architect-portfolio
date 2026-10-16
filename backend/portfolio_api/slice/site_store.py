"""The local public folder (BR3.3, REL-0.1; NFR Design Q2).

Layout under the ``site`` volume::

    releases/<versionId>/   one folder per Publish: rendered pages, fixture derivatives, assets
    releases/empty/         the initial placeholder, "New work is being installed."
    public -> releases/<x>  a relative symbolic link; nginx serves it read-only

Each Publish renders into ``releases/.tmp-<versionId>/`` and renames it into place; a failure
deletes the temporary folder. The ``public`` link is replaced atomically by renaming a new
link over it, so the served folder is always one complete release. The link target is
relative because the API and nginx mount the volume at different paths.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from portfolio_api.slice.errors import SliceError
from portfolio_api.slice.renderer import RenderOutput

EMPTY_RELEASE = "empty"
RELEASE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ASSET_REF = re.compile(r"^ast_[A-Za-z0-9]{16,32}$")
STATIC_ASSET = re.compile(
    r"^/assets/(?P<stem>[a-z0-9-]+)\.(?P<hash>[0-9a-f]{8,64})\.(?P<ext>css|js|woff2)$"
)

EMPTY_INDEX = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>\
<meta name="viewport" content="width=device-width, initial-scale=1"/>\
<title>New work is being installed.</title></head><body><main>\
<p>New work is being installed.</p></main></body></html>"""
EMPTY_404 = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>\
<title>This exhibit isn't on display</title></head><body><main>\
<h1>This exhibit isn&#x27;t on display</h1>\
<p><a href="/work/">All work</a></p></main></body></html>"""

logger = logging.getLogger("portfolio_api.slice.site")


class ReleaseWriteFailedError(SliceError):
    """A release folder could not be written; nothing was published."""


def page_key(path: str) -> str:
    """Map a C9 page path to its object key."""
    if path == "/":
        return "index.html"
    if path.endswith(".html"):
        return path.lstrip("/")
    return f"{path.strip('/')}/index.html"


def _check_name(name: str) -> str:
    if not RELEASE_NAME.match(name):
        raise ReleaseWriteFailedError(f"invalid release name {name!r}")
    return name


class LinkOps(Protocol):
    """The link primitive behind ``public``."""

    def replace_link(self, link: Path, target: str, temporary: Path) -> None:
        """Atomically make ``link`` point at the relative ``target``."""
        ...

    def read_link(self, link: Path) -> str | None:
        """Return the relative target ``link`` points at, or None."""
        ...


class SymlinkOps:
    """Relative symbolic links, replaced atomically by renaming a new link over the old one."""

    def replace_link(self, link: Path, target: str, temporary: Path) -> None:
        if temporary.is_symlink() or temporary.exists():
            temporary.unlink()
        os.symlink(target, temporary, target_is_directory=True)
        os.replace(temporary, link)

    def read_link(self, link: Path) -> str | None:
        return os.readlink(link) if link.is_symlink() else None


class SiteStore:
    """Writes releases and swaps the ``public`` link."""

    def __init__(
        self,
        root: Path,
        fixture_dir: Path,
        static_dir: Path,
        links: LinkOps | None = None,
    ) -> None:
        self.root = root
        self.releases = root / "releases"
        self.public = root / "public"
        self._fixture_dir = fixture_dir
        self._static_dir = static_dir
        self._links: LinkOps = links if links is not None else SymlinkOps()

    def ensure_initial(self) -> None:
        """Create ``releases/empty/`` and point ``public`` at it when nothing is served yet."""
        empty = self.releases / EMPTY_RELEASE
        if not empty.is_dir():
            empty.mkdir(parents=True, exist_ok=True)
            (empty / "index.html").write_text(EMPTY_INDEX, encoding="utf-8")
            (empty / "404.html").write_text(EMPTY_404, encoding="utf-8")
        if self._links.read_link(self.public) is None:
            self.swap_public(EMPTY_RELEASE)

    def current_release(self) -> str | None:
        """Return the release ``public`` points at, or None."""
        target = self._links.read_link(self.public)
        if target is None:
            return None
        path = Path(target)
        return path.name if path.parent.name == "releases" else None

    def has_release(self, name: str) -> bool:
        return RELEASE_NAME.match(name) is not None and (self.releases / name).is_dir()

    def write_release(self, name: str, output: RenderOutput) -> Path:
        """Write a complete release into a temporary folder, then rename it into place."""
        final = self.releases / _check_name(name)
        temporary = self.releases / f".tmp-{name}"
        try:
            if temporary.exists():
                shutil.rmtree(temporary)
            temporary.mkdir(parents=True)
            self._write_pages(temporary, output)
            self._copy_images(temporary, output)
            self._copy_static_assets(temporary, output)
            os.replace(temporary, final)
        except (OSError, ValueError, ReleaseWriteFailedError) as error:
            shutil.rmtree(temporary, ignore_errors=True)
            raise ReleaseWriteFailedError(
                f"release {name} could not be written: {error}"
            ) from error
        return final

    def _write_pages(self, folder: Path, output: RenderOutput) -> None:
        for page in output.pages:
            target = folder / page_key(page.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page.html, encoding="utf-8")

    def _copy_images(self, folder: Path, output: RenderOutput) -> None:
        for image in output.required_images:
            if not ASSET_REF.match(image.asset_ref):
                raise ReleaseWriteFailedError(f"invalid asset reference {image.asset_ref!r}")
            relative = Path(image.asset_ref) / f"{image.variant}.{image.format}"
            source = self._fixture_dir / relative
            if not source.is_file():
                raise ReleaseWriteFailedError(f"no fixture derivative {relative.as_posix()}")
            target = folder / "media" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

    def _copy_static_assets(self, folder: Path, output: RenderOutput) -> None:
        for asset in output.static_assets:
            match = STATIC_ASSET.match(asset)
            if not match:
                raise ReleaseWriteFailedError(f"unexpected static asset {asset!r}")
            source = self._static_dir / f"{match['stem']}.{match['ext']}"
            data = source.read_bytes()
            if not hashlib.sha256(data).hexdigest().startswith(match["hash"]):
                raise ReleaseWriteFailedError(f"static asset {asset} does not match its source")
            target = folder / asset.lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    def swap_public(self, name: str) -> None:
        """Atomically point ``public`` at ``releases/<name>`` (rename a new link over it)."""
        _check_name(name)
        if not (self.releases / name).is_dir():
            raise ReleaseWriteFailedError(f"release {name} does not exist")
        self._links.replace_link(self.public, f"releases/{name}", self.root / f".public-{name}.tmp")

    def delete_release(self, name: str) -> None:
        """Remove a release folder; a missing folder is not an error."""
        if RELEASE_NAME.match(name) and name != EMPTY_RELEASE:
            shutil.rmtree(self.releases / name, ignore_errors=True)

    def prune(self, keep: int, protect: Iterable[str]) -> list[str]:
        """Keep the newest ``keep`` releases plus the protected ones; return what was removed."""
        protected = {EMPTY_RELEASE, *protect}
        current = self.current_release()
        if current:
            protected.add(current)
        candidates = [
            path
            for path in self.releases.iterdir()
            if path.is_dir() and RELEASE_NAME.match(path.name) and path.name not in protected
        ]
        candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        kept_protected = [n for n in protected - {EMPTY_RELEASE} if self.has_release(n)]
        removed = [path.name for path in candidates[max(keep - len(kept_protected), 0) :]]
        for name in removed:
            self.delete_release(name)
        if removed:
            logger.info("pruned old releases", extra={"fields": {"releases": removed}})
        return removed
