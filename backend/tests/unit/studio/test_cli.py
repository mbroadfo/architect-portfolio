"""The command line: init, import-prototype (never publishes), build and backup."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from portfolio_studio.cli import main
from portfolio_studio.errors import LockedError, ValidationFailedError
from portfolio_studio.gitrepo import run_git
from portfolio_studio.importer import prototype_images, read_prototype_project
from portfolio_studio.locking import ContentLock
from portfolio_studio.store import ContentStore

from .conftest import make_image

DATA_JS = """
window.PORTFOLIO = (() => {
  const projects = [
    { slug: "stars", title: "STARS", category: "astronomy", featured: 1,
      publication: { status: "Published", content: "approved (simulated)" },
      summary: "Fly through the real galaxy.",
      lead: { src: "assets/live/stars.jpg", kind: "live", alt: "The atlas" },
      access: { liveUrl: "https://stars.example/", requirement: "open", phone: "suitable" },
      repos: [{ visibility: "public", licence: null, url: "https://github.com/mbroadfo/stars" }],
      narrative: { inspiration: "Instruments.", challenges: "Speed.", lessons: "" },
      gallery: [
        { src: "assets/live/stars.jpg", kind: "live", alt: "Gallery alt", caption: "Home" },
        { src: "assets/live/stars-phone.jpg", kind: "live", alt: "On a phone", caption: "Phone" },
        { src: "assets/draft/art.jpg", kind: "draft", alt: "Draft art" }
      ] },
    { slug: "risk", title: "Risk", repos: [], gallery: [] }
  ];
  return { find: (slug) => projects.find((p) => p.slug === slug) };
})();
"""

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


@pytest.fixture
def prototype(tmp_path: Path) -> Path:
    folder = tmp_path / "prototype"
    (folder / "assets" / "live").mkdir(parents=True)
    (folder / "data.js").write_text(DATA_JS, encoding="utf-8")
    (folder / "assets" / "live" / "stars.jpg").write_bytes(make_image((1400, 900)))
    (folder / "assets" / "live" / "stars-phone.jpg").write_bytes(make_image((500, 900)))
    return folder


def init(tmp_path: Path) -> Path:
    content = tmp_path / "content"
    assert main(["init", "--content", str(content)]) == 0
    run_git(content, ["config", "user.name", "Test Owner"])
    run_git(content, ["config", "user.email", "owner@example.invalid"])
    return content


def test_init_creates_a_private_repository(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    content = init(tmp_path)
    assert "Never push it to a public remote" in (content / "README.md").read_text("utf-8")
    assert "/build/" in (content / ".gitignore").read_text("utf-8")
    assert not ContentStore(content).git.is_dirty()
    assert main(["init", "--content", str(content)]) == 1
    assert "not empty" in capsys.readouterr().err


@needs_node
def test_import_prototype_creates_a_draft_and_publishes_nothing(
    tmp_path: Path, prototype: Path
) -> None:
    content = init(tmp_path)
    code = main(
        [
            "import-prototype",
            "--content",
            str(content),
            "--project",
            "stars",
            "--prototype",
            str(prototype),
        ]
    )
    assert code == 0
    store = ContentStore(content)
    draft = store.draft("stars")
    assert draft.title == "STARS" and draft.primaryCategory == "astronomy"
    assert draft.sections.inspiration == "Instruments."
    assert draft.sections.designChallenges == "Speed."
    assert draft.liveUrl == "https://stars.xaminisalamini.com"
    assert not draft.liveUrlIncluded and not draft.liveUrlAuthorized
    assert [i.altText for i in draft.images] == ["The atlas", "On a phone"]
    assert [i.caption for i in draft.images] == ["Home", "Phone"]
    assert [i.lead for i in draft.images] == [True, False]
    assert store.published_versions() == []
    assert not (content / "published" / "stars.json").exists()
    assert (
        main(
            [
                "import-prototype",
                "--content",
                str(content),
                "--project",
                "stars",
                "--prototype",
                str(prototype),
            ]
        )
        == 1
    )  # already imported


@needs_node
def test_only_stars_and_baduk_can_be_imported(prototype: Path) -> None:
    with pytest.raises(ValidationFailedError):
        read_prototype_project(prototype, "risk")
    with pytest.raises(SystemExit):
        main(["import-prototype", "--project", "risk"])
    project = read_prototype_project(prototype, "stars")
    assert [i.file.name for i in prototype_images(prototype, project)] == [
        "stars.jpg",
        "stars-phone.jpg",
    ]


def test_build_needs_the_renderer_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    content = init(tmp_path)
    code = main(["build", "--content", str(content), "--renderer-root", str(tmp_path / "none")])
    assert code == 1 and "renderer CLI" in capsys.readouterr().err


def test_dirty_content_repository_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    content = init(tmp_path)
    (content / "stray.txt").write_text("manual edit", encoding="utf-8")
    assert main(["build", "--content", str(content)]) == 1
    assert "uncommitted" in capsys.readouterr().err


def test_backup_writes_a_verified_bundle(tmp_path: Path) -> None:
    content = init(tmp_path)
    bundle = tmp_path / "backups" / "content.bundle"
    assert main(["backup", "--content", str(content), "--to", str(bundle)]) == 0
    assert bundle.is_file()
    clone = tmp_path / "restored"
    run_git(tmp_path, ["clone", "--quiet", str(bundle), str(clone)])
    assert (clone / "studio.json").is_file()
    assert json.loads((clone / "studio.json").read_text("utf-8"))["ownerName"]
    assert main(["backup", "--content", str(content), "--to", str(bundle)]) == 1


def test_serve_site_needs_a_build(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    content = init(tmp_path)
    assert main(["serve-site", "--content", str(content)]) == 1
    assert "run 'build' first" in capsys.readouterr().err


def test_one_studio_process_per_content_repository(tmp_path: Path) -> None:
    content = init(tmp_path)
    with ContentLock(content), pytest.raises(LockedError):
        ContentLock(content).acquire()
    with ContentLock(content):
        pass
