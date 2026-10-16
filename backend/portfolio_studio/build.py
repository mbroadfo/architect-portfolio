"""Generate the public static site from published versions only (ADR-002, ADR-013; FR7.4).

1. Read ``published/<id>.json`` and ``published/featured-order.json``. Drafts are never read.
2. Assemble the C2 snapshot and validate it (closed models).
3. Render it with the shared renderer CLI in public mode.
4. Write a new build next to the output: pages, the static assets (checked against their
   hashed names) and only the derivatives the published versions name, each checked against
   the digest frozen in its published version.
5. Run ``scripts/scan_output.py`` on it with the snapshot, the template vocabulary, the static
   assets and a digest manifest made from the published versions. Any finding fails the build.
6. Swap the new build into place. A failure at any step leaves the previous output untouched;
   the previous build is the rollback.

The output directory must be outside the code repository. An existing output directory is
replaced only when its build manifest (``<out>.build.json``, beside it) shows the Studio
made it, so a mistyped ``--out`` never deletes an unrelated folder.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from portfolio_api.slice.site_store import STATIC_ASSET, page_key

from portfolio_studio import c2
from portfolio_studio.errors import BuildFailedError, StudioError
from portfolio_studio.location import check_outside_code, code_root, is_within
from portfolio_studio.model import PublishedVersion
from portfolio_studio.renderer import RenderFailedError, RenderOutput, StudioRenderer
from portfolio_studio.scan import ScanInputs, run_scan, tree_digests
from portfolio_studio.store import BUILD, ContentStore

MANIFEST_SUFFIX = ".build.json"
SCAN_INPUTS_SUFFIX = ".scan-inputs"
RENAME_ATTEMPTS = 8
RENAME_BACKOFF_SECONDS = 0.05
BUILD_MANIFEST_SCHEMA = "portfolio-site-build/1"

logger = logging.getLogger("portfolio_studio.build")


@dataclass(frozen=True)
class RendererAssets:
    """Where the renderer's static assets and fixed template vocabulary live."""

    static_dir: Path
    vocabulary: tuple[Path, ...]

    @classmethod
    def from_renderer_root(cls, renderer: Path) -> RendererAssets:
        """``assets/`` and ``src/*strings.json`` of a renderer folder (not the preview words)."""
        vocabulary = tuple(
            sorted(
                p
                for p in (renderer / "src").glob("*strings.json")
                if not p.name.startswith("preview")
            )
        )
        return cls(static_dir=renderer / "assets", vocabulary=vocabulary)


@dataclass(frozen=True)
class BuildResult:
    output: Path
    pages: int
    exhibits: int
    files: int
    scan: str


def default_output(content_dir: Path) -> Path:
    return content_dir / BUILD / "site"


class SiteBuilder:
    """Builds, scans and swaps the public site output."""

    def __init__(
        self,
        store: ContentStore,
        renderer: StudioRenderer,
        assets: RendererAssets,
        scanner: Path | None = None,
    ) -> None:
        self.store = store
        self.renderer = renderer
        self.assets = assets
        self.scanner = scanner or code_root() / "scripts" / "scan_output.py"

    def snapshot(self) -> tuple[dict[str, Any], dict[str, str]]:
        """The C2 snapshot and the authorized digest manifest, from published versions only."""
        snapshot, digests, _ = self._from_published()
        return snapshot, digests

    def _from_published(
        self,
    ) -> tuple[dict[str, Any], dict[str, str], list[PublishedVersion]]:
        versions = self.store.published_versions()
        slugs = {v.projectId: str(v.exhibit["slug"]) for v in versions}
        order = [slugs[i] for i in self.store.featured_order().order if i in slugs]
        snapshot = c2.build_snapshot(
            [v.exhibit for v in versions],
            order,
            self.store.settings(),
            c2.PUBLIC_GENERATION,
        )
        digests: dict[str, str] = {}
        for version in versions:
            digests.update(version.derivatives)
        return snapshot, digests, versions

    def build(self, output: Path) -> BuildResult:
        output = self._check_output(output)
        recover_previous(output)
        snapshot, digests, versions = self._from_published()
        try:
            rendered = self.renderer.render(snapshot, "public")
        except RenderFailedError as error:
            raise BuildFailedError(f"the renderer refused the site: {error}") from error
        stamp = time.strftime("%Y%m%d%H%M%S") + f"-{time.perf_counter_ns() % 100000}"
        staging = output.parent / f".{output.name}.staging-{stamp}"
        work = output.parent / f".{output.name}.work-{stamp}"
        try:
            staging.mkdir(parents=True)
            files = self._write(staging, rendered, digests)
            inputs = ScanInputs.write(
                work, snapshot, digests, self.assets.vocabulary, self.assets.static_dir
            )
            scan = run_scan(self.scanner, staging, inputs, "the previous site is unchanged")
            self._swap(staging, output, stamp)
            self._replace_scan_inputs(work, output, stamp)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            shutil.rmtree(work, ignore_errors=True)
            raise
        self._write_manifest(output, snapshot, versions, scan, stamp)
        logger.info("site built", extra={"fields": {"exhibits": len(snapshot["exhibits"])}})
        return BuildResult(
            output=output,
            pages=len(rendered.pages),
            exhibits=len(snapshot["exhibits"]),
            files=files,
            scan=scan,
        )

    # --- checks ------------------------------------------------------------------------------

    def _check_output(self, output: Path) -> Path:
        output = check_outside_code(output, "site output directory")
        content = self.store.root.resolve()
        if output == content or (
            is_within(output, content) and not is_within(output, content / BUILD)
        ):
            raise BuildFailedError("inside the content repository, the output must be under build/")
        if is_within(content, output):
            raise BuildFailedError("the output directory must not contain the content repository")
        if output.exists():
            manifest = manifest_path(output)
            if not output.is_dir() or (any(output.iterdir()) and not manifest.is_file()):
                raise BuildFailedError(
                    f"{output} exists and was not made by the Studio; choose an empty or new folder"
                )
        return output

    # --- writing -----------------------------------------------------------------------------

    def _write(self, folder: Path, rendered: RenderOutput, digests: dict[str, str]) -> int:
        count = 0
        for page in rendered.pages:
            target = folder / page_key(page.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page.html, encoding="utf-8", newline="\n")
            count += 1
        for image in rendered.required_images:
            key = f"media/{image.asset_ref}/{image.variant}.{image.format}"
            expected = digests.get(key)
            if expected is None:
                raise BuildFailedError(f"no published derivative for {key}")
            source = self.store.root / "published" / key
            data = source.read_bytes() if source.is_file() else b""
            if hashlib.sha256(data).hexdigest() != expected:
                raise BuildFailedError(f"{key} is missing or differs from its published digest")
            target = folder / key
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            count += 1
        for asset in rendered.static_assets:
            count += self._copy_static(folder, asset)
        return count

    def _copy_static(self, folder: Path, asset: str) -> int:
        match = STATIC_ASSET.match(asset)
        if not match:
            raise BuildFailedError(f"unexpected static asset {asset}")
        source = self.assets.static_dir / f"{match['stem']}.{match['ext']}"
        try:
            data = source.read_bytes()
        except OSError as error:
            raise BuildFailedError(f"static asset source {source.name} is missing") from error
        if not hashlib.sha256(data).hexdigest().startswith(match["hash"]):
            raise BuildFailedError(f"static asset {asset} does not match its source")
        target = folder / asset.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return 1

    # --- scan --------------------------------------------------------------------------------

    # --- swap --------------------------------------------------------------------------------

    def _swap(self, staging: Path, output: Path, stamp: str) -> None:
        """Replace ``output`` with ``staging``. The previous build is moved aside under a new
        name and deleted only once the new build is in place (security review LS-4)."""
        previous = output.with_name(f".{output.name}.previous-{stamp}")
        had_previous = output.exists()
        if had_previous:
            rename_with_retry(output, previous)
        try:
            rename_with_retry(staging, output)
        except OSError as error:
            if had_previous:
                try:
                    rename_with_retry(previous, output)
                except OSError as restore_error:
                    raise BuildFailedError(
                        f"the new build could not be put in place ({error}) and the previous "
                        f"build could not be moved back ({restore_error}). It is kept, "
                        f"complete, at {previous}: rename it to {output.name} to restore it"
                    ) from restore_error
            raise BuildFailedError(f"the new build could not be put in place: {error}") from error
        remove_aside(output, ".previous-")

    def _replace_scan_inputs(self, work: Path, output: Path, stamp: str) -> None:
        """Keep the scan inputs of the build now in place beside it (``<out>.scan-inputs``)."""
        target = scan_inputs_dir(output)
        if target.exists():
            rename_with_retry(target, target.with_name(f".{target.name}.old-{stamp}"))
        rename_with_retry(work, target)
        remove_aside(target, ".old-")

    def _write_manifest(
        self,
        output: Path,
        snapshot: dict[str, Any],
        versions: list[PublishedVersion],
        scan: str,
        stamp: str,
    ) -> None:
        """Record what this build is: its id, scan result, contents and every file digest."""
        manifest = {
            "schema": BUILD_MANIFEST_SCHEMA,
            "buildId": f"build-{stamp}",
            "builtAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "generation": snapshot["generation"],
            "scan": {"passed": True, "summary": scan},
            "exhibits": [
                {
                    "projectId": v.projectId,
                    "slug": v.exhibit["slug"],
                    "sourceRevision": v.sourceRevision,
                    "publishedAt": v.publishedAt,
                }
                for v in sorted(versions, key=lambda v: v.projectId)
            ],
            "files": tree_digests(output),
            "scanInputs": tree_digests(scan_inputs_dir(output)),
        }
        manifest_path(output).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def rename_with_retry(
    source: Path,
    target: Path,
    attempts: int = RENAME_ATTEMPTS,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Rename, retrying transient Windows sharing errors (an indexer or a virus scanner
    briefly holding a just-written file open) with a short backoff."""
    for attempt in range(attempts):
        try:
            source.rename(target)
            return
        except OSError as error:
            transient = isinstance(error, PermissionError) or getattr(error, "winerror", None) in (
                5,
                32,
                33,
            )
            if not transient or attempt == attempts - 1:
                raise
            sleep(min(RENAME_BACKOFF_SECONDS * 2**attempt, 1.0))


def _aside(path: Path, marker: str) -> list[Path]:
    prefix = f".{path.name}{marker}"
    if not path.parent.is_dir():
        return []
    return sorted(p for p in path.parent.iterdir() if p.name.startswith(prefix) and p.is_dir())


def remove_aside(path: Path, marker: str) -> None:
    """Delete older copies moved aside, only while ``path`` itself is in place."""
    if not path.exists():
        return
    for old in _aside(path, marker):
        shutil.rmtree(old, ignore_errors=True)


def recover_previous(output: Path) -> None:
    """If an interrupted swap left no output but a previous build aside, put it back."""
    if output.exists():
        return
    candidates = _aside(output, ".previous-")
    if candidates:
        rename_with_retry(candidates[-1], output)


def manifest_path(output: Path) -> Path:
    """``<out>.build.json``: written only after a build passed its scan and is in place."""
    return output.with_name(output.name + MANIFEST_SUFFIX)


def scan_inputs_dir(output: Path) -> Path:
    return output.with_name(output.name + SCAN_INPUTS_SUFFIX)


def run_build(builder: SiteBuilder, output: Path) -> BuildResult:
    """Build and convert unexpected failures into BuildFailedError."""
    try:
        return builder.build(output)
    except StudioError:
        raise
    except OSError as error:
        raise BuildFailedError(f"the build could not write its output: {error}") from error
