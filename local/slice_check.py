"""LOCAL-ONLY: the walking slice end-to-end check (W6), run by ``make slice-check`` and by
``scripts/verify.py`` (check ``slice-e2e``).

It runs in this checkout's own Compose project, never the developer's own stack and never
another worktree's (the rules are in ``scripts/compose_isolation.py``):

- the project is ``portfolio-verify-<checkout id>``; ``portfolio-slice`` and any name that
  does not start with ``portfolio-verify-`` are refused;
- the host ports are free loopback ports chosen for this run (API, site, issuer, MongoDB and
  the Studio dev server);
- a lock file in ``.verify-work/`` stops two runs in the same checkout from overlapping;
- it never runs ``down -v``, ``--volumes``, ``--rmi``, ``--remove-orphans`` or a prune, and
  never removes a volume. Teardown is a plain ``down``.

Steps, each of which must pass (the check exits non-zero on any failure):

1. assert that the Compose configuration publishes nothing on a non-loopback host address
   (NFR1.2);
2. start the stack, or use the one the caller started: with ``SLICE_STACK_MANAGED=1``
   (set by scripts/verify.py, which also holds the lock and passes the project and ports)
   this script neither starts nor stops it. Otherwise it runs
   ``up -d --build --force-recreate`` and, at the end, ``down`` unless ``--keep-running``;
3. assert that the database is empty (REL-0.2). The tmpfs database is empty in every new
   container, so nothing has to be deleted. The ``site`` volume may hold earlier releases;
   the API reconciles them against the empty database;
4. run the Playwright journey (web/slice-e2e): create, save, preview and publish in the
   Studio page, the static page, the C9 headers on a 200 and a 404, and the timings
   (NFR6.1, NFR6.2);
5. export the published release and its snapshot, and run the public-output allow-list scan
   (scripts/scan_output.py; AC0.9), including the byte-for-byte check of every published
   image against the committed digests of the authorized fixture derivatives (R3).

Settings, from the environment: SLICE_COMPOSE_PROJECT (must be a verification project),
SLICE_COMPOSE_FILES (comma-separated, relative to the repository root), SLICE_API_PORT,
SLICE_SITE_PORT, SLICE_IDP_PORT, SLICE_MONGO_PORT, SLICE_STUDIO_PORT and SLICE_STACK_MANAGED.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compose_isolation import (  # noqa: E402 - scripts/ is added to the path above
    CheckoutLock,
    IsolationError,
    checkout_project,
    compose_argv,
    free_loopback_ports,
    validate_project,
)

WORK_DIR = ROOT / "local" / ".slice-check"
LOOPBACK = "127.0.0.1"
READY_TIMEOUT_SECONDS = 300
DEFAULT_COMPOSE_FILES = "local/compose.yaml,local/compose.verify.yaml"
PORT_VARIABLES: dict[str, str] = {
    "api": "SLICE_API_PORT",
    "site": "SLICE_SITE_PORT",
    "idp": "SLICE_IDP_PORT",
    "mongo": "SLICE_MONGO_PORT",
    "studio": "SLICE_STUDIO_PORT",
}


class SliceCheckError(RuntimeError):
    """One step of the slice check failed."""


def _port(name: str, value: str) -> str:
    if not value.isdigit() or not 0 < int(value) < 65536:
        raise SliceCheckError(f"{name} must be a port number, not {value!r}")
    return value


@dataclass(frozen=True)
class Stack:
    """Which Compose project and ports the check uses."""

    project: str
    compose_files: tuple[str, ...]
    ports: Mapping[str, str]
    managed: bool
    root: Path = field(default=ROOT)

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str],
        root: Path = ROOT,
        free_ports: Callable[[int], list[int]] = free_loopback_ports,
    ) -> Stack:
        """Read the settings; refuse any project that is not this checkout's kind."""
        managed = environ.get("SLICE_STACK_MANAGED", "") == "1"
        try:
            project = validate_project(
                environ.get("SLICE_COMPOSE_PROJECT", "").strip() or checkout_project(root)
            )
        except IsolationError as error:
            raise SliceCheckError(str(error)) from error
        files_text = environ.get("SLICE_COMPOSE_FILES", "").strip() or DEFAULT_COMPOSE_FILES
        files = tuple(f.strip() for f in files_text.split(",") if f.strip())
        given = {key: environ.get(var, "").strip() for key, var in PORT_VARIABLES.items()}
        missing = [key for key, value in given.items() if not value]
        if managed and missing:
            names = ", ".join(PORT_VARIABLES[key] for key in missing)
            raise SliceCheckError(f"SLICE_STACK_MANAGED=1 but the caller did not pass {names}")
        chosen = dict(zip(missing, (str(p) for p in free_ports(len(missing))), strict=True))
        ports = {key: _port(PORT_VARIABLES[key], given[key] or chosen[key]) for key in given}
        return cls(project, files, ports, managed, root)

    def env(self) -> dict[str, str]:
        """The environment for Compose and Playwright: the chosen host ports."""
        return {
            **os.environ,
            **{PORT_VARIABLES[key]: value for key, value in self.ports.items()},
        }

    def compose(self, *args: str) -> list[str]:
        try:
            return compose_argv(self.project, self.root, self.compose_files, *args)
        except IsolationError as error:
            raise SliceCheckError(str(error)) from error

    def url(self, port: str) -> str:
        return f"http://{LOOPBACK}:{self.ports[port]}"


def run(command: Sequence[str], cwd: Path = ROOT, env: Mapping[str, str] | None = None) -> str:
    """Run a command, echoing it; raise SliceCheckError on a non-zero exit."""
    print(f"$ {' '.join(command)}", flush=True)
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        output = (completed.stdout + completed.stderr).strip()
        raise SliceCheckError(f"{command[0]} exited {completed.returncode}:\n{output[-4000:]}")
    return completed.stdout


def wait_for(url: str, timeout: float = READY_TIMEOUT_SECONDS) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:  # noqa: S310 - local URL
                if response.status == 200:
                    return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1)
    raise SliceCheckError(f"{url} did not answer 200 within {timeout:.0f} s")


def assert_loopback_only(stack: Stack) -> None:
    """NFR1.2: every published port binds 127.0.0.1."""
    config = json.loads(run(stack.compose("config", "--format", "json"), env=stack.env()))
    published = []
    for name, service in config.get("services", {}).items():
        for port in service.get("ports", []) or []:
            host_ip = port.get("host_ip") if isinstance(port, dict) else None
            if host_ip != LOOPBACK:
                raise SliceCheckError(
                    f"service {name} publishes a port on {host_ip or 'every address'}"
                )
            published.append(f"{name}:{host_ip}:{port.get('published')}")
    if not published:
        raise SliceCheckError("the Compose file publishes no ports at all")
    print(f"  project {stack.project}; loopback only: {', '.join(published)}")


def start_stack(stack: Stack) -> None:
    """Start the isolated stack (unless the caller manages it) and wait until it answers."""
    if stack.managed:
        print(f"  stack '{stack.project}' is managed by the caller")
    else:
        run(stack.compose("up", "-d", "--build", "--force-recreate"), env=stack.env())
    wait_for(f"{stack.url('api')}/health")
    wait_for(f"{stack.url('site')}/")


def assert_empty_database(stack: Stack) -> None:
    """REL-0.2: the tmpfs database holds no projects or versions when the check starts."""
    query = (
        "print(db.slice_projects.countDocuments({}) + "
        "db.slice_published_versions.countDocuments({}))"
    )
    argv = ["exec", "-T", "mongo", "mongosh", "--quiet", "portfolio_slice", "--eval", query]
    count = run(stack.compose(*argv), env=stack.env()).strip()
    if count != "0":
        raise SliceCheckError(
            f"the database is not empty ({count} documents); was the stack kept running "
            "from an earlier run? Restart it so the tmpfs database is fresh"
        )
    print("  database empty")


def run_playwright(stack: Stack) -> None:
    npx = shutil.which("npx")
    if npx is None:
        raise SliceCheckError("npx was not found; install Node 22 (see local/SLICE.md)")
    env = {
        **stack.env(),
        "PLAYWRIGHT_BROWSERS_PATH": "0",
        "SLICE_API_URL": stack.url("api"),
        "SLICE_SITE_URL": stack.url("site"),
        "SLICE_IDP_URL": stack.url("idp"),
    }
    output = run(
        [npx, "playwright", "test", "-c", "slice-e2e/playwright.config.ts"],
        cwd=stack.root / "web",
        env=env,
    )
    print(output.strip())


def export_release(stack: Stack, target: Path) -> tuple[Path, Path]:
    """Copy the release `public` points at, and the snapshot it was rendered from.

    Only this script's own gitignored work folder (local/.slice-check) is replaced.
    """
    link = run(stack.compose("exec", "-T", "api", "readlink", "/site/public"), env=stack.env())
    link = link.strip()
    version_id = Path(link).name
    if not link.startswith("releases/") or version_id == "empty":
        raise SliceCheckError(f"nothing is published: public -> {link!r}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    release = target / "release"
    run(stack.compose("cp", f"api:/site/{link}", str(release)), env=stack.env())
    query = (
        "print(EJSON.stringify(db.slice_published_versions"
        f".findOne({{_id: '{version_id}'}}).snapshot, {{relaxed: true}}))"
    )
    argv = ["exec", "-T", "mongo", "mongosh", "--quiet", "portfolio_slice", "--eval", query]
    snapshot = target / "snapshot.json"
    snapshot.write_text(run(stack.compose(*argv), env=stack.env()), encoding="utf-8", newline="\n")
    print(f"  exported release {version_id}")
    return release, snapshot


def scan_argv(stack: Stack, release: Path, snapshot: Path) -> list[str]:
    """The public-output scan command, with the authorized media digests (R3)."""
    root = stack.root
    return [
        sys.executable,
        str(root / "scripts" / "scan_output.py"),
        "--release",
        str(release),
        "--snapshot",
        str(snapshot),
        "--vocabulary",
        str(root / "web" / "slice-renderer" / "src" / "template-strings.json"),
        "--static-dir",
        str(root / "web" / "slice-renderer" / "assets"),
        "--media-digests",
        str(root / "local" / "fixtures" / "derivatives.sha256.json"),
    ]


def scan_public_output(stack: Stack) -> None:
    """AC0.9: only C2-derived values, the vocabulary, authorized images and static assets."""
    release, snapshot = export_release(stack, WORK_DIR / "scan")
    output = run(scan_argv(stack, release, snapshot))
    print(f"  {output.strip()}")


STEPS: tuple[tuple[str, Callable[[Stack], None]], ...] = (
    ("Compose publishes only on loopback", assert_loopback_only),
    ("Isolated stack running", start_stack),
    ("Database empty at start (tmpfs)", assert_empty_database),
    ("Playwright journey, headers and timings", run_playwright),
    ("Public-output allow-list scan", scan_public_output),
)


def stop_stack(stack: Stack, keep_running: bool) -> None:
    """Stop the stack this script started: containers and network only, never volumes."""
    if stack.managed:
        return
    if keep_running:
        print(f"\n  stack left running; stop it with: {' '.join(stack.compose('down'))}")
        return
    try:
        run(stack.compose("down"), env=stack.env())
    except SliceCheckError as error:
        print(f"warning: could not stop the stack: {error}", file=sys.stderr)


def run_steps(stack: Stack, keep_running: bool) -> list[tuple[str, str, float]]:
    """Run every step in order, stopping at the first failure; always stop the stack."""
    results: list[tuple[str, str, float]] = []
    try:
        for name, step in STEPS:
            print(f"\n== {name}", flush=True)
            started = time.monotonic()
            try:
                step(stack)
            except SliceCheckError as error:
                results.append((name, "FAILED", time.monotonic() - started))
                print(f"FAILED: {error}", file=sys.stderr)
                break
            results.append((name, "passed", time.monotonic() - started))
    finally:
        stop_stack(stack, keep_running)
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Walking slice end-to-end check (W6).")
    parser.add_argument("--keep-running", action="store_true", help="leave the stack up")
    args = parser.parse_args(argv)
    try:
        stack = Stack.from_env(os.environ)
    except (SliceCheckError, IsolationError) as error:
        print(f"slice-check: {error}", file=sys.stderr)
        return 2
    print(f"slice-check: Compose project {stack.project}; ports {dict(stack.ports)}")
    lock = None if stack.managed else CheckoutLock(stack.root, "verify")
    try:
        if lock is not None:
            lock.acquire()
        results = run_steps(stack, args.keep_running)
    except IsolationError as error:
        print(f"slice-check: {error}", file=sys.stderr)
        return 2
    finally:
        if lock is not None:
            lock.release()
    print("\n== slice-check summary")
    for name, outcome, seconds in results:
        print(f"  {outcome:7} {seconds:6.1f} s  {name}")
    failed = len(results) < len(STEPS) or any(outcome != "passed" for _, outcome, _ in results)
    print("slice-check: FAILED" if failed else "slice-check: OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
