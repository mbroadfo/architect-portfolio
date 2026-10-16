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


PUBLIC_HTTPS = "https://github.com/mbroadfo/architect-portfolio.git"


def test_remote_pointing_at_the_public_repository_is_refused(tmp_path: Path) -> None:
    repo = git_init(tmp_path / "content")
    run_git(repo, ["remote", "add", "origin", "git@github.com:mbroadfo/architect-portfolio.git"])
    with pytest.raises(ContentLocationError, match="remote"):
        check_content_dir(repo)


def test_nested_repository_inside_a_public_clone_is_refused(tmp_path: Path) -> None:
    """LS-1: a content repository of its own, nested inside a repo with the public remote."""
    outer = git_init(tmp_path / "outer")
    run_git(outer, ["remote", "add", "origin", PUBLIC_HTTPS])
    inner = git_init(outer / "inner")
    with pytest.raises(ContentLocationError, match="public code repository"):
        check_content_dir(inner)
    with pytest.raises(ContentLocationError, match="public code repository"):
        check_content_dir(outer / "new-content", must_exist=False)


def test_nested_repository_inside_any_repository_is_refused(tmp_path: Path) -> None:
    """LS-1: nested inside any other work tree, whatever its remotes."""
    outer = git_init(tmp_path / "outer")
    inner = git_init(outer / "deeper" / "content")
    with pytest.raises(ContentLocationError, match="inside another Git repository"):
        check_content_dir(inner)


def test_separate_clone_of_the_public_repository_is_refused(tmp_path: Path) -> None:
    """LS-1: a second checkout of the public repository is not one of code_roots()."""
    clone = git_init(tmp_path / "another-checkout")
    run_git(clone, ["remote", "add", "upstream", "https://github.com/mbroadfo/architect-portfolio"])
    (clone / "content").mkdir()
    with pytest.raises(ContentLocationError, match="public code repository"):
        check_content_dir(clone / "content", must_exist=False)


def test_ssh_host_alias_is_refused(tmp_path: Path) -> None:
    """LS-1: an SSH alias host still names mbroadfo/architect-portfolio."""
    repo = git_init(tmp_path / "content")
    run_git(repo, ["remote", "add", "origin", "git@gh-personal:mbroadfo/architect-portfolio.git"])
    with pytest.raises(ContentLocationError, match="gh-personal"):
        check_content_dir(repo)
    other = git_init(tmp_path / "content2")
    run_git(other, ["remote", "add", "backup", "ssh://git@backup.example:2222/m/private.git"])
    run_git(other, ["remote", "set-url", "--add", "--push", "backup", PUBLIC_HTTPS])
    with pytest.raises(ContentLocationError, match="remote"):
        check_content_dir(other)


def test_insteadof_rewrite_is_resolved(tmp_path: Path) -> None:
    """LS-1: 'pf:architect-portfolio' becomes the public URL through url.<base>.insteadOf."""
    repo = git_init(tmp_path / "content")
    run_git(repo, ["config", "url.git@github.com:mbroadfo/.insteadOf", "pf:"])
    run_git(repo, ["remote", "add", "origin", "pf:architect-portfolio.git"])
    with pytest.raises(ContentLocationError, match="remote"):
        check_content_dir(repo)
    neighbour = git_init(tmp_path / "content3")
    run_git(neighbour, ["config", "url.git@github.com:mbroadfo/.insteadOf", "pf:"])
    run_git(neighbour, ["remote", "add", "origin", "pf:private-notes.git"])
    assert check_content_dir(neighbour) == neighbour.resolve()


@pytest.mark.parametrize(
    ("address", "public"),
    [
        ("https://github.com/mbroadfo/architect-portfolio", True),
        ("https://GitHub.com/MBroadfo/Architect-Portfolio.git/", True),
        ("ssh://git@ghe.example:22/mbroadfo/architect-portfolio.git", True),
        ("C:\\clones\\mbroadfo\\architect-portfolio", True),
        ("https://github.com/mbroadfo/architect-portfolio-content.git", False),
        ("https://github.com/notmbroadfo/architect-portfolio.git", False),
        ("https://example.invalid/private.git", False),
    ],
)
def test_public_remote_matching(address: str, public: bool) -> None:
    from portfolio_studio.location import is_public_remote

    assert is_public_remote(address) is public


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
