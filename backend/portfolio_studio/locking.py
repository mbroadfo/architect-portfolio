"""One writer per content repository: an OS-level lock on ``.studio.lock``.

The lock is held by an open file handle, so the operating system releases it when the
process exits, even after a crash. No process id is ever signalled.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import TracebackType
from typing import IO

from portfolio_studio.errors import LockedError

LOCK_NAME = ".studio.lock"


class ContentLock:
    """A non-blocking exclusive lock on ``<content>/.studio.lock``."""

    def __init__(self, content_dir: Path) -> None:
        self.path = content_dir / LOCK_NAME
        self._handle: IO[bytes] | None = None

    def acquire(self) -> None:
        handle = open(self.path, "a+b")  # noqa: SIM115 - held open for the lock's lifetime
        try:
            _lock(handle)
        except OSError as error:
            handle.close()
            raise LockedError(
                f"another Studio process is using {self.path.parent} (close it first)"
            ) from error
        self._handle = handle

    def release(self) -> None:
        if self._handle is not None:
            try:
                _unlock(self._handle)
            finally:
                self._handle.close()
                self._handle = None

    def __enter__(self) -> ContentLock:
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
