"""Tests for scripts/verify.py, the project-wide verification entry point."""

from __future__ import annotations

import io
import re
import sys
import textwrap
from collections.abc import Mapping, Sequence
from pathlib import Path

import compose_isolation as isolation
import pytest
import verify
from conftest import REPO_ROOT

PY = sys.executable.replace("\\", "/")
PORT_VARS = ("SLICE_API_PORT", "SLICE_SITE_PORT", "SLICE_MONGO_PORT", "SLICE_STUDIO_PORT")
FAKE_PORTS = [41001, 41002, 41003, 41004]
SERVICES = """
[services]
compose_files = ["stack.yaml", "stack.override.yaml"]
applies_when = ["stack.yaml"]
ports = ["SLICE_API_PORT", "SLICE_SITE_PORT", "SLICE_MONGO_PORT", "SLICE_STUDIO_PORT"]
ready_urls = ["http://127.0.0.1:{SLICE_API_PORT}/health", "http://127.0.0.1:{SLICE_SITE_PORT}/"]
ready_timeout = 5
[services.env]
SLICE_COMPOSE_PROJECT = "{project}"
SLICE_STACK_MANAGED = "1"
SLICE_IT_MONGO_URI = "mongodb://127.0.0.1:{SLICE_MONGO_PORT}/?directConnection=true"
"""
FORBIDDEN_FLAGS = ("-v", "--volumes", "--rmi", "--remove-orphans", "prune")


class Recorder:
    """A runner that records each command and answers with a chosen exit code.

    ``reports`` maps a check marker (an argv element) to JUnit XML that the fake command
    "writes" to the report path verify.py passes in VERIFY_JUNIT.
    """

    def __init__(
        self, codes: Mapping[str, int] | None = None, reports: Mapping[str, str] | None = None
    ) -> None:
        self.codes = dict(codes or {})
        self.reports = dict(reports or {})
        self.calls: list[tuple[list[str], Path, dict[str, str]]] = []

    def __call__(
        self, argv: Sequence[str], cwd: Path, env: Mapping[str, str], timeout: float
    ) -> int:
        self.calls.append((list(argv), cwd, dict(env)))
        for marker, xml in self.reports.items():
            if marker in argv:
                Path(env["VERIFY_JUNIT"]).write_text(xml, encoding="utf-8")
        for marker, code in self.codes.items():
            if marker in argv:
                return code
        return 0

    @property
    def docker_calls(self) -> list[list[str]]:
        return [argv for argv, _, _ in self.calls if argv[:2] == ["docker", "compose"]]


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def probes(**overrides: object) -> verify.Probes:
    clock = Clock()
    values: dict[str, object] = {
        "which": lambda name: f"/usr/bin/{name}",
        "has_module": lambda name: True,
        "docker_ready": lambda: True,
        "port_free": lambda port: True,
        "url_ready": lambda url: True,
        "free_ports": lambda count: FAKE_PORTS[:count],
        "sleep": clock.sleep,
        "clock": clock,
        "platform": "linux",
    }
    values.update(overrides)
    return verify.Probes(**values)  # type: ignore[arg-type]


def check(check_id: str, *extra: str, unit: str = "project", kind: str = "unit") -> str:
    lines = [
        "[[check]]",
        f'id = "{check_id}"',
        f'unit = "{unit}"',
        f'kind = "{kind}"',
        'argv = ["{python}", "-c", "pass"]',
        *extra,
    ]
    return "\n".join(lines) + "\n"


def registry(tmp_path: Path, *checks: str, services: bool = False) -> Path:
    (tmp_path / "stack.yaml").write_text("services: {}\n", encoding="utf-8")
    path = tmp_path / "checks.toml"
    path.write_text((SERVICES if services else "") + "\n".join(checks), encoding="utf-8")
    return path


def row(text: str, check_id: str) -> list[str]:
    """The columns of the table row for ``check_id`` (columns are separated by 2+ spaces)."""
    for line in text.splitlines():
        cells = re.split(r"\s{2,}", line.strip())
        if cells and cells[0] == check_id:
            return cells
    raise AssertionError(f"no row for {check_id}")


def run_main(
    tmp_path: Path,
    path: Path,
    *args: str,
    runner: Recorder | None = None,
    **probe_overrides: object,
) -> tuple[int, str]:
    out = io.StringIO()
    code = verify.main(
        ["--registry", str(path), *args],
        runner=runner or Recorder(),
        probes=probes(**probe_overrides),
        root=tmp_path,
        out=out,
    )
    return code, out.getvalue()


def junit(*cases: tuple[str, str | None]) -> str:
    """A JUnit report: (name, skip message or None) per test case."""
    body = "".join(
        f'<testcase classname="pkg.mod" name="{name}">'
        + (f'<skipped message="{skip}"/>' if skip is not None else "")
        + "</testcase>"
        for name, skip in cases
    )
    return f'<?xml version="1.0"?><testsuites><testsuite name="s">{body}</testsuite></testsuites>'


# --- running real commands -------------------------------------------------------------------


def test_real_commands_pass_and_fail(tmp_path: Path) -> None:
    """A passing and a failing command; the summary names both and the exit code is 1."""
    path = tmp_path / "checks.toml"
    path.write_text(
        "[[check]]\nid='ok'\nunit='project'\nkind='unit'\n"
        f"argv=['{PY}', '-c', 'import sys; sys.exit(0)']\n"
        "[[check]]\nid='broken'\nunit='project'\nkind='static'\n"
        f"argv=['{PY}', '-c', 'import sys; sys.exit(3)']\n",
        encoding="utf-8",
    )
    out = io.StringIO()
    code = verify.main(["--registry", str(path)], root=tmp_path, out=out)
    text = out.getvalue()
    assert code == 1
    assert row(text, "ok")[:4] == ["ok", "project", "unit", "passed"]
    broken = row(text, "broken")
    assert broken[:4] == ["broken", "project", "static", "failed"]
    assert broken[-1] == "exit 3"
    assert "verify: FAILED (1 passed, 1 failed, 0 skipped, 0 not applicable)" in text


def test_default_runner_reports_timeouts_and_missing_programs(tmp_path: Path) -> None:
    slow = [sys.executable, "-c", "import time; time.sleep(5)"]
    assert verify.default_runner(slow, tmp_path, {}, 0.5) == verify.EXIT_TIMEOUT
    missing = [str(tmp_path / "no-such-program")]
    assert verify.default_runner(missing, tmp_path, {}, 5) == verify.EXIT_NOT_RUNNABLE


def test_python_placeholder_is_this_interpreter(tmp_path: Path) -> None:
    runner = Recorder()
    code, _ = run_main(tmp_path, registry(tmp_path, check("a")), runner=runner)
    assert code == 0
    assert runner.calls[0][0][0] == sys.executable


# --- prerequisites, strict mode and applicability ----------------------------------------------


def test_missing_prerequisite_skips_and_strict_turns_it_into_failure(tmp_path: Path) -> None:
    path = registry(tmp_path, check("needs-tool", 'requires = ["tool:actionlint"]'))
    code, text = run_main(tmp_path, path, which=lambda name: None)
    assert code == 0
    assert "skipped" in text and "actionlint not on PATH" in text
    code, text = run_main(tmp_path, path, "--strict", which=lambda name: None)
    assert code == 1
    assert "--strict: required checks skipped: needs-tool" in text


def test_optional_checks_skip_without_failing_strict(tmp_path: Path) -> None:
    path = registry(tmp_path, check("optional", 'requires = ["tool:gitleaks"]', "required = false"))
    code, text = run_main(tmp_path, path, "--strict", which=lambda name: None)
    assert code == 0
    assert "gitleaks not on PATH (optional)" in text


def test_applies_when_marks_not_applicable_and_is_not_a_skip(tmp_path: Path) -> None:
    path = registry(tmp_path, check("slice-only", 'applies_when = ["backend/slice"]', unit="slice"))
    runner = Recorder()
    code, text = run_main(tmp_path, path, "--strict", runner=runner)
    assert code == 0
    assert "not applicable" in text and "missing backend/slice" in text
    assert runner.calls == []


@pytest.mark.parametrize(
    ("requirement", "overrides", "reason"),
    [
        ('"path:web/node_modules"', {}, "missing web/node_modules"),
        ('"module:ruff"', {"has_module": lambda name: False}, "Python module ruff not installed"),
        ('"free-port:5173"', {"port_free": lambda port: False}, "port 5173 is in use"),
        ('"docker"', {"docker_ready": lambda: False}, "Docker CLI or daemon unavailable"),
    ],
)
def test_each_prerequisite_kind(
    tmp_path: Path, requirement: str, overrides: dict[str, object], reason: str
) -> None:
    path = registry(tmp_path, check("c", f"requires = [{requirement}]"))
    _, text = run_main(tmp_path, path, **overrides)
    assert reason in text


def test_missing_npm_placeholder_skips(tmp_path: Path) -> None:
    path = registry(
        tmp_path, '[[check]]\nid="npm"\nunit="project"\nkind="static"\nargv=["{npm}","test"]\n'
    )
    _, text = run_main(tmp_path, path, which=lambda name: None)
    assert "npm not on PATH" in text


# --- selection and listing ----------------------------------------------------------------------


def test_unit_and_kind_filters(tmp_path: Path) -> None:
    path = registry(
        tmp_path,
        check("p-static", kind="static"),
        check("s-unit", unit="walking-slice"),
        check("s-e2e", unit="walking-slice", kind="e2e"),
    )
    runner = Recorder()
    _, text = run_main(tmp_path, path, "--unit", "walking-slice", runner=runner)
    assert "s-unit" in text and "s-e2e" in text and "p-static" not in text
    runner = Recorder()
    _, text = run_main(tmp_path, path, "--kind", "static", "--kind", "e2e", runner=runner)
    assert "p-static" in text and "s-e2e" in text and "s-unit" not in text


def test_list_runs_nothing(tmp_path: Path) -> None:
    path = registry(
        tmp_path,
        check("plain"),
        check("tooling", 'requires = ["tool:actionlint"]', "required = false"),
        check("stacked", 'requires = ["services"]', kind="e2e"),
        check("absent", 'applies_when = ["missing/dir"]'),
        services=True,
    )
    runner = Recorder()
    code, text = run_main(tmp_path, path, "--list", runner=runner, which=lambda name: None)
    assert code == 0
    assert runner.calls == []
    assert row(text, "plain") == ["plain", "project", "unit", "yes", "yes", "none"]
    assert row(text, "tooling")[3:] == ["no", "yes", "actionlint not on PATH"]
    assert row(text, "stacked")[-1] == "ok (stack started on demand)"
    assert row(text, "absent")[4] == "no (missing missing/dir)"
    assert f"services: Compose project {isolation.checkout_project(tmp_path)}" in text


# --- registry errors ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content",
    [
        "not = [valid",
        "",
        check("a", kind="weird"),
        check("a") + check("a"),
        check("a", 'requires = ["magic"]'),
        check("a", 'requires = ["services"]'),
        check("a", "colour = 1"),
        '[[check]]\nid="a"\nunit="p"\nkind="unit"\nargv=[]\n',
        '[[check]]\nid="a"\nunit="p"\nkind="unit"\nargv="python"\n',
        '[[check]]\nunit="p"\nkind="unit"\nargv=["x"]\n',
        check("a", 'required = "yes"'),
        check("a", "timeout = -1"),
        check("a", "env = { A = 1 }"),
        check("a", "cwd = 3"),
        check("a", 'report = "xml"'),
        check("a", 'allowed_skips = [{ test = "t", reason = "r" }]'),
        check("a", 'report = "junit"', 'allowed_skips = [{ test = "t" }]'),
        check("a", 'report = "junit"', 'allowed_skips = [{ test = "t", reason = "r", x = 1 }]'),
        check("a", 'report = "junit"', 'allowed_skips = "t"'),
        '[[check]]\nid="a"\nunit="p"\nkind="unit"\nargv=["{compose}","run"]\n',
        SERVICES + "[[check]]\nid='a'\nunit='p'\nkind='unit'\nargv=['x', '{compose}']\n"
        "requires=['services']\n",
        "check = 1\n",
        '[services]\nproject = "portfolio-verify"\ncompose_files = ["a.yaml"]\n' + check("a"),
        "[services]\ncompose_files = []\n" + check("a"),
        '[services]\ncompose_files = ["a.yaml"]\nready_timeout = 0\n' + check("a"),
        '[services]\ncompose_files = ["a.yaml"]\ncolour = 1\n' + check("a"),
        '[services]\ncompose_files = ["a.yaml"]\nports = ["lower"]\n' + check("a"),
        '[services]\ncompose_files = ["a.yaml"]\nports = ["A_PORT", "A_PORT"]\n' + check("a"),
        '[services]\ncompose_files = ["a.yaml"]\nready_urls = ["http://x:{NOPE}/"]\n' + check("a"),
        '[services]\ncompose_files = ["a.yaml"]\n[services.env]\nX = "{nope}"\n' + check("a"),
        "services = 1\n" + check("a"),
    ],
)
def test_registry_errors_exit_2(
    tmp_path: Path, content: str, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "checks.toml"
    path.write_text(content, encoding="utf-8")
    assert (
        verify.main(["--registry", str(path)], runner=Recorder(), probes=probes(), root=tmp_path)
        == 2
    )
    assert "registry error" in capsys.readouterr().err


def test_missing_registry_unknown_unit_and_empty_selection_exit_2(tmp_path: Path) -> None:
    assert run_main(tmp_path, tmp_path / "nope.toml")[0] == 2
    path = registry(tmp_path, check("a"))
    assert run_main(tmp_path, path, "--unit", "nobody")[0] == 2
    assert run_main(tmp_path, path, "--kind", "e2e")[0] == 2


def test_usage_error_exits_2(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exit_info:
        verify.main(["--kind", "nonsense"], root=tmp_path)
    assert exit_info.value.code == 2


# --- R1: the per-checkout stack, free ports, the lock and data safety ---------------------------


def _forbidden(argv: Sequence[str]) -> bool:
    return any(arg in FORBIDDEN_FLAGS for arg in argv) or "rm" in argv


def test_r1_every_compose_argv_uses_the_checkout_project_and_no_forbidden_flag(
    tmp_path: Path,
) -> None:
    """R1: start, the {compose} run of a check and teardown all use this checkout's project
    with no data-removing flag; readiness and the checks use the ports chosen for the run."""
    path = registry(
        tmp_path,
        check("integration", 'requires = ["services"]', kind="integration"),
        "[[check]]\nid='in-stack'\nunit='p'\nkind='integration'\n"
        "argv=['{compose}', 'run', '--rm', '--no-deps', '-T', 'tests']\nrequires=['services']\n",
        check("e2e", 'requires = ["services"]', 'env = { EXTRA = "1" }', kind="e2e"),
        services=True,
    )
    runner = Recorder()
    ready: list[str] = []
    code, text = run_main(
        tmp_path, path, runner=runner, url_ready=lambda url: ready.append(url) or True
    )
    assert code == 0, text
    project = isolation.checkout_project(tmp_path)
    assert re.fullmatch(r"portfolio-verify-[0-9a-f]{10}", project)
    docker = runner.docker_calls
    assert len(docker) == 3
    assert docker[0][-4:] == ["up", "-d", "--build", "--force-recreate"]
    assert docker[1][-5:] == ["run", "--rm", "--no-deps", "-T", "tests"]
    assert docker[2][-1] == "down"
    for argv in docker:
        assert argv[:4] == ["docker", "compose", "-p", project]
        assert str(tmp_path / "stack.override.yaml") in argv
        assert not _forbidden(argv), argv
    assert ready == ["http://127.0.0.1:41001/health", "http://127.0.0.1:41002/"]
    envs = [env for _, _, env in runner.calls]
    assert all(env["SLICE_API_PORT"] == "41001" for env in envs)
    assert all(env["SLICE_COMPOSE_PROJECT"] == project for env in envs)
    assert envs[1]["SLICE_IT_MONGO_URI"] == "mongodb://127.0.0.1:41003/?directConnection=true"
    assert envs[3]["EXTRA"] == "1" and envs[3]["SLICE_STACK_MANAGED"] == "1"
    assert "volumes kept" in text and f"Compose project '{project}'" in text


def test_r1_worktrees_get_different_projects(tmp_path: Path) -> None:
    first, second = tmp_path / "main", tmp_path / "worktree"
    first.mkdir()
    second.mkdir()
    assert isolation.checkout_project(first) != isolation.checkout_project(second)
    assert isolation.checkout_project(first) == isolation.checkout_project(first / ".")
    assert isolation.checkout_project(first, "isotest").endswith("-isotest")


@pytest.mark.parametrize(
    "name", ["portfolio-slice", "portfolio-verify", "portfolio-verify-", "my-stack", "Portfolio-X"]
)
def test_r1_protected_and_foreign_projects_are_refused(tmp_path: Path, name: str) -> None:
    with pytest.raises(isolation.IsolationError, match="refusing Compose project"):
        isolation.validate_project(name)
    with pytest.raises(isolation.IsolationError):
        isolation.compose_argv(name, tmp_path, ["a.yaml"], "up", "-d")


def test_r1_compose_argv_refuses_data_removing_arguments(tmp_path: Path) -> None:
    project = isolation.checkout_project(tmp_path)
    assert isolation.compose_argv(project, tmp_path, ["a.yaml"], "down")[-1] == "down"
    for args in (
        ("down", "-v"),
        ("down", "--volumes"),
        ("down", "--rmi", "all"),
        ("down", "--remove-orphans"),
        ("up", "-d", "--remove-orphans"),
        ("system", "prune"),
        ("rm", "-f"),
    ):
        with pytest.raises(isolation.IsolationError, match="refusing data-removing"):
            isolation.compose_argv(project, tmp_path, ["a.yaml"], *args)
    with pytest.raises(isolation.IsolationError):
        isolation.checkout_project(tmp_path, "Bad Name")


def test_r1_a_compose_check_with_a_forbidden_flag_fails_without_running(tmp_path: Path) -> None:
    path = registry(
        tmp_path,
        "[[check]]\nid='bad'\nunit='p'\nkind='integration'\n"
        "argv=['{compose}', 'down', '-v']\nrequires=['services']\n",
        services=True,
    )
    runner = Recorder()
    code, text = run_main(tmp_path, path, runner=runner)
    assert code == 1
    assert "refusing data-removing compose argument(s): -v" in row(text, "bad")[-1]
    assert runner.docker_calls == []
    code, text = run_main(tmp_path, path, "--list", runner=runner)
    assert code == 0 and "refusing data-removing" in row(text, "bad")[-1]


def test_r1_ports_that_cannot_be_isolated_fail_the_check(tmp_path: Path) -> None:
    path = registry(
        tmp_path, check("i", 'requires = ["services"]', kind="integration"), services=True
    )
    runner = Recorder()
    code, text = run_main(tmp_path, path, runner=runner, free_ports=lambda count: [1])
    assert code == 1
    assert "cannot be isolated" in text
    assert runner.docker_calls == []


def test_r1_a_second_run_in_the_same_checkout_fails_clearly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = registry(tmp_path, check("a"))
    runner = Recorder()
    with isolation.CheckoutLock(tmp_path, "verify"):
        code = verify.main(["--registry", str(path)], runner=runner, probes=probes(), root=tmp_path)
    assert code == 2
    assert "another verification run is using this checkout" in capsys.readouterr().err
    assert runner.calls == []
    assert run_main(tmp_path, path)[0] == 0, "the lock is released after the first run"


def test_r1_lock_is_exclusive_and_released(tmp_path: Path) -> None:
    first = isolation.CheckoutLock(tmp_path)
    first.acquire()
    with pytest.raises(isolation.LockBusyError):
        isolation.CheckoutLock(tmp_path).acquire()
    first.release()
    first.release()
    with isolation.CheckoutLock(tmp_path) as again:
        assert again.path == tmp_path / ".verify-work" / "verify.lock"
    with pytest.raises(isolation.IsolationError):
        isolation.CheckoutLock(tmp_path, "../escape")


def test_r1_free_loopback_ports_are_distinct_numbers() -> None:
    ports = isolation.free_loopback_ports(5)
    assert len(set(ports)) == 5 and all(0 < port < 65536 for port in ports)
    assert isolation.free_loopback_ports(0) == []


def test_keep_running_leaves_the_stack_up(tmp_path: Path) -> None:
    path = registry(
        tmp_path, check("i", 'requires = ["services"]', kind="integration"), services=True
    )
    runner = Recorder()
    _, text = run_main(tmp_path, path, "--keep-running", runner=runner)
    assert [argv for argv in runner.docker_calls if "down" in argv] == []
    assert "left running (--keep-running)" in text


def test_stack_start_failure_fails_the_check_and_still_tears_down(tmp_path: Path) -> None:
    path = registry(
        tmp_path, check("i", 'requires = ["services"]', kind="integration"), services=True
    )
    runner = Recorder({"up": 1, "down": 5})
    code, text = run_main(tmp_path, path, runner=runner)
    assert code == 1
    assert "the verification stack did not start (exit 1)" in text
    assert "'docker compose down' exited 5" in text
    assert not any(_forbidden(argv) for argv in runner.docker_calls)


def test_stack_not_ready_in_time_fails(tmp_path: Path) -> None:
    path = registry(
        tmp_path, check("i", 'requires = ["services"]', kind="integration"), services=True
    )
    code, text = run_main(tmp_path, path, url_ready=lambda url: False)
    assert code == 1
    assert "not ready within 5 s: http://127.0.0.1:41001/health" in text


def test_services_need_docker_and_their_files(tmp_path: Path) -> None:
    path = registry(
        tmp_path, check("i", 'requires = ["services"]', kind="integration"), services=True
    )
    _, text = run_main(tmp_path, path, docker_ready=lambda: False)
    assert "services: Docker CLI or daemon unavailable" in text
    (tmp_path / "stack.yaml").unlink()
    runner = Recorder()
    path.write_text(
        SERVICES + check("i", 'requires = ["services"]', kind="integration"), encoding="utf-8"
    )
    _, text = run_main(tmp_path, path, runner=runner)
    assert "verification stack files are missing" in text
    assert runner.docker_calls == []


def test_repository_registry_is_valid_and_never_removes_data() -> None:
    """The real registry loads, and no check or service command removes data."""
    loaded = verify.load_registry(REPO_ROOT / "scripts" / "verify-checks.toml")
    assert loaded.services is not None
    assert "SLICE_STUDIO_PORT" in loaded.services.ports
    assert dict(loaded.services.env)["SLICE_COMPOSE_PROJECT"] == "{project}"
    for item in loaded.checks:
        assert not _forbidden(item.argv), item.id
        assert not any(r.startswith("free-port:") for r in item.requires), item.id
    ids = {item.id for item in loaded.checks}
    assert {"ruff-check", "mypy", "scripts-tests", "slice-e2e", "slice-integration"} <= ids
    assert {"verify-docker-isolation", "slice-check-unit"} <= ids
    reported = {item.id for item in loaded.checks if item.report == "junit"}
    pytest_checks = {item.id for item in loaded.checks if "pytest" in item.argv}
    assert pytest_checks <= reported


# --- R2: test-level skips in JUnit reports ---------------------------------------------------


def _reported(tmp_path: Path, *extra: str) -> Path:
    return registry(tmp_path, check("tests", 'report = "junit"', *extra))


def test_r2_a_skipped_test_fails_strict_and_is_reported_otherwise(tmp_path: Path) -> None:
    path = _reported(tmp_path)
    xml = junit(("test_ok", None), ("test_symlink", "no symlinks"))
    code, text = run_main(tmp_path, path, "--strict", runner=Recorder(reports={"pass": xml}))
    assert code == 1
    assert row(text, "tests")[3] == "failed"
    assert "--strict: 1 skipped test(s): pkg.mod::test_symlink" in text
    code, text = run_main(tmp_path, path, runner=Recorder(reports={"pass": xml}))
    assert code == 0
    assert row(text, "tests")[-1] == "2 tests; 1 skipped test(s): pkg.mod::test_symlink"


def test_r2_an_allowed_skip_passes_strict_only_on_its_platform(tmp_path: Path) -> None:
    rule = 'allowed_skips = [{ test = "test_symlink", reason = "no links", platforms = ["win32"] }]'
    path = _reported(tmp_path, rule)
    xml = junit(("test_ok", None), ("test_symlink", "no symlinks"))
    code, text = run_main(
        tmp_path, path, "--strict", runner=Recorder(reports={"pass": xml}), platform="win32"
    )
    assert code == 0
    assert "1 allowed skip(s) on win32: pkg.mod::test_symlink (no links)" in text
    code, _ = run_main(
        tmp_path, path, "--strict", runner=Recorder(reports={"pass": xml}), platform="linux"
    )
    assert code == 1


@pytest.mark.parametrize(
    ("xml", "reason"),
    [
        (None, "no JUnit report was written"),
        ("<testsuites>", "cannot be read"),
        (junit(), "the JUnit report lists no tests"),
    ],
)
def test_r2_missing_broken_or_empty_reports_fail(
    tmp_path: Path, xml: str | None, reason: str
) -> None:
    path = _reported(tmp_path)
    runner = Recorder(reports={"pass": xml} if xml is not None else {})
    code, text = run_main(tmp_path, path, runner=runner)
    assert code == 1
    assert reason in row(text, "tests")[-1]


def test_r2_a_failing_command_is_not_judged_by_its_report(tmp_path: Path) -> None:
    path = _reported(tmp_path)
    code, text = run_main(tmp_path, path, runner=Recorder(codes={"pass": 3}))
    assert code == 1 and row(text, "tests")[-1] == "exit 3"


def test_r2_the_report_variables_reach_the_command(tmp_path: Path) -> None:
    (tmp_path / "work").mkdir()
    path = _reported(tmp_path, 'env = { PYTEST_ADDOPTS = "-q" }')
    runner = Recorder(reports={"pass": junit(("t", None))})
    run_main(tmp_path, path, runner=runner)
    env = runner.calls[0][2]
    report = tmp_path / ".verify-work" / "junit" / "tests.xml"
    assert env["VERIFY_JUNIT"] == str(report)
    assert env["VERIFY_JUNIT_NAME"] == "tests.xml"
    assert env["VERIFY_JUNIT_DIR"] == str(report.parent)
    assert env["PYTEST_ADDOPTS"] == "-q", "a check's own env wins"


def test_r2_real_pytest_skips_are_caught_under_strict(tmp_path: Path) -> None:
    """End to end: a real pytest run writes its report through PYTEST_ADDOPTS (a Windows path
    survives the shell-style split), and the skipped test fails --strict."""
    tests = tmp_path / "suite"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        textwrap.dedent(
            """
            import pytest

            def test_runs():
                assert 1 + 1 == 2

            @pytest.mark.skip(reason="needs something this host lacks")
            def test_is_skipped():
                assert False
            """
        ),
        encoding="utf-8",
    )
    (tests / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    path = tmp_path / "checks.toml"
    path.write_text(
        "[[check]]\nid='real'\nunit='project'\nkind='unit'\nreport='junit'\n"
        f"argv=['{PY}', '-m', 'pytest', 'suite', '-p', 'no:cacheprovider', '-q']\n",
        encoding="utf-8",
    )
    out = io.StringIO()
    code = verify.main(["--registry", str(path), "--strict"], root=tmp_path, out=out)
    text = out.getvalue()
    assert code == 1
    assert "1 skipped test(s)" in text and "test_is_skipped" in text
    out = io.StringIO()
    assert verify.main(["--registry", str(path)], root=tmp_path, out=out) == 0
    assert "2 tests; 1 skipped test(s)" in out.getvalue()


def test_read_junit_handles_a_single_testsuite_root(tmp_path: Path) -> None:
    report = tmp_path / "r.xml"
    report.write_text(
        '<testsuite><testcase name="a"/><testcase name="b"><skipped>why\n not</skipped>'
        "</testcase></testsuite>",
        encoding="utf-8",
    )
    assert verify.read_junit(report) == verify.TestReport(2, (("b", "why not"),))


# --- real probes -----------------------------------------------------------------------------


def test_real_probes() -> None:
    assert verify._has_module("json") is True
    assert verify._has_module("no_such_module_here") is False
    assert verify._url_ready("http://127.0.0.1:1/") is False
    assert isinstance(verify._port_free(1), bool)
    assert isinstance(verify._docker_ready(), bool)
