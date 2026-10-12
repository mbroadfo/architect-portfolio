"""Tests for scripts/check_security_review.py (AC0.11, BR5.2).

Every case builds a temporary git repository: ``main`` holds the sensitive-paths list, and a
``feature`` branch plays the pull request.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import check_security_review as review
import pytest
from conftest import GitRepo

RepoFactory = Callable[[], GitRepo]


def _record(patch_id: str, verdict: str = "READY") -> str:
    return f"# Review\n\npatch-id: {patch_id}\nverdict: {verdict}\n\n- Reviewer: test\n"


def _feature_touching_scripts(factory: RepoFactory) -> GitRepo:
    repo = factory()
    repo.run("checkout", "-q", "-b", "feature")
    repo.write("scripts/tool.py", "print('v2')\n")
    repo.commit_all("change a sensitive script")
    return repo


def _patch_id(repo: GitRepo) -> str:
    result = review.run_check(repo.path, "main", "HEAD")
    assert result.patch_id is not None
    return result.patch_id


def test_ac0_11_no_record_fails(git_repo: RepoFactory, capsys: pytest.CaptureFixture[str]) -> None:
    """AC0.11: a sensitive change with no review record fails, naming the paths."""
    repo = _feature_touching_scripts(git_repo)
    assert review.main(["--repo", str(repo.path), "--base", "main"]) == 1
    err = capsys.readouterr().err
    assert "no review record" in err
    assert "scripts/tool.py" in err


def test_ac0_11_mismatched_patch_identity_fails(git_repo: RepoFactory) -> None:
    repo = _feature_touching_scripts(git_repo)
    repo.write("docs/security-reviews/2026-10-11-other.md", _record("f" * 40))
    repo.commit_all("record for another change")
    result = review.run_check(repo.path, "main", "HEAD")
    assert not result.ok
    assert "no review record" in result.message


def test_ac0_11_not_ready_verdict_fails(git_repo: RepoFactory) -> None:
    repo = _feature_touching_scripts(git_repo)
    repo.write("docs/security-reviews/2026-10-11-tool.md", _record(_patch_id(repo), "NOT-READY"))
    repo.commit_all("NOT-READY review")
    result = review.run_check(repo.path, "main", "HEAD")
    assert not result.ok
    assert "not READY" in result.message


def test_ac0_11_matching_ready_record_passes(git_repo: RepoFactory) -> None:
    repo = _feature_touching_scripts(git_repo)
    repo.write("docs/security-reviews/2026-10-11-tool.md", _record(_patch_id(repo)))
    repo.commit_all("READY review")
    assert review.main(["--repo", str(repo.path), "--base", "main"]) == 0


def test_ac0_11_adding_the_record_keeps_the_identity(git_repo: RepoFactory) -> None:
    """The review folder is excluded, so committing the record does not move the target."""
    repo = _feature_touching_scripts(git_repo)
    before = _patch_id(repo)
    repo.write("docs/security-reviews/2026-10-11-tool.md", _record(before))
    repo.commit_all("READY review")
    assert _patch_id(repo) == before


def test_ac0_11_content_identical_rebase_still_passes(git_repo: RepoFactory) -> None:
    """A rebase over unrelated main commits keeps the identity, so the review stays valid."""
    repo = _feature_touching_scripts(git_repo)
    repo.write("docs/security-reviews/2026-10-11-tool.md", _record(_patch_id(repo)))
    repo.commit_all("READY review")
    repo.run("checkout", "-q", "main")
    repo.write("README.md", "base\nmore context on main\n")
    repo.commit_all("unrelated main change")
    repo.run("checkout", "-q", "feature")
    repo.run("rebase", "-q", "main")
    assert review.run_check(repo.path, "main", "HEAD").ok


def test_content_change_after_review_needs_a_new_review(git_repo: RepoFactory) -> None:
    repo = _feature_touching_scripts(git_repo)
    repo.write("docs/security-reviews/2026-10-11-tool.md", _record(_patch_id(repo)))
    repo.commit_all("READY review")
    repo.write("scripts/tool.py", "print('v3')\n")
    repo.commit_all("change after review")
    assert not review.run_check(repo.path, "main", "HEAD").ok


def test_non_sensitive_change_needs_no_review(git_repo: RepoFactory) -> None:
    repo = git_repo()
    repo.run("checkout", "-q", "-b", "feature")
    repo.write("README.md", "docs only\n")
    repo.commit_all("docs")
    result = review.run_check(repo.path, "main", "HEAD")
    assert result.ok
    assert "no security-sensitive path touched" in result.message


def test_only_review_records_changed_is_not_a_content_change(git_repo: RepoFactory) -> None:
    """Records are excluded from the identity, so a records-only change has nothing to review."""
    repo = git_repo()
    repo.write(".github/security-sensitive-paths.txt", "scripts/\ndocs/security-reviews/\n")
    repo.commit_all("list the review folder too")
    repo.run("checkout", "-q", "-b", "feature")
    repo.write("docs/security-reviews/note.md", "notes\n")
    repo.commit_all("records only")
    result = review.run_check(repo.path, "main", "HEAD")
    assert result.ok
    assert "no content change outside the review records" in result.message


def test_git_failure_is_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert review.main(["--repo", str(tmp_path), "--base", "main"]) == 2
    assert "ERROR" in capsys.readouterr().err


def test_missing_paths_list_on_base_and_head_is_an_error(git_repo: RepoFactory) -> None:
    repo = git_repo()
    repo.run("rm", "-q", ".github/security-sensitive-paths.txt")
    repo.commit_all("no list on main")
    repo.run("checkout", "-q", "-b", "feature")
    repo.write("scripts/tool.py", "print('v2')\n")
    repo.commit_all("change")
    with pytest.raises(review.GitError, match="cannot read"):
        review.run_check(repo.path, "main", "HEAD")


def test_r02_deleting_the_list_in_the_pull_request_does_not_help(git_repo: RepoFactory) -> None:
    """R-02: the base's list judges the change, so removing it on the head changes nothing."""
    repo = _feature_touching_scripts(git_repo)
    repo.run("rm", "-q", ".github/security-sensitive-paths.txt")
    repo.commit_all("drop list")
    result = review.run_check(repo.path, "main", "HEAD")
    assert not result.ok
    assert "scripts/tool.py" in result.sensitive_paths


def test_r02_the_list_is_read_from_the_base_not_the_head(git_repo: RepoFactory) -> None:
    """R-02: a pull request that narrows the list still needs a review for what it touches."""
    repo = _feature_touching_scripts(git_repo)
    repo.write(".github/security-sensitive-paths.txt", "infra/\n")
    repo.commit_all("narrow the list")
    result = review.run_check(repo.path, "main", "HEAD")
    assert not result.ok
    assert result.sensitive_paths == ("scripts/tool.py",)
    assert result.notices == ()


def test_r02_bootstrap_uses_the_head_list_with_a_notice(
    git_repo: RepoFactory, capsys: pytest.CaptureFixture[str]
) -> None:
    """R-02: the pull request that introduces the list is judged by its own list, and says so."""
    repo = git_repo()
    repo.run("rm", "-q", ".github/security-sensitive-paths.txt")
    repo.commit_all("main before the check exists")
    repo.run("checkout", "-q", "-b", "feature")
    repo.write(".github/security-sensitive-paths.txt", "scripts/\n")
    repo.write("scripts/tool.py", "print('v2')\n")
    repo.commit_all("introduce the check")
    result = review.run_check(repo.path, "main", "HEAD")
    assert not result.ok
    assert result.notices and "bootstrap" in result.notices[0]
    assert review.main(["--repo", str(repo.path), "--base", "main"]) == 1
    assert "NOTICE - bootstrap" in capsys.readouterr().out


def test_r02_a_not_ready_record_beside_a_ready_one_fails(git_repo: RepoFactory) -> None:
    """R-02: every record for the patch identity must be READY."""
    repo = _feature_touching_scripts(git_repo)
    patch_id = _patch_id(repo)
    repo.write("docs/security-reviews/2026-10-11-a.md", _record(patch_id))
    repo.write("docs/security-reviews/2026-10-11-b.md", _record(patch_id, "NOT-READY"))
    repo.commit_all("two records")
    result = review.run_check(repo.path, "main", "HEAD")
    assert not result.ok
    assert "2026-10-11-b.md: verdict NOT-READY" in result.message


REAL_LIST_COVERS = [
    "backend/portfolio_api/settings.py",
    "backend/portfolio_api/auth.py",
    "backend/portfolio_api/slice/app.py",
    "backend/portfolio_api/slice/api.py",
    "backend/portfolio_api/slice/snapshot.py",
    "backend/portfolio_api/slice/site_store.py",
    "backend/portfolio_api/slice/mongo.py",
    "backend/portfolio_api/slice/renderer.py",
    "backend/portfolio_api/slice/publish.py",
    "web/slice-renderer/src/pages.tsx",
    "web/slice-renderer/src/c2-schema.json",
    "web/slice-studio/src/api.ts",
    "web/slice-studio/src/config.ts",
    "local/nginx.conf",
    "local/compose.yaml",
    "local/fake-idp/fake_idp/app.py",
    "contracts/README.md",
    ".github/workflows/ci.yml",
    ".github/security-sensitive-paths.txt",
    "scripts/check_security_review.py",
    "scripts/gate_results.py",
    "infra/README.md",
]


@pytest.mark.parametrize("path", REAL_LIST_COVERS)
def test_r01_the_repository_list_covers_the_boundary_files(path: str) -> None:
    """R-01: each file that carries an authentication or publication boundary is listed."""
    from conftest import REPO_ROOT

    patterns = review.parse_patterns(
        (REPO_ROOT / ".github" / "security-sensitive-paths.txt").read_text(encoding="utf-8")
    )
    assert any(review.path_matches(path, pattern) for pattern in patterns)


def test_r01_ordinary_files_are_not_listed() -> None:
    from conftest import REPO_ROOT

    patterns = review.parse_patterns(
        (REPO_ROOT / ".github" / "security-sensitive-paths.txt").read_text(encoding="utf-8")
    )
    for path in ("README.md", "web/site/src/placeholder.ts", "docs/security-reviews/x.md"):
        assert not any(review.path_matches(path, pattern) for pattern in patterns)


@pytest.mark.parametrize(
    ("path", "pattern", "expected"),
    [
        ("scripts/tool.py", "scripts/", True),
        ("scriptsx/tool.py", "scripts/", False),
        ("backend/portfolio_api/auth.py", "backend/**/auth*", True),
        ("backend/auth/tokens.py", "backend/**/auth*", True),
        ("backend/portfolio_api/slice/publish.py", "backend/**/publish*", True),
        ("backend/portfolio_api/slice/models.py", "backend/**/auth*", False),
        (".github/security-sensitive-paths.txt", ".github/security-sensitive-paths.txt", True),
        ("local/fake-idp/fake_idp/app.py", "local/fake-idp/", True),
        ("local/compose.yaml", "local/fake-idp/", False),
        ("web/a/b.ts", "web/*/", True),
        ("web/a.ts", "web/?.ts", True),
    ],
)
def test_path_patterns(path: str, pattern: str, expected: bool) -> None:
    assert review.path_matches(path, pattern) is expected


def test_parse_patterns_skips_comments_and_blanks() -> None:
    assert review.parse_patterns("# c\n\nscripts/\n  infra/  \n") == ["scripts/", "infra/"]


def test_record_without_fields_is_ignored(git_repo: RepoFactory) -> None:
    repo = _feature_touching_scripts(git_repo)
    repo.write("docs/security-reviews/README.md", _record(_patch_id(repo)))
    repo.write("docs/security-reviews/empty.md", "no fields here\n")
    repo.commit_all("readme and empty record")
    records = review.load_records(repo.path, "HEAD")
    assert [(r.path, r.patch_id, r.verdict) for r in records] == [
        ("docs/security-reviews/empty.md", None, None)
    ]
    assert not review.run_check(repo.path, "main", "HEAD").ok
