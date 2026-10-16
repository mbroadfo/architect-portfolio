"""The renderer boundary: the API runs the TypeScript renderer CLI as a subprocess (NFR Design Q1).

The snapshot goes in on stdin as JSON; a C11 ``RenderOutput`` comes back as JSON on stdout.
Python stays authoritative; Node only renders.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from portfolio_api.slice.errors import SliceError

RENDER_TIMEOUT_SECONDS = 30
PAGE_PATH = re.compile(
    r"^/(work/([a-z0-9]+(-[a-z0-9]+)*)?|category/[a-z]+|404\.html|category-404\.html)?$"
)
STATIC_ASSET_PATH = re.compile(r"^/assets/[a-z0-9-]+\.[0-9a-f]{8,64}\.(css|js|woff2)$")
VARIANTS = frozenset({"w480", "w960", "w1600"})
FORMATS = frozenset({"webp", "jpg"})

Mode = Literal["public", "preview"]


class RenderFailedError(SliceError):
    """The renderer refused the snapshot or failed; nothing is written."""


@dataclass(frozen=True)
class RenderedPage:
    path: str
    status: int
    html: str


@dataclass(frozen=True)
class RequiredImage:
    asset_ref: str
    variant: str
    format: str


@dataclass(frozen=True)
class RenderOutput:
    """A parsed and shape-checked C11 RenderOutput."""

    pages: tuple[RenderedPage, ...]
    required_images: tuple[RequiredImage, ...]
    static_assets: tuple[str, ...]


class Renderer(Protocol):
    def render(self, snapshot: dict[str, Any], mode: Mode) -> RenderOutput:
        """Render a C2 snapshot; raise RenderFailedError."""
        ...


def _as_list(document: dict[str, Any], key: str) -> list[Any]:
    value = document.get(key)
    if not isinstance(value, list):
        raise RenderFailedError(f"renderer output has no '{key}' list")
    return value


def parse_output(raw: str) -> RenderOutput:
    """Parse and check the C11 RenderOutput shape; refuse anything unexpected."""
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RenderFailedError("renderer output is not JSON") from error
    if not isinstance(document, dict) or document.get("contractVersion") != "1.0":
        raise RenderFailedError("renderer output is not a C11 1.0 RenderOutput")
    pages = []
    for page in _as_list(document, "pages"):
        path, status, html = page.get("path"), page.get("status"), page.get("html")
        if not isinstance(path, str) or not PAGE_PATH.match(path):
            raise RenderFailedError(f"renderer produced an unexpected page path {path!r}")
        if status not in (200, 404) or not isinstance(html, str):
            raise RenderFailedError(f"renderer produced an invalid page for {path}")
        pages.append(RenderedPage(path=path, status=status, html=html))
    images = []
    for image in _as_list(document, "requiredImages"):
        if image.get("variant") not in VARIANTS or image.get("format") not in FORMATS:
            raise RenderFailedError("renderer requested an unknown image variant")
        images.append(RequiredImage(str(image["assetRef"]), image["variant"], image["format"]))
    assets = _as_list(document, "staticAssets")
    if not all(isinstance(a, str) and STATIC_ASSET_PATH.match(a) for a in assets):
        raise RenderFailedError("renderer listed an unexpected static asset")
    if _as_list(document, "requiredDownloads"):
        raise RenderFailedError("the slice publishes no downloads")
    return RenderOutput(tuple(pages), tuple(images), tuple(assets))


class SubprocessRenderer:
    """Runs ``node dist/cli.cjs --mode <mode>`` with the snapshot on stdin."""

    def __init__(self, command: tuple[str, ...], timeout: float = RENDER_TIMEOUT_SECONDS) -> None:
        self._command = command
        self._timeout = timeout

    def render(self, snapshot: dict[str, Any], mode: Mode) -> RenderOutput:
        try:
            completed = subprocess.run(  # noqa: S603 - fixed command from settings, no shell
                [*self._command, "--mode", mode],
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
