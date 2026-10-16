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
    assert [(e["projectId"], e["sourceRevision"]) for e in manifest["exhibits"]] == [("stars", 3)]
    assert manifest["scan"]["passed"] is True
    assert manifest["files"]["work/stars/index.html"]
    assert "snapshot.json" in manifest["scanInputs"]


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


def _flaky_rename(
    monkeypatch: pytest.MonkeyPatch, fail: Any, transient_failures: int = 0
) -> list[str]:
    """Replace Path.rename: fail ``transient_failures`` times, then whenever ``fail(src)``."""
    import portfolio_studio.build as build_module

    monkeypatch.setattr(build_module, "RENAME_BACKOFF_SECONDS", 0.0)
    original = Path.rename
    seen: list[str] = []

    def rename(self: Path, target: Any) -> Path:
        seen.append(self.name)
        if len(seen) <= transient_failures or fail(self.name):
            error = PermissionError(13, "Access is denied")
            error.winerror = 5  # type: ignore[attr-defined]
            raise error
        return original(self, target)

    monkeypatch.setattr(Path, "rename", rename)
    return seen


def test_transient_windows_rename_errors_are_retried(
    service: StudioService, builder: SiteBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LS-4: WinError 5 from a briefly held file is retried, not fatal."""
    ready_project(service, "STARS")
    publish(service, "stars")
    output = default_output(service.store.root)
    builder.build(output)
    seen = _flaky_rename(monkeypatch, lambda name: False, transient_failures=3)
    result = builder.build(output)
    assert result.exhibits == 1 and len(seen) > 3
    assert not [p for p in output.parent.iterdir() if ".previous-" in p.name]


def test_failed_swap_and_failed_restore_keep_the_previous_build(
    service: StudioService, builder: SiteBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LS-4: if neither the new build nor the restore can be renamed, the previous build is
    kept complete under a recoverable name, and the next build puts it back first."""
    ready_project(service, "STARS")
    publish(service, "stars")
    output = default_output(service.store.root)
    builder.build(output)
    before = (output / "work" / "stars" / "index.html").read_text(encoding="utf-8")
    _flaky_rename(monkeypatch, lambda name: name.startswith((".site.staging-", ".site.previous-")))
    with pytest.raises(BuildFailedError, match="kept, complete, at") as raised:
        builder.build(output)
    monkeypatch.undo()
    kept = [p for p in output.parent.iterdir() if p.name.startswith(".site.previous-")]
    assert len(kept) == 1 and str(kept[0]) in str(raised.value)
    assert (kept[0] / "work" / "stars" / "index.html").read_text(encoding="utf-8") == before
    assert not output.exists()
    builder.build(output)  # recovers the previous build first, then replaces it
    assert (output / "work" / "stars" / "index.html").is_file()
    assert not [p for p in output.parent.iterdir() if ".previous-" in p.name]


def test_failed_swap_restores_the_previous_build(
    service: StudioService, builder: SiteBuilder, monkeypatch: pytest.MonkeyPatch
) -> None:
    ready_project(service, "STARS")
    publish(service, "stars")
    output = default_output(service.store.root)
    builder.build(output)
    _flaky_rename(monkeypatch, lambda name: name.startswith(".site.staging-"))
    with pytest.raises(BuildFailedError, match="could not be put in place"):
        builder.build(output)
    monkeypatch.undo()
    assert (output / "work" / "stars" / "index.html").is_file()
