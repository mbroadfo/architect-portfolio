"""The public-output scan (``scripts/scan_output.py``) and the inputs it ran with.

A build keeps the exact scan inputs beside its output (``<out>.scan-inputs/``): the C2
snapshot, the authorized media digests, the renderer's template vocabulary and copies of the
static asset sources. Packaging for Pages re-runs the same scan from those saved inputs, so a
package is checked against what the build was checked against, even if the renderer folder
has changed since.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from portfolio_studio.errors import BuildFailedError

SCAN_TIMEOUT_SECONDS = 120
SNAPSHOT = "snapshot.json"
MEDIA_DIGESTS = "media-digests.json"
VOCABULARY = "vocabulary"
STATIC = "static"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_digests(root: Path) -> dict[str, str]:
    """``relative/posix/path -> sha256`` for every file under ``root``."""
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@dataclass(frozen=True)
class ScanInputs:
    """A folder holding everything ``scan_output.py`` needs."""

    folder: Path

    @classmethod
    def write(
        cls,
        folder: Path,
        snapshot: dict[str, Any],
        digests: dict[str, str],
        vocabulary: Sequence[Path],
        static_dir: Path,
    ) -> ScanInputs:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / SNAPSHOT).write_text(json.dumps(snapshot), encoding="utf-8")
        (folder / MEDIA_DIGESTS).write_text(
            json.dumps({"version": 1, "algorithm": "sha256", "derivatives": digests}),
            encoding="utf-8",
        )
        (folder / VOCABULARY).mkdir()
        for index, path in enumerate(vocabulary):
            shutil.copyfile(path, folder / VOCABULARY / f"{index:02d}-{path.name}")
        (folder / STATIC).mkdir()
        if static_dir.is_dir():
            for path in static_dir.iterdir():
                if path.is_file():
                    shutil.copyfile(path, folder / STATIC / path.name)
        return cls(folder)

    def snapshot(self) -> dict[str, Any]:
        document = json.loads((self.folder / SNAPSHOT).read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise BuildFailedError("the saved scan snapshot is not a JSON object")
        return document

    def argv(self, scanner: Path, release: Path) -> list[str]:
        args = [
            sys.executable,
            str(scanner),
            "--release",
            str(release),
            "--snapshot",
            str(self.folder / SNAPSHOT),
            "--static-dir",
            str(self.folder / STATIC),
            "--media-digests",
            str(self.folder / MEDIA_DIGESTS),
        ]
        for path in sorted((self.folder / VOCABULARY).glob("*.json")):
            args += ["--vocabulary", str(path)]
        return args


def run_scan(scanner: Path, release: Path, inputs: ScanInputs, what: str) -> str:
    """Run the scan; return its summary line or raise BuildFailedError with the findings."""
    try:
        completed = subprocess.run(  # noqa: S603 - this Python, fixed script, no shell
            inputs.argv(scanner, release),
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
            f"the public-output scan failed; {what}:\n" + "\n".join(findings[:20])
        )
    return completed.stdout.strip()
