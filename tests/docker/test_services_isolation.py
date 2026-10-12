"""R1 regression at the Docker level: a full verification services cycle (up, readiness,
down) keeps every pre-existing volume and every other Compose project's containers.

The cycle is the real one from ``scripts/verify.py`` with the real registry and Compose files.
It runs under a test namespace (project ``portfolio-verify-<checkout id>-isotest``, lock
``.verify-work/verify-isotest.lock``) because it normally runs *inside* a ``verify.py`` run
that already holds this checkout's own lock and stack; that stack is one of the "other
projects" whose containers must survive. The test creates no resource named like
``portfolio-slice`` and removes nothing itself: teardown is the verifier's own plain ``down``.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import compose_isolation as isolation
import pytest
import verify
from conftest import REPO_ROOT

NAMESPACE = "isotest"


@dataclass(frozen=True)
class Container:
    state: str
    project: str
    name: str


def _docker(*args: str) -> str:
    completed = subprocess.run(
        ["docker", *args], capture_output=True, text=True, encoding="utf-8", check=True
    )
    return completed.stdout


def _volumes() -> set[str]:
    return {line.strip() for line in _docker("volume", "ls", "-q").splitlines() if line.strip()}


def _containers() -> dict[str, Container]:
    output = _docker(
        "ps",
        "-a",
        "--no-trunc",
        "--format",
        '{{.ID}}\t{{.State}}\t{{.Label "com.docker.compose.project"}}\t{{.Names}}',
    )
    containers: dict[str, Container] = {}
    for line in output.splitlines():
        if line.strip():
            cid, state, project, name = [*line.split("\t"), "", "", ""][:4]
            containers[cid] = Container(state, project, name)
    return containers


class RecordingRunner:
    """The real runner, recording every command it is given."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(
        self, argv: Sequence[str], cwd: Path, env: Mapping[str, str], timeout: float
    ) -> int:
        self.calls.append(list(argv))
        return verify.default_runner(argv, cwd, env, timeout)


@pytest.fixture(scope="module", autouse=True)
def _docker_available() -> None:
    if not verify._docker_ready():
        pytest.skip("Docker is not available")


def test_r1_a_services_cycle_keeps_every_volume_and_other_projects_containers() -> None:
    """R1: record `docker volume ls -q` and the other projects' containers, run up,
    readiness and down for this checkout's (namespaced) project, then assert every
    pre-existing volume still exists and no other container was stopped or removed."""
    registry = verify.load_registry(REPO_ROOT / "scripts" / "verify-checks.toml")
    assert registry.services is not None
    runner = RecordingRunner()
    verifier = verify.Verifier(
        root=REPO_ROOT, registry=registry, runner=runner, namespace=NAMESPACE, out=sys.stdout
    )
    project = verifier.project
    assert project == isolation.checkout_project(REPO_ROOT, NAMESPACE)
    assert project.startswith("portfolio-verify-") and "portfolio-slice" not in project

    volumes_before = _volumes()
    others_before = {cid: c for cid, c in _containers().items() if c.project != project}
    print(f"before: {len(volumes_before)} volumes, {len(others_before)} other containers")

    with isolation.CheckoutLock(REPO_ROOT, f"verify-{NAMESPACE}"):
        try:
            assert verifier._ensure_services() == "", "the stack did not start or get ready"
            mine = {cid for cid, c in _containers().items() if c.project == project}
            assert mine, "the cycle started no containers of its own project"
        finally:
            verifier.stop_services()

    volumes_after = _volumes()
    containers_after = _containers()
    missing_volumes = sorted(volumes_before - volumes_after)
    assert missing_volumes == [], f"pre-existing volumes were removed: {missing_volumes}"
    for cid, before in others_before.items():
        after = containers_after.get(cid)
        assert after is not None, f"container {before.name} ({before.project}) was removed"
        if before.state == "running":
            assert after.state == "running", f"container {before.name} was stopped"
    assert not [c for c in containers_after.values() if c.project == project], "down left some"
    assert f"{project}_site" in volumes_after, "the project's own site volume is kept"

    docker_calls = [argv for argv in runner.calls if argv[:2] == ["docker", "compose"]]
    subcommand = 4 + 2 * len(registry.services.compose_files)
    assert [argv[subcommand] for argv in docker_calls] == ["up", "down"]
    for argv in docker_calls:
        assert argv[:4] == ["docker", "compose", "-p", project]
        assert not set(argv) & {"-v", "--volumes", "--rmi", "--remove-orphans", "prune"}
    print(f"after: {len(volumes_after)} volumes; every earlier volume and container kept")
