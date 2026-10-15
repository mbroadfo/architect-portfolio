"""A thin wrapper around the ``git`` command for the private content repository.

Every save, upload, publish and take-down is one commit, so the Git history is the activity
log (FR7.7) and the first backup (NFR10, ADR-009 superseded by ADR-013).
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from portfolio_studio.errors import GitError

GIT_TIMEOUT_SECONDS = 60
FALLBACK_NAME = "Portfolio Studio"
FALLBACK_EMAIL = "studio@localhost"
LOG_SEPARATOR = "\x1f"


@dataclass(frozen=True)
class Commit:
    sha: str
    time: str
    subject: str


def git_executable() -> str:
    found = shutil.which("git")
    if found is None:
        raise GitError("git is not installed or not on PATH")
    return found


def run_git(cwd: Path, args: Sequence[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run ``git <args>`` in ``cwd`` without a shell; raise GitError on failure."""
    try:
        completed = subprocess.run(  # noqa: S603 - fixed executable, argument list, no shell
            [git_executable(), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise GitError(f"git {args[0] if args else ''} could not run: {error}") from error
    if check and completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        raise GitError(f"git {args[0]} failed: {detail[-1] if detail else completed.returncode}")
    return completed


def toplevel(path: Path) -> Path | None:
    """The root of the Git work tree containing ``path``, or None."""
    probe = path if path.is_dir() else path.parent
    while not probe.exists():
        probe = probe.parent
    completed = run_git(probe, ["rev-parse", "--show-toplevel"], check=False)
    if completed.returncode != 0:
        return None
    return Path(completed.stdout.strip()).resolve()


def remote_urls(repo: Path) -> list[str]:
    completed = run_git(repo, ["remote", "-v"], check=False)
    if completed.returncode != 0:
        return []
    return sorted({line.split()[1] for line in completed.stdout.splitlines() if line.split()})


class ContentRepo:
    """Commits in the content repository."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def init(self) -> None:
        run_git(self.root, ["init", "--quiet", "--initial-branch=main"])

    def _identity(self) -> list[str]:
        """Use the owner's configured identity; fall back to a local one if none is set."""
        name = run_git(self.root, ["config", "user.name"], check=False).stdout.strip()
        email = run_git(self.root, ["config", "user.email"], check=False).stdout.strip()
        args: list[str] = []
        if not name:
            args += ["-c", f"user.name={FALLBACK_NAME}"]
        if not email:
            args += ["-c", f"user.email={FALLBACK_EMAIL}"]
        return args

    def commit(self, paths: Sequence[str], message: str) -> str:
        """Stage ``paths`` (additions, changes and deletions) and commit them.

        On failure the staged change is undone and the error is raised; the caller restores
        the working files.
        """
        present = self._present(paths)
        if not present:
            raise GitError("nothing to commit")
        run_git(self.root, ["add", "--all", "--", *present])
        completed = run_git(
            self.root,
            [*self._identity(), "commit", "--quiet", "--no-verify", "-m", message, "--", *present],
            check=False,
        )
        if completed.returncode != 0:
            run_git(self.root, ["reset", "--quiet", "--", *present], check=False)
            detail = (completed.stderr or completed.stdout).strip().splitlines()
            raise GitError(f"git commit failed: {detail[-1] if detail else completed.returncode}")
        return run_git(self.root, ["rev-parse", "HEAD"]).stdout.strip()

    def _present(self, paths: Sequence[str]) -> list[str]:
        """The paths that exist now or are tracked (a pathspec matching nothing fails)."""
        present = []
        for path in paths:
            tracked = run_git(self.root, ["ls-files", "--", path], check=False).stdout.strip()
            if (self.root / path).exists() or tracked:
                present.append(path)
        return present

    def restore(self, paths: Sequence[str]) -> None:
        """Put ``paths`` back to the last commit (used after a failed operation)."""
        for path in self._present(paths):
            run_git(self.root, ["checkout", "--quiet", "HEAD", "--", path], check=False)
            run_git(self.root, ["clean", "--quiet", "-fd", "--", path], check=False)

    def is_dirty(self) -> bool:
        status = run_git(self.root, ["status", "--porcelain", "--untracked-files=all"])
        return bool(status.stdout.strip())

    def commit_count(self) -> int:
        completed = run_git(self.root, ["rev-list", "--count", "HEAD"], check=False)
        return int(completed.stdout.strip()) if completed.returncode == 0 else 0

    def log(self, limit: int = 100) -> list[Commit]:
        """The newest commits first: the Studio's activity log."""
        completed = run_git(
            self.root,
            ["log", f"-n{limit}", f"--format=%H{LOG_SEPARATOR}%cI{LOG_SEPARATOR}%s"],
            check=False,
        )
        if completed.returncode != 0:
            return []
        commits = []
        for line in completed.stdout.splitlines():
            sha, time, subject = line.split(LOG_SEPARATOR, 2)
            commits.append(Commit(sha=sha, time=time, subject=subject))
        return commits

    def bundle(self, target: Path) -> None:
        """Write every ref to a Git bundle file and verify it."""
        run_git(self.root, ["bundle", "create", str(target), "--all"])
        run_git(self.root, ["bundle", "verify", "--quiet", str(target)])
