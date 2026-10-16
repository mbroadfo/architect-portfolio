"""Fixtures for the local Studio tests: a real temporary content repository (Git), a fake
renderer, a fake GitHub client and generated images. No test makes a network call."""

from __future__ import annotations

import html
import io
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from portfolio_api.slice.renderer import RenderedPage, RenderOutput, RequiredImage
from portfolio_studio.build import RendererAssets, SiteBuilder
from portfolio_studio.github import RepositoryChecker
from portfolio_studio.model import CreateRequest, SaveRequest
from portfolio_studio.service import StudioService
from portfolio_studio.store import ContentStore

VOCABULARY = {"text": ["Not found", "All work", "Preview — not public"]}


def make_image(
    size: tuple[int, int] = (1200, 800), image_format: str = "JPEG", gps: bool = False
) -> bytes:
    """An image; with ``gps`` it carries EXIF with a GPS block and a camera model."""
    image = Image.new("RGB", size, (40, 90, 160))
    buffer = io.BytesIO()
    if gps:
        exif = Image.Exif()
        exif[0x0110] = "SecretCam 9000"  # Model
        exif[0x8825] = {1: "N", 2: (47.0, 36.0, 12.0), 3: "W", 4: (122.0, 19.0, 55.0)}
        image.save(buffer, image_format, exif=exif.tobytes())
    else:
        image.save(buffer, image_format)
    return buffer.getvalue()


class FakeRenderer:
    """Renders C2 snapshots into minimal pages made only of snapshot and vocabulary values."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.inject: str | None = None

    def render(
        self, snapshot: dict[str, Any], mode: str, preview_slug: str | None = None
    ) -> RenderOutput:
        self.calls.append((mode, preview_slug))
        banner = "<p>Preview — not public</p>" if mode == "preview" else ""
        extra = f"<p>{html.escape(self.inject)}</p>" if self.inject else ""

        def page(body: str) -> str:
            return f"<!DOCTYPE html><html><body>{banner}{body}{extra}</body></html>"

        cards = "".join(
            f'<a href="/work/{e["slug"]}">{html.escape(e["title"])}</a>'
            for e in snapshot["exhibits"]
        )
        pages = [
            RenderedPage("/", 200, page(cards)),
            RenderedPage("/work/", 200, page(f'<a href="/work/">All work</a>{cards}')),
            RenderedPage("/404.html", 404, page("<p>Not found</p>")),
            RenderedPage("/category-404.html", 404, page("<p>Not found</p>")),
        ]
        images: list[RequiredImage] = []
        for exhibit in snapshot["exhibits"]:
            lead = exhibit["leadImage"]
            pages.append(
                RenderedPage(
                    f"/work/{exhibit['slug']}",
                    200,
                    page(
                        f"<h1>{html.escape(exhibit['title'])}</h1>"
                        f'<img src="/media/{lead["assetRef"]}/w480.jpg" '
                        f'alt="{html.escape(lead["altText"])}">'
                    ),
                )
            )
            for image in [lead, *exhibit["images"]]:
                for variant, width in (("w480", 480), ("w960", 960), ("w1600", 1600)):
                    if width <= image["width"] or variant == "w480":
                        for image_format in ("webp", "jpg"):
                            images.append(RequiredImage(image["assetRef"], variant, image_format))
        for category in snapshot["categories"]:
            pages.append(RenderedPage(f"/category/{category['slug']}", 200, page(cards)))
        return RenderOutput(tuple(pages), tuple(images), ())


def fake_fetch(answers: dict[str, tuple[int, dict[str, Any] | None]]) -> Callable[..., Any]:
    """A GitHub fetch that answers from ``answers`` (owner/name -> status, body)."""

    def fetch(url: str) -> tuple[int, bytes]:
        key = url.removeprefix("https://api.github.com/repos/")
        if key not in answers:
            raise OSError("no network in tests")
        status, body = answers[key]
        return status, json.dumps(body).encode() if body is not None else b""

    return fetch


PUBLIC_REPO = {
    "full_name": "mbroadfo/stars",
    "private": False,
    "visibility": "public",
    "license": None,
}


@pytest.fixture
def content(tmp_path: Path) -> ContentStore:
    store = ContentStore(tmp_path / "content")
    store.root.mkdir()
    store.git.init()
    from portfolio_studio.gitrepo import run_git

    run_git(store.root, ["config", "user.name", "Test Owner"])
    run_git(store.root, ["config", "user.email", "owner@example.invalid"])
    store.initialize()
    store.git.commit(
        ["README.md", ".gitignore", "studio.json", "projects", "published", "withdrawn"],
        "Create the private content repository",
    )
    return store


@pytest.fixture
def renderer() -> FakeRenderer:
    return FakeRenderer()


@pytest.fixture
def github() -> dict[str, tuple[int, dict[str, Any] | None]]:
    return {"mbroadfo/stars": (200, dict(PUBLIC_REPO))}


@pytest.fixture
def service(
    content: ContentStore,
    renderer: FakeRenderer,
    github: dict[str, tuple[int, dict[str, Any] | None]],
) -> StudioService:
    return StudioService(content, renderer, RepositoryChecker(fetch=fake_fetch(github)))


@pytest.fixture
def assets(tmp_path: Path) -> RendererAssets:
    static = tmp_path / "renderer-assets"
    static.mkdir()
    vocabulary = tmp_path / "template-strings.json"
    vocabulary.write_text(json.dumps(VOCABULARY), encoding="utf-8")
    return RendererAssets(static_dir=static, vocabulary=(vocabulary,))


@pytest.fixture
def builder(content: ContentStore, renderer: FakeRenderer, assets: RendererAssets) -> SiteBuilder:
    return SiteBuilder(content, renderer, assets)


def ready_project(service: StudioService, title: str = "STARS", **changes: Any) -> dict[str, Any]:
    """A project with a lead image with alt text: nothing blocks its publication."""
    view = service.create(CreateRequest(title=title))
    view = service.upload_image(view["id"], view["revision"], make_image())
    image = view["images"][0]
    fields: dict[str, Any] = {
        "revision": view["revision"],
        "title": title,
        "slug": view["slug"],
        "summary": f"{title} summary",
        "sections": {"inspiration": f"{title} inspiration"},
        "primaryCategory": "astronomy",
        "images": [{"assetRef": image["assetRef"], "altText": f"{title} lead", "lead": True}],
    }
    fields.update(changes)
    return service.save(view["id"], SaveRequest.model_validate(fields))


def publish(service: StudioService, project_id: str) -> dict[str, Any]:
    from portfolio_studio.model import PublishRequest

    review = service.prepare_review(project_id)
    assert review["reviewId"], review["blockers"]
    return service.publish(
        project_id, PublishRequest(revision=review["revision"], reviewId=review["reviewId"])
    )
