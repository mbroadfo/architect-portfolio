"""The renderer boundary: the shared TypeScript renderer CLI runs as a subprocess (ADR-008).

The C2 snapshot goes in on stdin; a C11 ``RenderOutput`` comes back on stdout and is parsed
and shape-checked by the U0 boundary (``portfolio_api.slice.renderer.parse_output``).
Preview mode passes ``--preview-slug``; every preview page carries the renderer's
"Preview — not public" marking and noindex.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Protocol

from portfolio_api.slice.renderer import (
    RENDER_TIMEOUT_SECONDS,
    Mode,
    RenderFailedError,
    RenderOutput,
    parse_output,
)

__all__ = [
    "CliRenderer",
    "RenderFailedError",
    "RenderOutput",
    "StudioRenderer",
    "cli_path",
    "default_renderer_root",
]


class StudioRenderer(Protocol):
    def render(
        self, snapshot: dict[str, Any], mode: Mode, preview_slug: str | None = None
    ) -> RenderOutput:
        """Render a C2 snapshot; raise RenderFailedError."""
        ...


def default_renderer_root(code_root: Path) -> Path:
    """The shared renderer package in the code repository (ADR-008)."""
    return code_root / "web" / "slice-renderer"


def cli_path(renderer_root: Path) -> Path:
    return renderer_root / "dist" / "cli.cjs"


class CliRenderer:
    """Runs ``node <cli> --mode <mode> [--preview-slug <slug>]`` with the snapshot on stdin."""

    def __init__(self, command: tuple[str, ...], timeout: float = RENDER_TIMEOUT_SECONDS) -> None:
        self._command = command
        self._timeout = timeout

    def render(
        self, snapshot: dict[str, Any], mode: Mode, preview_slug: str | None = None
    ) -> RenderOutput:
        args = [*self._command, "--mode", mode]
        if preview_slug is not None:
            args += ["--preview-slug", preview_slug]
        try:
            completed = subprocess.run(  # noqa: S603 - fixed command, argument list, no shell
                args,
                input=json.dumps(snapshot).encode("utf-8"),
                capture_output=True,
                timeout=self._timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RenderFailedError(f"the renderer could not run: {error}") from error
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip().splitlines()
            raise RenderFailedError(f"the renderer refused the snapshot: {detail[:1]}")
        return parse_output(completed.stdout.decode("utf-8"))
