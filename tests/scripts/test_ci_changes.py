"""Runs the real `changes` detection script from .github/workflows/ci.yml in throwaway git
repositories (Codex review R2 and R4): every path-gated output is exactly "true" or "false",
and `slice_e2e` is "true" only where the walking-slice code (local/compose.yaml) exists."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import gate_results
import pytest
import yaml
from conftest import GIT_ENV, REPO_ROOT, GitRepo

OUTPUT_KEYS = set(gate_results.PATH_GATED.values())


def _bash() -> str | None:
    """bash on PATH, or Git for Windows' bash next to the git installation."""
    if sys.platform != "win32":
        return shutil.which("bash")
    git = shutil.which("git")
    if git is None:
        return None
    exec_path = subprocess.run(
        [git, "--exec-path"], capture_output=True, text=True, check=True
    ).stdout.strip()
    candidate = Path(exec_path).parents[2] / "bin" / "bash.exe"
    return str(candidate) if candidate.is_file() else None


BASH = _bash()
pytestmark = pytest.mark.skipif(BASH is None, reason="bash is not available on this host")


def _detect_script() -> str:
    workflow = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    steps = workflow["jobs"]["changes"]["steps"]
    script: str = next(step["run"] for step in steps if step.get("id") == "detect")
    return script


def _outputs(repo: GitRepo, event: str, before: str = "") -> dict[str, str]:
    output = repo.path.parent / "github-output.txt"
    output.write_text("", encoding="utf-8")
    env = {
        **os.environ,
        **GIT_ENV,
        "HOME": str(repo.path.parent),
        "EVENT_NAME": event,
        "BASE_REF": "main",
        "BEFORE_SHA": before,
        "GITHUB_OUTPUT": str(output),
    }
    assert BASH is not None
    subprocess.run(
        [BASH, "-c", _detect_script()],
        cwd=repo.path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    pairs = [line.split("=", 1) for line in output.read_text("utf-8").splitlines() if line]
    values = {key: value for key, value in pairs}
    assert set(values) == OUTPUT_KEYS
    assert set(values.values()) <= {"true", "false"}
    return values


@pytest.fixture
def pull_request(tmp_path: Path) -> Callable[[bool, dict[str, str]], dict[str, str]]:
    """A repository on `main` (with or without the slice), then one change on a branch."""

    def run(slice_present: bool, changes: dict[str, str]) -> dict[str, str]:
        path = tmp_path / "repo"
        path.mkdir()
        repo = GitRepo(path)
        repo.run("init", "-q", "-b", "main")
        repo.run("config", "core.autocrlf", "false")
        repo.write("README.md", "base\n")
        repo.write("scripts/verify.py", "print('v1')\n")
        if slice_present:
            repo.write("local/compose.yaml", "services: {}\n")
        base = repo.commit_all("base")
        repo.run("update-ref", "refs/remotes/origin/main", base)
        repo.run("checkout", "-q", "-b", "feature")
        for relative, content in changes.items():
            repo.write(relative, content)
        repo.commit_all("change")
        return _outputs(repo, "pull_request")

    return run


def test_r4_slice_paths_turn_slice_e2e_on_where_the_slice_exists(
    pull_request: Callable[[bool, dict[str, str]], dict[str, str]],
) -> None:
    outputs = pull_request(True, {"backend/portfolio_api/slice/publish.py": "x\n"})
    assert outputs["slice_e2e"] == "true" and outputs["python"] == "true"


@pytest.mark.parametrize(
    "path",
    [
        "web/slice-studio/src/App.tsx",
        "web/package-lock.json",
        "local/nginx.conf",
        "tests/docker/test_services_isolation.py",
        ".nvmrc",
        "backend/requirements-slice.lock",
    ],
)
def test_r4_each_slice_dependency_turns_slice_e2e_on(
    pull_request: Callable[[bool, dict[str, str]], dict[str, str]], path: str
) -> None:
    assert pull_request(True, {path: "changed\n"})["slice_e2e"] == "true"


def test_r4_unrelated_changes_leave_every_job_off(
    pull_request: Callable[[bool, dict[str, str]], dict[str, str]],
) -> None:
    outputs = pull_request(True, {"docs/notes.md": "x\n"})
    assert outputs == dict.fromkeys(OUTPUT_KEYS, "false")


def test_r4_forcing_changes_never_turn_slice_e2e_on_without_the_slice(
    pull_request: Callable[[bool, dict[str, str]], dict[str, str]],
) -> None:
    """On main after S0 there is no slice code: a scripts/ or .github/ change forces the
    other path-gated jobs, but slice_e2e stays "false" (it would have nothing to run)."""
    outputs = pull_request(False, {"scripts/verify.py": "print('v2')\n", ".github/x.yml": "a\n"})
    assert outputs["slice_e2e"] == "false"
    assert outputs["python"] == outputs["web"] == outputs["guard"] == "true"


def test_r4_forcing_changes_turn_slice_e2e_on_with_the_slice(
    pull_request: Callable[[bool, dict[str, str]], dict[str, str]],
) -> None:
    assert pull_request(True, {".github/workflows/ci.yml": "a\n"})["slice_e2e"] == "true"


def test_r4_a_push_without_a_usable_base_forces_jobs_only_where_the_slice_exists(
    tmp_path: Path,
) -> None:
    for slice_present in (True, False):
        path = tmp_path / f"push-{slice_present}"
        path.mkdir()
        repo = GitRepo(path)
        repo.run("init", "-q", "-b", "main")
        repo.write("README.md", "base\n")
        if slice_present:
            repo.write("local/compose.yaml", "services: {}\n")
        repo.commit_all("first")
        outputs = _outputs(repo, "push", before="0" * 40)
        assert outputs["python"] == "true"
        assert outputs["slice_e2e"] == ("true" if slice_present else "false")
