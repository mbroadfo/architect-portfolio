"""ADR-013: private content never lives in, or points at, the public code repository."""

from __future__ import annotations

from pathlib import Path

import pytest
from portfolio_studio.errors import ContentLocationError
from portfolio_studio.gitrepo import run_git
from portfolio_studio.location import check_content_dir, code_root, default_content_dir


def git_init(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    run_git(path, ["init", "--quiet"])
    return path


def test_content_inside_the_code_repository_is_refused() -> None:
    with pytest.raises(ContentLocationError, match="public code repository"):
        check_content_dir(code_root() / "content", must_exist=False)
    with pytest.raises(ContentLocationError):
        check_content_dir(code_root())


def test_content_inside_another_repository_is_refused(tmp_path: Path) -> None:
    outer = git_init(tmp_path / "outer")
    with pytest.raises(ContentLocationError, match="inside another Git repository"):
        check_content_dir(outer / "content", must_exist=False)


def test_remote_pointing_at_the_public_repository_is_refused(tmp_path: Path) -> None:
    repo = git_init(tmp_path / "content")
    run_git(repo, ["remote", "add", "origin", "git@github.com:mbroadfo/architect-portfolio.git"])
    with pytest.raises(ContentLocationError, match="remote"):
        check_content_dir(repo)


def test_a_private_remote_is_allowed_and_a_plain_folder_is_not(tmp_path: Path) -> None:
    repo = git_init(tmp_path / "content")
    run_git(repo, ["remote", "add", "backup", "https://example.invalid/private.git"])
    assert check_content_dir(repo) == repo.resolve()
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(ContentLocationError, match="not a Git repository"):
        check_content_dir(plain)
    with pytest.raises(ContentLocationError, match="no content repository"):
        check_content_dir(tmp_path / "missing")


def test_default_content_dir_is_beside_the_code_repository() -> None:
    default = default_content_dir()
    assert default.name == "architect-portfolio-content"
    assert code_root() not in default.parents
