"""Project-wide verification entry point.

Runs every check registered in ``scripts/verify-checks.toml``: formatting, linting, type
checking, tests with coverage, contract tests, the build-output guard, integration and
end-to-end tests, and audits. Units add their own ``[[check]]`` entries to the registry
when they are implemented; this script does not change.

For each check:

- ``applies_when`` paths must all exist, otherwise the check is *not applicable* (the unit
  is not on this branch) and is not counted as a skip;
- ``requires`` prerequisites must be met, otherwise the check is *skipped* with the reason:
  ``docker`` (CLI present and daemon reachable), ``services`` (the verification stack,
  started on demand), ``path:<p>``, ``tool:<name>`` on PATH, ``module:<name>`` importable by
  this Python, ``free-port:<n>`` (nothing listening on that local port);
- otherwise it runs, with its output streamed, and *passes* on exit code 0.

A check with ``report = "junit"`` writes a JUnit XML report into the work directory
(``.verify-work/junit/<id>.xml``): pytest through ``PYTEST_ADDOPTS``, Vitest through the
``VERIFY_JUNIT`` variable its configuration reads. The report must exist, list at least one
test, and, under ``--strict``, contain no skipped test unless the check's ``allowed_skips``
lists it (with a reason, optionally for some platforms only).

Integration and end-to-end checks share one Compose project per checkout
(``portfolio-verify-<checkout id>``, see ``scripts/compose_isolation.py``), never the
developer's own stack and never another worktree's. Its host ports are chosen free for each
run and passed through the registry's ``[services] ports`` variables. It is started once,
before the first check that needs it, and stopped with a plain ``docker compose down``
(containers and network) at the end unless ``--keep-running``. A lock file stops two runs in
the same checkout from overlapping. This script never removes volumes, images or files other
than its own reports.

Usage::

    python scripts/verify.py --strict          # everything that applies
    python scripts/verify.py --unit walking-slice
    python scripts/verify.py --kind unit --kind contract
    python scripts/verify.py --list            # registry, applicability, prerequisites

Exit codes: 0 nothing required failed; 1 a check failed (or, with ``--strict``, a required
applicable check or a test inside one was skipped); 2 a usage, registry or lock error.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
import xml.etree.ElementTree as ElementTree
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from compose_isolation import (
    CheckoutLock,
    IsolationError,
    checkout_project,
    compose_argv,
    free_loopback_ports,
    work_dir,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "scripts" / "verify-checks.toml"
KINDS: tuple[str, ...] = ("static", "unit", "contract", "integration", "e2e", "audit")
PASSED, FAILED, SKIPPED, NOT_APPLICABLE = "passed", "failed", "skipped", "not applicable"
REQUIREMENT_WORDS: frozenset[str] = frozenset({"docker", "services"})
REQUIREMENT_PREFIXES: tuple[str, ...] = ("path:", "tool:", "module:", "free-port:")
TOOL_PLACEHOLDERS: dict[str, str] = {"{npm}": "npm", "{npx}": "npx"}
COMPOSE_PLACEHOLDER = "{compose}"
REPORT_KINDS: frozenset[str] = frozenset({"junit"})
PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
DEFAULT_TIMEOUT = 1200.0
EXIT_TIMEOUT, EXIT_NOT_RUNNABLE = 124, 127

Runner = Callable[[Sequence[str], Path, Mapping[str, str], float], int]


class RegistryError(Exception):
    """The registry cannot be read or is invalid."""


class ReportError(Exception):
    """A JUnit report is missing or cannot be read."""


@dataclass(frozen=True)
class AllowedSkip:
    """A test that may be skipped under --strict, with the reason (and platforms)."""

    test: str
    reason: str
    platforms: tuple[str, ...] = ()

    def matches(self, name: str, platform: str) -> bool:
        return self.test in name and (not self.platforms or platform in self.platforms)


@dataclass(frozen=True)
class Check:
    """One registered check."""

    id: str
    unit: str
    kind: str
    argv: tuple[str, ...]
    cwd: str = "."
    env: tuple[tuple[str, str], ...] = ()
    applies_when: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    required: bool = True
    timeout: float = DEFAULT_TIMEOUT
    description: str = ""
    report: str = ""
    allowed_skips: tuple[AllowedSkip, ...] = ()


@dataclass(frozen=True)
class Services:
    """The verification stack: compose files, per-run port variables, readiness URLs."""

    compose_files: tuple[str, ...]
    env: tuple[tuple[str, str], ...] = ()
    ready_urls: tuple[str, ...] = ()
    ready_timeout: float = 300.0
    applies_when: tuple[str, ...] = ()
    ports: tuple[str, ...] = ()


@dataclass(frozen=True)
class Registry:
    checks: tuple[Check, ...]
    services: Services | None = None


@dataclass(frozen=True)
class Result:
    check: Check
    status: str
    seconds: float = 0.0
    reason: str = ""


@dataclass(frozen=True)
class TestReport:
    """What a JUnit report says: how many tests ran and which were skipped."""

    tests: int
    skipped: tuple[tuple[str, str], ...] = ()


# --- registry --------------------------------------------------------------------------


def _strings(value: object, where: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise RegistryError(f"{where} must be a list of non-empty strings")
    return tuple(value)


def _mapping(value: object, where: str) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    if not isinstance(value, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    ):
        raise RegistryError(f"{where} must be a table of string values")
    return tuple(sorted(value.items()))


def _requirement_ok(requirement: str) -> bool:
    if requirement in REQUIREMENT_WORDS:
        return True
    return any(
        requirement.startswith(p) and len(requirement) > len(p) for p in REQUIREMENT_PREFIXES
    )


def _parse_allowed_skips(value: object, where: str) -> tuple[AllowedSkip, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise RegistryError(f"{where} must be a list of tables")
    rules: list[AllowedSkip] = []
    for index, raw in enumerate(value):
        here = f"{where}[{index}]"
        if not isinstance(raw, dict) or set(raw) - {"test", "reason", "platforms"}:
            raise RegistryError(f"{here} must be a table of test, reason and platforms")
        test, reason = raw.get("test"), raw.get("reason")
        if not isinstance(test, str) or not test or not isinstance(reason, str) or not reason:
            raise RegistryError(f"{here} needs a non-empty test and a non-empty reason")
        platforms = _strings(raw.get("platforms"), f"{here}.platforms")
        rules.append(AllowedSkip(test, reason, platforms))
    return tuple(rules)


def _parse_check(raw: object, index: int) -> Check:
    where = f"check[{index}]"
    if not isinstance(raw, dict):
        raise RegistryError(f"{where} must be a table")
    allowed = {
        "id", "unit", "kind", "argv", "cwd", "env", "applies_when", "requires", "required",
        "timeout", "description", "report", "allowed_skips",
    }  # fmt: skip
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise RegistryError(f"{where} has unknown field(s): {', '.join(unknown)}")
    for key in ("id", "unit", "kind"):
        if not isinstance(raw.get(key), str) or not raw[key]:
            raise RegistryError(f"{where}.{key} must be a non-empty string")
    where = f"check '{raw['id']}'"
    if raw["kind"] not in KINDS:
        raise RegistryError(f"{where}: kind must be one of {', '.join(KINDS)}")
    argv = _strings(raw.get("argv"), f"{where}.argv")
    if not argv:
        raise RegistryError(f"{where}.argv must not be empty")
    requires = _strings(raw.get("requires"), f"{where}.requires")
    bad = [r for r in requires if not _requirement_ok(r)]
    if bad:
        raise RegistryError(f"{where}: unknown prerequisite(s) {', '.join(bad)}")
    if COMPOSE_PLACEHOLDER in argv:
        if argv[0] != COMPOSE_PLACEHOLDER or argv.count(COMPOSE_PLACEHOLDER) > 1:
            raise RegistryError(f"{where}: {COMPOSE_PLACEHOLDER} may only be argv[0]")
        if "services" not in requires:
            raise RegistryError(f"{where}: {COMPOSE_PLACEHOLDER} needs requires = ['services']")
    required = raw.get("required", True)
    timeout = raw.get("timeout", DEFAULT_TIMEOUT)
    if not isinstance(required, bool):
        raise RegistryError(f"{where}.required must be true or false")
    if not isinstance(timeout, int | float) or timeout <= 0:
        raise RegistryError(f"{where}.timeout must be a positive number")
    cwd = raw.get("cwd", ".")
    description = raw.get("description", "")
    report = raw.get("report", "")
    if not isinstance(cwd, str) or not isinstance(description, str):
        raise RegistryError(f"{where}: cwd and description must be strings")
    if report != "" and report not in REPORT_KINDS:
        raise RegistryError(f"{where}.report must be one of {', '.join(sorted(REPORT_KINDS))}")
    allowed_skips = _parse_allowed_skips(raw.get("allowed_skips"), f"{where}.allowed_skips")
    if allowed_skips and not report:
        raise RegistryError(f"{where}: allowed_skips needs report = 'junit'")
    return Check(
        id=raw["id"],
        unit=raw["unit"],
        kind=raw["kind"],
        argv=argv,
        cwd=cwd,
        env=_mapping(raw.get("env"), f"{where}.env"),
        applies_when=_strings(raw.get("applies_when"), f"{where}.applies_when"),
        requires=requires,
        required=required,
        timeout=float(timeout),
        description=description,
        report=str(report),
        allowed_skips=allowed_skips,
    )


def _check_placeholders(texts: Sequence[str], known: set[str], where: str) -> None:
    for text in texts:
        unknown = sorted(set(PLACEHOLDER.findall(text)) - known)
        if unknown:
            raise RegistryError(f"{where}: unknown placeholder(s) {', '.join(unknown)}")


def _parse_services(raw: object) -> Services:
    if not isinstance(raw, dict):
        raise RegistryError("[services] must be a table")
    if "project" in raw:
        raise RegistryError(
            "services.project is not accepted: the Compose project is derived per checkout"
        )
    allowed = {"compose_files", "env", "ready_urls", "ready_timeout", "applies_when", "ports"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise RegistryError(f"[services] has unknown field(s): {', '.join(unknown)}")
    files = _strings(raw.get("compose_files"), "services.compose_files")
    if not files:
        raise RegistryError("services.compose_files must not be empty")
    ready_timeout = raw.get("ready_timeout", 300)
    if not isinstance(ready_timeout, int | float) or ready_timeout <= 0:
        raise RegistryError("services.ready_timeout must be a positive number")
    ports = _strings(raw.get("ports"), "services.ports")
    if any(not ENV_NAME.match(p) for p in ports) or len(set(ports)) != len(ports):
        raise RegistryError("services.ports must be distinct UPPER_CASE variable names")
    env = _mapping(raw.get("env"), "services.env")
    ready_urls = _strings(raw.get("ready_urls"), "services.ready_urls")
    known = {"project", *ports}
    _check_placeholders([value for _, value in env], known, "services.env")
    _check_placeholders(ready_urls, known, "services.ready_urls")
    return Services(
        compose_files=files,
        env=env,
        ready_urls=ready_urls,
        ready_timeout=float(ready_timeout),
        applies_when=_strings(raw.get("applies_when"), "services.applies_when"),
        ports=ports,
    )


def load_registry(path: Path) -> Registry:
    """Read and validate the registry; raise RegistryError on any problem."""
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise RegistryError(f"cannot read {path}: {error}") from error
    raw_checks = document.get("check", [])
    if not isinstance(raw_checks, list) or not raw_checks:
        raise RegistryError(f"{path} defines no [[check]] entries")
    checks = tuple(_parse_check(raw, index) for index, raw in enumerate(raw_checks))
    ids = [c.id for c in checks]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise RegistryError(f"duplicate check id(s): {', '.join(duplicates)}")
    services = _parse_services(document["services"]) if "services" in document else None
    if services is None and any("services" in c.requires for c in checks):
        raise RegistryError("a check requires 'services' but the registry has no [services]")
    return Registry(checks=checks, services=services)


def select(checks: Sequence[Check], unit: str | None, kinds: Sequence[str]) -> list[Check]:
    """Keep the checks of one unit and of the given kinds (all, when empty)."""
    return [
        c for c in checks if (unit is None or c.unit == unit) and (not kinds or c.kind in kinds)
    ]


def expand(text: str, values: Mapping[str, str]) -> str:
    """Replace ``{name}`` placeholders that ``values`` knows; leave the rest unchanged."""
    return PLACEHOLDER.sub(lambda m: values.get(m.group(1), m.group(0)), text)


# --- JUnit reports -----------------------------------------------------------------------


def read_junit(path: Path) -> TestReport:
    """Count the test cases of a JUnit XML report and list the skipped ones."""
    if not path.is_file():
        raise ReportError(f"no JUnit report was written ({path})")
    try:
        # The report is a local file this run's own test command just wrote.
        root = ElementTree.parse(path).getroot()  # noqa: S314
    except (OSError, ElementTree.ParseError) as error:
        raise ReportError(f"the JUnit report {path} cannot be read: {error}") from error
    tests = 0
    skipped: list[tuple[str, str]] = []
    for case in root.iter("testcase"):
        tests += 1
        marker = case.find("skipped")
        if marker is None:
            continue
        classname = case.get("classname", "")
        name = f"{classname}::{case.get('name', '')}" if classname else case.get("name", "")
        message = marker.get("message") or (marker.text or "").strip()
        skipped.append((name, " ".join(message.split())[:160]))
    return TestReport(tests, tuple(skipped))


# --- probes ----------------------------------------------------------------------------


def _docker_ready() -> bool:
    docker = shutil.which("docker")
    if docker is None:
        return False
    try:
        completed = subprocess.run(
            [docker, "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _port_free(port: int) -> bool:
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as probe:
                probe.settimeout(0.5)
                if probe.connect_ex((host, port)) == 0:
                    return False
        except OSError:
            continue
    return True


def _url_ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:  # noqa: S310 - local URL
            return bool(response.status == 200)
    except (urllib.error.URLError, OSError):
        return False


def _has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


@dataclass
class Probes:
    """Questions about the machine; injectable for tests."""

    which: Callable[[str], str | None] = shutil.which
    has_module: Callable[[str], bool] = _has_module
    docker_ready: Callable[[], bool] = _docker_ready
    port_free: Callable[[int], bool] = _port_free
    url_ready: Callable[[str], bool] = _url_ready
    free_ports: Callable[[int], list[int]] = free_loopback_ports
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    platform: str = sys.platform


def default_runner(argv: Sequence[str], cwd: Path, env: Mapping[str, str], timeout: float) -> int:
    """Run a command with its output streamed to this console."""
    try:
        return subprocess.run(
            list(argv), cwd=cwd, env=dict(env), timeout=timeout, check=False
        ).returncode
    except subprocess.TimeoutExpired:
        print(f"verify: timed out after {timeout:.0f} s", flush=True)
        return EXIT_TIMEOUT
    except OSError as error:
        print(f"verify: cannot run {argv[0]}: {error}", flush=True)
        return EXIT_NOT_RUNNABLE


# --- running ---------------------------------------------------------------------------


@dataclass
class Verifier:
    """Runs selected checks against one repository root."""

    root: Path
    registry: Registry
    runner: Runner = default_runner
    probes: Probes = field(default_factory=Probes)
    strict: bool = False
    keep_running: bool = False
    out: TextIO = sys.stdout
    namespace: str = ""
    _services_state: str | None = None
    _services_started: bool = False
    _docker: bool | None = None
    _ports: dict[str, str] = field(default_factory=dict)

    @property
    def project(self) -> str:
        """This checkout's Compose project (``portfolio-verify-<checkout id>``)."""
        return checkout_project(self.root, self.namespace)

    def compose(self, *args: str) -> list[str]:
        """The isolated ``docker compose`` argv for the verification stack."""
        services = self.registry.services
        files = services.compose_files if services is not None else ()
        return compose_argv(self.project, self.root, files, *args)

    def _docker_ready(self) -> bool:
        if self._docker is None:
            self._docker = self.probes.docker_ready()
        return self._docker

    def _say(self, text: str) -> None:
        print(text, file=self.out, flush=True)

    def missing_paths(self, paths: Sequence[str]) -> list[str]:
        return [p for p in paths if not (self.root / p).exists()]

    def services_applicable(self) -> bool:
        services = self.registry.services
        return services is not None and not self.missing_paths(services.applies_when)

    def unmet_prerequisites(self, check: Check) -> list[str]:
        """The prerequisites that are not met (without starting anything)."""
        unmet: list[str] = []
        for requirement in check.requires:
            if requirement in ("docker", "services"):
                if not self._docker_ready():
                    unmet.append(f"{requirement}: Docker CLI or daemon unavailable")
                elif requirement == "services" and not self.services_applicable():
                    unmet.append("services: the verification stack files are missing")
            elif requirement.startswith("path:"):
                if not (self.root / requirement[5:]).exists():
                    unmet.append(f"missing {requirement[5:]}")
            elif requirement.startswith("tool:"):
                if self.probes.which(requirement[5:]) is None:
                    unmet.append(f"{requirement[5:]} not on PATH")
            elif requirement.startswith("module:"):
                if not self.probes.has_module(requirement[7:]):
                    unmet.append(f"Python module {requirement[7:]} not installed")
            elif requirement.startswith("free-port:") and not self.probes.port_free(
                int(requirement[10:])
            ):
                unmet.append(f"port {requirement[10:]} is in use")
        return unmet

    def resolve_argv(self, check: Check) -> tuple[list[str] | None, str]:
        """Fill in the placeholders. A ``{compose}`` check (always argv[0]) gets the isolated
        compose prefix, and every argument after it is checked for data-removing flags."""
        if check.argv[0] == COMPOSE_PLACEHOLDER:
            return self.compose(*check.argv[1:]), ""
        argv: list[str] = []
        for part in check.argv:
            if part == "{python}":
                argv.append(sys.executable)
            elif part in TOOL_PLACEHOLDERS:
                found = self.probes.which(TOOL_PLACEHOLDERS[part])
                if found is None:
                    return None, f"{TOOL_PLACEHOLDERS[part]} not on PATH"
                argv.append(found)
            else:
                argv.append(part)
        return argv, ""

    def services_env(self) -> dict[str, str]:
        """The chosen ports and the registry's services variables, placeholders filled in."""
        services = self.registry.services
        if services is None:
            return {}
        values = {"project": self.project, **self._ports}
        env = {**self._ports, **{k: expand(v, values) for k, v in services.env}}
        # Containers that write into the work directory (test reports) run as this user on
        # POSIX hosts, so the files stay writable by the next run. Windows has no uid.
        getuid = getattr(os, "getuid", None)
        getgid = getattr(os, "getgid", None)
        if callable(getuid) and callable(getgid):
            env["VERIFY_UID"], env["VERIFY_GID"] = str(getuid()), str(getgid())
        return env

    def report_path(self, check: Check) -> Path:
        return work_dir(self.root) / "junit" / f"{check.id}.xml"

    def environment(self, check: Check) -> dict[str, str]:
        env = dict(os.environ)
        if "services" in check.requires:
            env.update(self.services_env())
        if check.report:
            report = self.report_path(check)
            # PYTEST_ADDOPTS is split like a shell line; forward slashes survive on Windows.
            option = f'--junitxml="{report.as_posix()}"'
            env["PYTEST_ADDOPTS"] = f"{env.get('PYTEST_ADDOPTS', '')} {option}".strip()
            env["VERIFY_JUNIT"] = str(report)
            env["VERIFY_JUNIT_DIR"] = str(report.parent)
            env["VERIFY_JUNIT_NAME"] = report.name
        env.update(dict(check.env))
        return env

    def _wait_until_ready(self, services: Services) -> str:
        values = {"project": self.project, **self._ports}
        deadline = self.probes.clock() + services.ready_timeout
        pending = [expand(url, values) for url in services.ready_urls]
        while pending and self.probes.clock() < deadline:
            pending = [url for url in pending if not self.probes.url_ready(url)]
            if pending:
                self.probes.sleep(1.0)
        if pending:
            return f"not ready within {services.ready_timeout:.0f} s: {', '.join(pending)}"
        return ""

    def _ensure_services(self) -> str:
        """Start the verification stack once; return '' when ready, or the failure reason."""
        if self._services_state is not None:
            return self._services_state
        services = self.registry.services
        if services is None:  # load_registry refuses this; kept for a clear message
            self._services_state = "the registry defines no [services]"
            return self._services_state
        try:
            ports = self.probes.free_ports(len(services.ports))
            self._ports = {
                name: str(port) for name, port in zip(services.ports, ports, strict=True)
            }
            up = self.compose("up", "-d", "--build", "--force-recreate")
        except (IsolationError, ValueError) as error:
            self._services_state = f"the verification stack cannot be isolated: {error}"
            return self._services_state
        chosen = ", ".join(f"{k}={v}" for k, v in self._ports.items()) or "none"
        self._say(
            f"\n== services: starting Compose project '{self.project}' on free loopback ports "
            f"({chosen}); no data is removed"
        )
        self._say(f"$ {' '.join(up)}")
        self._services_started = True
        code = self.runner(up, self.root, {**os.environ, **self.services_env()}, DEFAULT_TIMEOUT)
        if code != 0:
            self._services_state = f"the verification stack did not start (exit {code})"
            return self._services_state
        self._services_state = self._wait_until_ready(services)
        return self._services_state

    def stop_services(self) -> None:
        services = self.registry.services
        if not self._services_started or services is None:
            return
        down = self.compose("down")
        if self.keep_running:
            self._say(f"\n== services: left running (--keep-running). Stop with: {' '.join(down)}")
            return
        self._say(
            f"\n== services: stopping '{self.project}' (containers and network; volumes kept)"
        )
        self._say(f"$ {' '.join(down)}")
        code = self.runner(down, self.root, {**os.environ, **self.services_env()}, DEFAULT_TIMEOUT)
        if code != 0:
            self._say(f"verify: warning: 'docker compose down' exited {code}")

    def _judge_report(self, check: Check, seconds: float) -> Result:
        try:
            report = read_junit(self.report_path(check))
        except ReportError as error:
            return Result(check, FAILED, seconds, str(error))
        if report.tests == 0:
            return Result(check, FAILED, seconds, "the JUnit report lists no tests")
        platform = self.probes.platform
        allowed: dict[str, str] = {}
        for name, _ in report.skipped:
            rule = next((r for r in check.allowed_skips if r.matches(name, platform)), None)
            if rule is not None:
                allowed[name] = rule.reason
        unallowed = [name for name, _ in report.skipped if name not in allowed]
        notes = [f"{report.tests} tests"]
        if allowed:
            notes.append(
                f"{len(allowed)} allowed skip(s) on {platform}: "
                + "; ".join(f"{name} ({reason})" for name, reason in allowed.items())
            )
        if unallowed:
            text = f"{len(unallowed)} skipped test(s): {', '.join(unallowed)}"
            if self.strict:
                return Result(check, FAILED, seconds, f"--strict: {text}")
            notes.append(text)
        return Result(check, PASSED, seconds, "; ".join(notes))

    def run_one(self, check: Check) -> Result:
        missing = self.missing_paths(check.applies_when)
        if missing:
            return Result(check, NOT_APPLICABLE, reason=f"missing {', '.join(missing)}")
        unmet = self.unmet_prerequisites(check)
        try:
            argv, unresolved = self.resolve_argv(check)
        except IsolationError as error:
            return Result(check, FAILED, reason=str(error))
        if unresolved:
            unmet.append(unresolved)
        optional = "" if check.required else " (optional)"
        if unmet or argv is None:
            return Result(check, SKIPPED, reason="; ".join(unmet) + optional)
        if "services" in check.requires:
            problem = self._ensure_services()
            if problem:
                return Result(check, FAILED, reason=problem)
        if check.report:
            report = self.report_path(check)
            report.parent.mkdir(parents=True, exist_ok=True)
            report.unlink(missing_ok=True)
        self._say(f"\n== [{check.unit}] {check.id} ({check.kind}): {' '.join(check.argv)}")
        started = self.probes.clock()
        code = self.runner(argv, self.root / check.cwd, self.environment(check), check.timeout)
        seconds = self.probes.clock() - started
        if code != 0:
            return Result(check, FAILED, seconds, f"exit {code}")
        if check.report:
            return self._judge_report(check, seconds)
        return Result(check, PASSED, seconds)

    def run(self, checks: Sequence[Check]) -> list[Result]:
        results: list[Result] = []
        try:
            for check in checks:
                results.append(self.run_one(check))
        finally:
            self.stop_services()
        return results


# --- reporting -------------------------------------------------------------------------


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    widths = [max(len(header[i]), *(len(r[i]) for r in rows)) for i in range(len(header))]
    line = "  ".join(h.ljust(w) for h, w in zip(header, widths, strict=True))
    lines = [line, "  ".join("-" * w for w in widths)]
    lines += ["  ".join(c.ljust(w) for c, w in zip(row, widths, strict=True)) for row in rows]
    return "\n".join(line.rstrip() for line in lines)


def summary(results: Sequence[Result]) -> str:
    rows = [
        [r.check.id, r.check.unit, r.check.kind, r.status, f"{r.seconds:.1f}", r.reason]
        for r in results
    ]
    return _table(["check", "unit", "kind", "status", "seconds", "reason"], rows)


def exit_code(results: Sequence[Result], strict: bool) -> int:
    if any(r.status == FAILED for r in results):
        return 1
    if strict and any(r.status == SKIPPED and r.check.required for r in results):
        return 1
    return 0


def verdict(results: Sequence[Result], strict: bool) -> str:
    counts = {
        s: sum(1 for r in results if r.status == s)
        for s in (PASSED, FAILED, SKIPPED, NOT_APPLICABLE)
    }
    required_skips = [r.check.id for r in results if r.status == SKIPPED and r.check.required]
    text = (
        f"{counts[PASSED]} passed, {counts[FAILED]} failed, {counts[SKIPPED]} skipped, "
        f"{counts[NOT_APPLICABLE]} not applicable"
    )
    if exit_code(results, strict) == 0:
        return f"verify: OK ({text})"
    reason = ""
    if strict and required_skips and not counts[FAILED]:
        reason = f"; --strict: required checks skipped: {', '.join(required_skips)}"
    return f"verify: FAILED ({text}{reason})"


def listing(verifier: Verifier, checks: Sequence[Check]) -> str:
    rows = []
    for check in checks:
        missing = verifier.missing_paths(check.applies_when)
        applies = f"no (missing {', '.join(missing)})" if missing else "yes"
        unmet = verifier.unmet_prerequisites(check) if not missing else []
        if not missing:
            try:
                _, unresolved = verifier.resolve_argv(check)
            except IsolationError as error:
                unresolved = str(error)
            unmet += [unresolved] if unresolved else []
        tools = [p for p in check.argv if p in TOOL_PLACEHOLDERS]
        if unmet:
            unmet_text = "; ".join(unmet)
        elif "services" in check.requires:
            unmet_text = "ok (stack started on demand)"
        else:
            unmet_text = "ok" if check.requires or tools else "none"
        rows.append(
            [
                check.id,
                check.unit,
                check.kind,
                "yes" if check.required else "no",
                applies,
                unmet_text,
            ]
        )
    table = _table(["check", "unit", "kind", "required", "applies", "prerequisites"], rows)
    if verifier.registry.services is not None:
        table += (
            f"\nservices: Compose project {verifier.project}; host ports chosen free per run; "
            f"lock {work_dir(verifier.root) / 'verify.lock'}"
        )
    return table


def main(
    argv: Sequence[str] | None = None,
    runner: Runner = default_runner,
    probes: Probes | None = None,
    root: Path = ROOT,
    out: TextIO | None = None,
) -> int:
    """Command-line entry point."""
    stream = out if out is not None else sys.stdout
    parser = argparse.ArgumentParser(description="Project-wide verification.")
    parser.add_argument("--registry", type=Path, default=None, help="registry file (TOML)")
    parser.add_argument("--unit", help="run only this unit's checks (e.g. walking-slice)")
    parser.add_argument("--kind", action="append", default=[], choices=KINDS, help="repeatable")
    parser.add_argument("--list", action="store_true", help="show the registry; run nothing")
    parser.add_argument("--strict", action="store_true", help="a skipped required check fails")
    parser.add_argument("--keep-running", action="store_true", help="leave the stack up")
    args = parser.parse_args(argv)
    registry_path = (
        args.registry if args.registry is not None else root / "scripts" / "verify-checks.toml"
    )
    try:
        registry = load_registry(registry_path)
    except RegistryError as error:
        print(f"verify: registry error: {error}", file=sys.stderr)
        return 2
    if args.unit is not None and args.unit not in {c.unit for c in registry.checks}:
        units = ", ".join(sorted({c.unit for c in registry.checks}))
        print(f"verify: unknown unit '{args.unit}' (registered: {units})", file=sys.stderr)
        return 2
    checks = select(registry.checks, args.unit, args.kind)
    if not checks:
        print("verify: no checks match the selection", file=sys.stderr)
        return 2
    verifier = Verifier(
        root=root,
        registry=registry,
        runner=runner,
        probes=probes if probes is not None else Probes(),
        strict=args.strict,
        keep_running=args.keep_running,
        out=stream,
    )
    if args.list:
        print(listing(verifier, checks), file=stream)
        return 0
    try:
        with CheckoutLock(root, "verify"):
            results = verifier.run(checks)
    except IsolationError as error:
        print(f"verify: {error}", file=sys.stderr)
        return 2
    print("\n== verify summary", file=stream)
    print(summary(results), file=stream)
    print(verdict(results, args.strict), file=stream, flush=True)
    return exit_code(results, args.strict)


if __name__ == "__main__":
    sys.exit(main())
