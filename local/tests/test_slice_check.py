"""LOCAL-ONLY: unit tests for local/slice_check.py (Codex review R1 and R3; AC0.9, NFR1.2).

The command runner and the readiness wait are replaced, so no Docker command, browser or
network call runs. Every composed ``docker compose`` argv is captured and checked.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Sequence
from pathlib import Path

import compose_isolation as isolation
import pytest
import scan_output
import slice_check
from conftest import REPO_ROOT

FORBIDDEN = {"-v", "--volumes", "--rmi", "--remove-orphans", "prune"}
FIXTURE = REPO_ROOT / "local" / "fixtures"
ASSET = FIXTURE / "ast_SliceFixtureImage0001"
PORTS = [42001, 42002, 42003, 42004, 42005]


def fake_ports(count: int) -> list[int]:
    return PORTS[:count]


class Recorder:
    """Stands in for slice_check.run: records commands, answers with canned output."""

    def __init__(self, project: str) -> None:
        self.project = project
        self.commands: list[list[str]] = []

    def __call__(self, command: Sequence[str], cwd: Path = REPO_ROOT, env: object = None) -> str:
        argv = list(command)
        self.commands.append(argv)
        if "config" in argv:
            ports = [{"host_ip": "127.0.0.1", "published": "42001"}]
            return json.dumps({"services": {"api": {"ports": ports}}})
        if "readlink" in argv:
            return "releases/v0001\n"
        if "mongosh" in argv:
            return "0\n" if "countDocuments" in argv[-1] else "{}\n"
        if "cp" in argv:
            Path(argv[-1]).mkdir(parents=True, exist_ok=True)
        return "ok\n"

    @property
    def docker(self) -> list[list[str]]:
        return [argv for argv in self.commands if argv[:2] == ["docker", "compose"]]


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Recorder, list[str]]:
    stack = slice_check.Stack.from_env({}, free_ports=fake_ports)
    recorder = Recorder(stack.project)
    waits: list[str] = []
    monkeypatch.setattr(slice_check, "run", recorder)
    monkeypatch.setattr(slice_check, "wait_for", lambda url, timeout=0: waits.append(url))
    monkeypatch.setattr(slice_check, "WORK_DIR", tmp_path / "work")
    monkeypatch.setattr(slice_check.shutil, "which", lambda name: f"/usr/bin/{name}")
    return recorder, waits


def test_r1_the_project_is_derived_per_checkout(tmp_path: Path) -> None:
    main = slice_check.Stack.from_env({}, root=REPO_ROOT, free_ports=fake_ports)
    other = slice_check.Stack.from_env({}, root=tmp_path, free_ports=fake_ports)
    assert main.project == isolation.checkout_project(REPO_ROOT)
    assert main.project.startswith("portfolio-verify-")
    assert other.project != main.project


@pytest.mark.parametrize(
    "project", ["portfolio-slice", "portfolio-verify", "my-stack", "Portfolio-Verify-x"]
)
def test_r1_protected_and_foreign_projects_are_refused(
    project: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(slice_check.SliceCheckError, match="refusing Compose project"):
        slice_check.Stack.from_env({"SLICE_COMPOSE_PROJECT": project}, free_ports=fake_ports)
    monkeypatch.setenv("SLICE_COMPOSE_PROJECT", project)
    assert slice_check.main([]) == 2
    assert "refusing Compose project" in capsys.readouterr().err


def test_r1_free_ports_are_chosen_and_given_ports_are_kept() -> None:
    stack = slice_check.Stack.from_env({"SLICE_API_PORT": "18000"}, free_ports=fake_ports)
    assert stack.ports == {
        "api": "18000",
        "site": "42001",
        "idp": "42002",
        "mongo": "42003",
        "studio": "42004",
    }
    assert stack.env()["SLICE_STUDIO_PORT"] == "42004"
    with pytest.raises(slice_check.SliceCheckError, match="must be a port number"):
        slice_check.Stack.from_env({"SLICE_API_PORT": "80; rm"}, free_ports=fake_ports)


def test_r1_a_managed_stack_needs_every_port_from_the_caller() -> None:
    env = {"SLICE_STACK_MANAGED": "1", "SLICE_API_PORT": "18000"}
    with pytest.raises(slice_check.SliceCheckError, match="did not pass SLICE_SITE_PORT"):
        slice_check.Stack.from_env(env, free_ports=fake_ports)


def test_r1_every_compose_argv_is_isolated_for_start_readiness_exec_and_teardown(
    recorded: tuple[Recorder, list[str]],
) -> None:
    """R1: config, up, exec, cp and down all use this checkout's project and never a
    data-removing flag; readiness uses the ports chosen for this run."""
    recorder, waits = recorded
    stack = slice_check.Stack.from_env({}, free_ports=fake_ports)
    results = slice_check.run_steps(stack, keep_running=False)
    assert [outcome for _, outcome, _ in results] == ["passed"] * len(slice_check.STEPS)
    docker = recorder.docker
    subcommands = [argv[4 + 2 * len(stack.compose_files)] for argv in docker]
    assert subcommands == ["config", "up", "exec", "exec", "cp", "exec", "down"]
    for argv in docker:
        assert argv[:4] == ["docker", "compose", "-p", stack.project]
        assert not FORBIDDEN & set(argv), argv
        assert "portfolio-slice" not in argv
    assert docker[1][-3:] == ["-d", "--build", "--force-recreate"]
    assert docker[-1][-1] == "down"
    assert waits == ["http://127.0.0.1:42001/health", "http://127.0.0.1:42002/"]


def test_r1_a_managed_stack_is_neither_started_nor_stopped(
    recorded: tuple[Recorder, list[str]],
) -> None:
    recorder, _ = recorded
    env = {
        "SLICE_STACK_MANAGED": "1",
        **{v: str(p) for v, p in zip(slice_check.PORT_VARIABLES.values(), PORTS, strict=True)},
    }
    stack = slice_check.Stack.from_env(env)
    slice_check.run_steps(stack, keep_running=False)
    subcommands = [argv[4 + 2 * len(stack.compose_files)] for argv in recorder.docker]
    assert "up" not in subcommands and "down" not in subcommands


def test_r1_keep_running_prints_the_plain_down_command(
    recorded: tuple[Recorder, list[str]], capsys: pytest.CaptureFixture[str]
) -> None:
    recorder, _ = recorded
    stack = slice_check.Stack.from_env({}, free_ports=fake_ports)
    slice_check.stop_stack(stack, keep_running=True)
    assert recorder.docker == []
    assert f"-p {stack.project}" in capsys.readouterr().out


@pytest.mark.parametrize("flag", sorted(FORBIDDEN))
def test_r1_the_stack_refuses_data_removing_arguments(flag: str) -> None:
    stack = slice_check.Stack.from_env({}, free_ports=fake_ports)
    with pytest.raises(slice_check.SliceCheckError, match="refusing data-removing"):
        stack.compose("down", flag)


# Security re-review S0-4: forbidden operations spelled to slip past exact-token matching.
EVASIONS = [
    ("down", "--volumes=true"),
    ("down", "-tv"),
    ("down", "-v=true"),
    ("down", "--rmi=all"),
    ("down", "--remove-orphans=true"),
    ("--profile", "x", "rm", "-fsv"),
    ("--profile", "x", "rm"),
    ("volume", "rm", "data"),
    ("volumes",),
    ("system", "prune"),
    ("prune",),
]


@pytest.mark.parametrize("args", EVASIONS, ids=[" ".join(a) for a in EVASIONS])
def test_s0_4_differently_spelled_forbidden_arguments_are_refused(args: tuple[str, ...]) -> None:
    stack = slice_check.Stack.from_env({}, free_ports=fake_ports)
    with pytest.raises(slice_check.SliceCheckError, match="refusing data-removing"):
        stack.compose(*args)


def test_s0_4_every_command_the_check_runs_is_still_allowed(
    recorded: tuple[Recorder, list[str]],
) -> None:
    recorder, _ = recorded
    stack = slice_check.Stack.from_env({}, free_ports=fake_ports)
    results = slice_check.run_steps(stack, keep_running=False)
    assert all(outcome == "passed" for _, outcome, _ in results)
    assert len(recorder.docker) == 7


def test_r1_a_second_run_in_the_same_checkout_fails_clearly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stack = slice_check.Stack(
        isolation.checkout_project(tmp_path),
        ("local/compose.yaml",),
        dict.fromkeys(slice_check.PORT_VARIABLES, "1"),
        managed=False,
        root=tmp_path,
    )
    monkeypatch.setattr(slice_check.Stack, "from_env", classmethod(lambda cls, environ: stack))

    def must_not_run(stack: object, keep_running: bool) -> list[tuple[str, str, float]]:
        raise AssertionError("no step may run while another run holds the lock")

    monkeypatch.setattr(slice_check, "run_steps", must_not_run)
    with isolation.CheckoutLock(tmp_path, "verify"):
        assert slice_check.main([]) == 2
    assert "another verification run is using this checkout" in capsys.readouterr().err


def test_r3_the_scan_gets_the_authorized_media_digests() -> None:
    stack = slice_check.Stack.from_env({}, free_ports=fake_ports)
    argv = slice_check.scan_argv(stack, Path("release"), Path("snapshot.json"))
    position = argv.index("--media-digests")
    assert Path(argv[position + 1]) == FIXTURE / "derivatives.sha256.json"


def test_r3_committed_digests_match_the_fixture_derivatives() -> None:
    """The trusted manifest names every committed derivative, with its exact SHA-256."""
    digests = scan_output.load_media_digests(FIXTURE / "derivatives.sha256.json")
    expected = {
        f"media/{ASSET.name}/{path.name}": hashlib.sha256(path.read_bytes()).hexdigest()
        for path in ASSET.iterdir()
        if path.is_file()
    }
    assert digests == expected


def test_r3_codex_reproduction_on_the_real_fixture(tmp_path: Path) -> None:
    """R3 (Codex reproduction): copy w480.jpg to an allow-listed release media path, append
    PRIVATE_DRAFT_NOTE=not-authorized-for-publication; scan_file must report a finding."""
    release = tmp_path / "release"
    key = f"media/{ASSET.name}/w480.jpg"
    target = release / key
    target.parent.mkdir(parents=True)
    shutil.copyfile(ASSET / "w480.jpg", target)
    digests = scan_output.load_media_digests(FIXTURE / "derivatives.sha256.json")
    allowed = scan_output.Allowed(files={key})
    static = REPO_ROOT / "web" / "slice-renderer" / "assets"
    assert scan_output.scan_file(release, target, allowed, static, digests) == []
    with target.open("ab") as handle:
        handle.write(b"PRIVATE_DRAFT_NOTE=not-authorized-for-publication")
    findings = scan_output.scan_file(release, target, allowed, static, digests)
    assert [f.location for f in findings] == [key]
    assert findings[0].reason.startswith("bytes differ from the authorized derivative")
