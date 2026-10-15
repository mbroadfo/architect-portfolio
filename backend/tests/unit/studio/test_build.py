"""The site build reads published versions only, scans the output and swaps atomically
(ADR-002, ADR-013; FR7.4, FR8.2, NFR2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from portfolio_studio.build import SiteBuilder, default_output, run_build
from portfolio_studio.errors import BuildFailedError, ContentLocationError
from portfolio_studio.location import code_root
from portfolio_studio.service import StudioService

from .conftest import publish, ready_project
from .test_service import save


def site_text(output: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in output.rglob("*.html"))


def test_build_contains_published_versions_only(
    service: StudioService, builder: SiteBuilder
) -> None:
    """NFR2/FR7.4: a draft-only change and an unpublished project never reach the site."""
    ready_project(service, "STARS")
    publish(service, "stars")
    save(service, "stars", title="STARS draft-only title")
    ready_project(service, "Unpublished Secret")
    output = default_output(service.store.root)
    result = builder.build(output)
    text = site_text(output)
    assert "STARS" in text
    assert "draft-only" not in text and "Unpublished Secret" not in text
    assert result.exhibits == 1 and "OK" in result.scan
    assert (output / "work" / "stars" / "index.html").is_file()
    media = sorted(p.relative_to(output).as_posix() for p in (output / "media").rglob("*.*"))
    published = service.store.published("stars")
    assert published is not None
    assert media == sorted(published.derivatives)
    assert not any("originals" in p.as_posix() for p in output.rglob("*"))
    manifest = json.loads(output.with_name("site.build.json").read_text(encoding="utf-8"))
    assert manifest["exhibits"] == ["stars"]


def test_take_down_removes_the_exhibit_and_media_from_the_next_build(
    service: StudioService, builder: SiteBuilder
) -> None:
    """FR8.2: after take-down the page, card and images are gone from the output."""
    ready_project(service, "STARS")
    ready_project(service, "Baduk")
    publish(service, "stars")
    publish(service, "baduk")
    output = default_output(service.store.root)
    builder.build(output)
    assert (output / "work" / "baduk" / "index.html").is_file()
    service.take_down("baduk", "Baduk")
    builder.build(output)
    assert not (output / "work" / "baduk").exists()
    assert "Baduk" not in site_text(output)
    published = service.store.published("stars")
    assert published is not None
    refs = {key.split("/")[1] for key in published.derivatives}
    assert {p.name for p in (output / "media").iterdir()} == refs


def test_scan_failure_keeps_the_previous_output(
    service: StudioService, builder: SiteBuilder, renderer: Any
) -> None:
    """A scan finding fails the build; the previous site is left untouched."""
    ready_project(service, "STARS")
    publish(service, "stars")
    output = default_output(service.store.root)
    builder.build(output)
    before = (output / "index.html").read_text(encoding="utf-8")
    renderer.inject = "Private draft notes"
    with pytest.raises(BuildFailedError, match="scan failed"):
        builder.build(output)
    assert (output / "index.html").read_text(encoding="utf-8") == before
    assert not [p for p in output.parent.iterdir() if ".staging-" in p.name or ".work-" in p.name]


def test_tampered_derivative_fails_the_build(service: StudioService, builder: SiteBuilder) -> None:
    """A published derivative must match the digest frozen in its published version."""
    ready_project(service, "STARS")
    publish(service, "stars")
    published = service.store.published("stars")
    assert published is not None
    key = next(iter(published.derivatives))
    (service.store.root / "published" / key).write_bytes(b"changed")
    with pytest.raises(BuildFailedError, match="differs"):
        builder.build(default_output(service.store.root))


def test_output_inside_the_code_repository_is_refused(builder: SiteBuilder) -> None:
    with pytest.raises(ContentLocationError):
        builder.build(code_root() / "site-output")


def test_unrelated_existing_folder_is_never_replaced(
    service: StudioService, builder: SiteBuilder, tmp_path: Path
) -> None:
    folder = tmp_path / "important"
    folder.mkdir()
    (folder / "keep.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(BuildFailedError, match="not made by the Studio"):
        builder.build(folder)
    assert (folder / "keep.txt").read_text(encoding="utf-8") == "mine"
    with pytest.raises(BuildFailedError):
        builder.build(service.store.root / "projects")


def test_renderer_failure_fails_the_build(
    service: StudioService, builder: SiteBuilder, renderer: Any
) -> None:
    from portfolio_studio.renderer import RenderFailedError

    def broken(*_: Any, **__: Any) -> Any:
        raise RenderFailedError("refused")

    renderer.render = broken
    with pytest.raises(BuildFailedError, match="renderer"):
        run_build(builder, default_output(service.store.root))


def test_empty_site_builds(builder: SiteBuilder, service: StudioService) -> None:
    result = builder.build(default_output(service.store.root))
    assert result.exhibits == 0
