"""Isolation rules for the Docker Compose verification stack (Codex review R1).

``scripts/verify.py`` and ``local/slice_check.py`` both start the walking slice stack. They
share these rules so that a verification run never touches anything it did not create:

- **One Compose project per checkout.** The name is ``portfolio-verify-<10 hex>``, where the
  hex is the start of the SHA-256 of the resolved checkout path. Two worktrees therefore never
  share containers, networks or volumes. ``portfolio-slice`` (the developer's own demo stack)
  and any name that does not start with ``portfolio-verify-`` are refused.
- **Free loopback ports per run.** Each run binds ``127.0.0.1:0`` to find free ports, so two
  checkouts never collide on a host port.
- **One run per checkout.** An exclusive lock file in the gitignored work directory
  (``.verify-work/``) stops two runs in the same checkout from overlapping; a second run fails
  at once with a clear message. The operating system releases the lock when the process ends,
  so a crashed run never leaves a stale lock behind.
- **Nothing is deleted.** Compose arguments that remove data or other projects' resources
  are refused, whatever the caller asks for and however they are spelled (security re-review
  S0-4): ``--volumes``, ``--rmi`` and ``--remove-orphans`` also as ``--flag=value``; ``-v``
  also inside combined short flags (``-tv``, ``-fsv``); and the words ``rm``, ``prune``,
  ``volume``, ``volumes`` and ``system`` wherever they appear (after global options such as
  ``--profile x`` too). Teardown is a plain ``down``: containers and the network of this
  project only. The project's ``site`` volume is kept and reused.

Standard library only.
"""

from __future__ import annotations

import errno
import hashlib
import os
import re
import socket
import sys
from collections.abc import Sequence
from pathlib import Path
from types import TracebackType
from typing import IO

PROJECT_PREFIX = "portfolio-verify-"
# The developer's own stack (local/compose.yaml), which verification must never touch.
PROTECTED_PROJECTS: frozenset[str] = frozenset({"portfolio-slice"})
# Long options that remove volumes, images or other projects' containers (also `--x=value`).
FORBIDDEN_LONG: frozenset[str] = frozenset({"--volumes", "--rmi", "--remove-orphans"})
# Short option letters that remove volumes (also inside combined flags such as `-tv`).
FORBIDDEN_SHORT: frozenset[str] = frozenset({"v"})
# Subcommands that remove resources other than through a plain `down`, refused wherever they
# appear in the argument list.
FORBIDDEN_WORDS: frozenset[str] = frozenset({"rm", "prune", "volume", "volumes", "system"})
WORK_DIR_NAME = ".verify-work"
PROJECT_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
NAMESPACE = re.compile(r"^[a-z0-9]{1,16}$")
PORT_ATTEMPTS = 20


class IsolationError(Exception):
    """A Compose project name or argument list would break the isolation rules."""


class LockBusyError(IsolationError):
    """Another verification run in this checkout holds the lock."""


def checkout_id(root: Path) -> str:
    """The first 10 hex digits of the SHA-256 of the resolved checkout path."""
    resolved = os.path.normcase(str(Path(root).resolve()))
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:10]


def validate_project(name: str) -> str:
    """Return ``name`` when it is a verification project; raise IsolationError otherwise."""
    if name in PROTECTED_PROJECTS:
        raise IsolationError(f"refusing Compose project '{name}': it is the developer's own stack")
    if (
        not name.startswith(PROJECT_PREFIX)
        or len(name) == len(PROJECT_PREFIX)
        or not PROJECT_NAME.match(name)
    ):
        raise IsolationError(
            f"refusing Compose project '{name}': verification projects are named "
            f"'{PROJECT_PREFIX}<checkout id>'"
        )
    return name


def checkout_project(root: Path, namespace: str = "") -> str:
    """The Compose project for this checkout, optionally with a test namespace suffix."""
    if namespace and not NAMESPACE.match(namespace):
        raise IsolationError(f"invalid project namespace {namespace!r}")
    name = f"{PROJECT_PREFIX}{checkout_id(root)}"
    return validate_project(f"{name}-{namespace}" if namespace else name)


def _is_forbidden(arg: str) -> bool:
    """Whether one argument, normalised, removes data: `--x=value` is `--x`, `-tv` is -t -v."""
    if arg in FORBIDDEN_WORDS:
        return True
    if arg.startswith("--"):
        return arg.split("=", 1)[0] in FORBIDDEN_LONG
    if arg.startswith("-") and len(arg) > 1:
        letters = arg[1:].split("=", 1)[0]
        return any(letter in FORBIDDEN_SHORT for letter in letters)
    return False


def check_compose_args(args: Sequence[str]) -> None:
    """Raise IsolationError when the arguments would remove data or foreign resources."""
    bad = [arg for arg in args if _is_forbidden(arg)]
    if bad:
        raise IsolationError(f"refusing data-removing compose argument(s): {', '.join(bad)}")


def compose_argv(project: str, root: Path, compose_files: Sequence[str], *args: str) -> list[str]:
    """``docker compose -p <project> -f <file>... <args>``, after checking both."""
    validate_project(project)
    check_compose_args(args)
    argv = ["docker", "compose", "-p", project]
    for compose_file in compose_files:
        argv += ["-f", str(Path(root) / compose_file)]
    return [*argv, *args]


def _ipv6_port_taken(port: int) -> bool:
    """True when ``[::1]:port`` is already bound (a dev server may listen there only)."""
    try:
        probe = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    except OSError:
        return False
    with probe:
        try:
            probe.bind(("::1", port))
        except OSError as error:
            return error.errno in (errno.EADDRINUSE, getattr(errno, "WSAEADDRINUSE", -1))
    return False


def free_loopback_ports(count: int) -> list[int]:
    """Return ``count`` distinct ports that are free on 127.0.0.1 (and on ::1) right now."""
    if count <= 0:
        return []
    for _ in range(PORT_ATTEMPTS):
        sockets: list[socket.socket] = []
        try:
            for _index in range(count):
                holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sockets.append(holder)
                holder.bind(("127.0.0.1", 0))
            ports = [int(holder.getsockname()[1]) for holder in sockets]
        finally:
            for holder in sockets:
                holder.close()
        if len(set(ports)) == count and not any(_ipv6_port_taken(p) for p in ports):
            return ports
    raise IsolationError(f"could not find {count} free loopback ports")


def work_dir(root: Path) -> Path:
    """The gitignored per-checkout work directory (lock files, test reports)."""
    return Path(root) / WORK_DIR_NAME


class CheckoutLock:
    """An exclusive, non-blocking lock file per checkout (``.verify-work/<name>.lock``).

    The lock is an operating-system file lock, so it is released when the process ends.
    """

    def __init__(self, root: Path, name: str = "verify") -> None:
        if not NAMESPACE.match(name.replace("-", "")):
            raise IsolationError(f"invalid lock name {name!r}")
        self.path = work_dir(root) / f"{name}.lock"
        self._handle: IO[bytes] | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self.path, "a+b")  # noqa: SIM115 - held until release()
        try:
            _lock(handle)
        except OSError as error:
            handle.close()
            raise LockBusyError(
                f"another verification run is using this checkout (lock {self.path} is held); "
                "wait for it to finish. Worktrees each have their own lock and stack"
            ) from error
        self._handle = handle

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            _unlock(self._handle)
        finally:
            self._handle.close()
            self._handle = None

    def __enter__(self) -> CheckoutLock:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()


if sys.platform == "win32":
    import msvcrt

    def _lock(handle: IO[bytes]) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock(handle: IO[bytes]) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _lock(handle: IO[bytes]) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(handle: IO[bytes]) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
