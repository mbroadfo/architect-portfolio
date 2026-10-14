"""Shared fixtures for the S0 CI script tests."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
GUARD_FIXTURES = REPO_ROOT / "tests" / "guard" / "fixtures"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "author@example.invalid",
    "GIT_COMMITTER_NAME": "Test Committer",
    "GIT_COMMITTER_EMAIL": "committer@example.invalid",
    "GIT_CONFIG_NOSYSTEM": "1",
}


class GitRepo:
    """A throwaway git repository for one test."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def run(self, *args: str) -> str:
        env = {**os.environ, **GIT_ENV, "HOME": str(self.path.parent)}
        completed = subprocess.run(
            ["git", *args],
            cwd=self.path,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout.strip()

    def write(self, relative: str, content: str) -> None:
        target = self.path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode("utf-8"))

    def commit_all(self, message: str) -> str:
        self.run("add", "-A")
        self.run("commit", "-q", "-m", message)
        return self.run("rev-parse", "HEAD")


@pytest.fixture
def git_repo(tmp_path: Path) -> Callable[[], GitRepo]:
    """Return a factory for a repository whose main branch holds the sensitive-paths list."""

    def factory() -> GitRepo:
        path = tmp_path / "repo"
        path.mkdir()
        repo = GitRepo(path)
        repo.run("init", "-q", "-b", "main")
        repo.run("config", "core.autocrlf", "false")
        repo.write(".github/security-sensitive-paths.txt", "scripts/\nbackend/**/auth*\n")
        repo.write("README.md", "base\n")
        repo.write("scripts/tool.py", "print('v1')\n")
        repo.commit_all("base")
        return repo

    return factory
