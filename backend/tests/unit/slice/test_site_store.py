"""Site folder tests (Step 18; BR3.3, REL-0.1)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from portfolio_api.slice.renderer import RenderedPage, RenderOutput, RequiredImage
from portfolio_api.slice.site_store import (
    EMPTY_RELEASE,
    ReleaseWriteFailedError,
    SiteStore,
    SymlinkOps,
    page_key,
)

from tests.unit.slice.conftest import ASSET_REF, CSS, needs_symlinks

ASSET = f"/assets/site.{hashlib.sha256(CSS).hexdigest()[:10]}.css"


def _output(**overrides: object) -> RenderOutput:
    values: dict[str, object] = {
        "pages": (
            RenderedPage("/", 200, "<html>home</html>"),
            RenderedPage("/work/x", 200, "<html>x</html>"),
        ),
        "required_images": (RequiredImage(ASSET_REF, "w480", "jpg"),),
        "static_assets": (ASSET,),
    }
    values.update(overrides)
    return RenderOutput(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("path", "key"),
    [
        ("/", "index.html"),
        ("/work/", "work/index.html"),
        ("/work/demo", "work/demo/index.html"),
        ("/category/games", "category/games/index.html"),
        ("/404.html", "404.html"),
        ("/category-404.html", "category-404.html"),
    ],
)
def test_page_keys_follow_c9(path: str, key: str) -> None:
    assert page_key(path) == key


def test_initial_state_points_public_at_the_placeholder(site: SiteStore) -> None:
    site.ensure_initial()
    assert site.current_release() == EMPTY_RELEASE
    assert (
        "New work is being installed." in (site.releases / EMPTY_RELEASE / "index.html").read_text()
    )
    site.ensure_initial()
    assert site.current_release() == EMPTY_RELEASE


def test_write_release_and_swap(site: SiteStore) -> None:
    site.ensure_initial()
    folder = site.write_release("v1", _output())
    assert (folder / "work" / "x" / "index.html").read_text() == "<html>x</html>"
    assert (folder / "media" / ASSET_REF / "w480.jpg").is_file()
    assert (folder / ASSET.lstrip("/")).read_bytes() == CSS
    site.swap_public("v1")
    assert site.current_release() == "v1"
    assert not list(site.root.glob(".public-*"))


@pytest.mark.parametrize(
    "overrides",
    [
        {"required_images": (RequiredImage(ASSET_REF, "w960", "jpg"),)},
        {"required_images": (RequiredImage("../escape", "w480", "jpg"),)},
        {"static_assets": ("/assets/site.0000000000.css",)},
        {"static_assets": ("/scripts/evil.js",)},
    ],
)
def test_a_failed_write_leaves_no_folder(site: SiteStore, overrides: dict[str, object]) -> None:
    site.ensure_initial()
    with pytest.raises(ReleaseWriteFailedError):
        site.write_release("v1", _output(**overrides))
    assert sorted(p.name for p in site.releases.iterdir()) == [EMPTY_RELEASE]


def test_release_names_are_checked(site: SiteStore) -> None:
    with pytest.raises(ReleaseWriteFailedError):
        site.write_release("../outside", _output())
    with pytest.raises(ReleaseWriteFailedError):
        site.swap_public("missing")
    assert not site.has_release("../outside")


def test_stale_temporary_folder_is_replaced(site: SiteStore) -> None:
    (site.releases / ".tmp-v1").mkdir(parents=True)
    (site.releases / ".tmp-v1" / "junk.txt").write_text("x")
    folder = site.write_release("v1", _output())
    assert not (folder / "junk.txt").exists()


def test_delete_and_prune(site: SiteStore) -> None:
    site.ensure_initial()
    for index, name in enumerate(["a1", "a2", "a3", "a4", "a5"]):
        folder = site.write_release(name, _output())
        os.utime(folder, (1000 + index, 1000 + index))
    site.swap_public("a2")
    removed = site.prune(3, protect={"a5"})
    remaining = sorted(p.name for p in site.releases.iterdir())
    assert "a2" in remaining and "a5" in remaining and EMPTY_RELEASE in remaining
    assert len(remaining) == 4
    assert sorted(removed) == ["a1", "a3"]
    site.delete_release(EMPTY_RELEASE)
    site.delete_release("a5")
    assert site.has_release(EMPTY_RELEASE)
    assert not site.has_release("a5")


def test_current_release_ignores_foreign_targets(site: SiteStore, tmp_path: Path) -> None:
    site.root.mkdir(parents=True, exist_ok=True)
    assert site.current_release() is None


@needs_symlinks
def test_public_is_a_relative_symbolic_link(
    tmp_path: Path, fixture_dir: Path, static_dir: Path
) -> None:
    """The real link primitive: a relative link, replaced atomically."""
    store = SiteStore(tmp_path / "site", fixture_dir, static_dir, links=SymlinkOps())
    store.ensure_initial()
    store.write_release("v1", _output())
    store.swap_public("v1")
    assert store.public.is_symlink()
    assert os.readlink(store.public) == "releases/v1"
    assert (store.public / "index.html").read_text() == "<html>home</html>"
    store.swap_public(EMPTY_RELEASE)
    assert os.readlink(store.public) == f"releases/{EMPTY_RELEASE}"
