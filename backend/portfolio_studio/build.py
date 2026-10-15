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
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from portfolio_api.slice.site_store import STATIC_ASSET, page_key

from portfolio_studio import c2
from portfolio_studio.errors import BuildFailedError, StudioError
from portfolio_studio.location import check_outside_code, code_root, is_within
from portfolio_studio.renderer import RenderFailedError, RenderOutput, StudioRenderer
from portfolio_studio.store import BUILD, ContentStore

SCAN_TIMEOUT_SECONDS = 120
MANIFEST_SUFFIX = ".build.json"

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
        versions = self.store.published_versions()
        slugs = {v.projectId: str(v.exhibit["slug"]) for v in versions}
        order = [slugs[i] for i in self.store.featured_order().order if i in slugs]
        snapshot = c2.build_snapshot(
            [v.exhibit for v in versions],
            order,
            self.store.settings(),
            self.store.git.commit_count(),
        )
        digests: dict[str, str] = {}
        for version in versions:
            digests.update(version.derivatives)
        return snapshot, digests

    def build(self, output: Path) -> BuildResult:
        output = self._check_output(output)
        snapshot, digests = self.snapshot()
        try:
            rendered = self.renderer.render(snapshot, "public")
        except RenderFailedError as error:
            raise BuildFailedError(f"the renderer refused the site: {error}") from error
        stamp = time.strftime("%Y%m%d%H%M%S") + f"-{time.perf_counter_ns() % 100000}"
        staging = output.parent / f".{output.name}.staging-{stamp}"
        work = output.parent / f".{output.name}.work-{stamp}"
        try:
            staging.mkdir(parents=True)
            work.mkdir(parents=True)
            files = self._write(staging, rendered, digests)
            scan = self._scan(staging, work, snapshot, digests)
            self._swap(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        finally:
            shutil.rmtree(work, ignore_errors=True)
        self._write_manifest(output, snapshot, files)
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
            manifest = output.with_name(output.name + MANIFEST_SUFFIX)
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

    def _scan(
        self, staging: Path, work: Path, snapshot: dict[str, Any], digests: dict[str, str]
    ) -> str:
        snapshot_file = work / "snapshot.json"
        digests_file = work / "media-digests.json"
        snapshot_file.write_text(json.dumps(snapshot), encoding="utf-8")
        digests_file.write_text(
            json.dumps({"version": 1, "algorithm": "sha256", "derivatives": digests}),
            encoding="utf-8",
        )
        args = [
            sys.executable,
            str(self.scanner),
            "--release",
            str(staging),
            "--snapshot",
            str(snapshot_file),
            "--static-dir",
            str(self.assets.static_dir),
            "--media-digests",
            str(digests_file),
        ]
        for vocabulary in self.assets.vocabulary:
            args += ["--vocabulary", str(vocabulary)]
        try:
            completed = subprocess.run(  # noqa: S603 - this Python, fixed script, no shell
                args,
                capture_output=True,
                text=True,
                timeout=SCAN_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise BuildFailedError(f"the output scan could not run: {error}") from error
        if completed.returncode != 0:
            findings = (completed.stderr or completed.stdout).strip().splitlines()
            raise BuildFailedError(
                "the public-output scan failed; the previous site is unchanged:\n"
                + "\n".join(findings[:20])
            )
        return completed.stdout.strip()

    # --- swap --------------------------------------------------------------------------------

    def _swap(self, staging: Path, output: Path) -> None:
        """Replace ``output`` with ``staging``; on failure put the previous build back."""
        previous = output.with_name(f".{output.name}.previous")
        shutil.rmtree(previous, ignore_errors=True)
        had_previous = output.exists()
        if had_previous:
            output.rename(previous)
        try:
            staging.rename(output)
        except OSError as error:
            if had_previous:
                previous.rename(output)
            raise BuildFailedError(f"the new build could not be put in place: {error}") from error
        shutil.rmtree(previous, ignore_errors=True)

    def _write_manifest(self, output: Path, snapshot: dict[str, Any], files: int) -> None:
        manifest = output.with_name(output.name + MANIFEST_SUFFIX)
        manifest.write_text(
            json.dumps(
                {
                    "builtAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "generation": snapshot["generation"],
                    "exhibits": [e["slug"] for e in snapshot["exhibits"]],
                    "files": files,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def run_build(builder: SiteBuilder, output: Path) -> BuildResult:
    """Build and convert unexpected failures into BuildFailedError."""
    try:
        return builder.build(output)
    except StudioError:
        raise
    except OSError as error:
        raise BuildFailedError(f"the build could not write its output: {error}") from error
