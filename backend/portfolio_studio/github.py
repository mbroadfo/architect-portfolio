"""Repository visibility and licence, read from the public GitHub REST API (FR4.10).

The read uses no credentials. It fails closed: any error, a 404, a rate limit, a renamed
repository or an unexpected answer means "visibility not confirmed", which is treated as
private, so no name, link or licence is ever published for it (review-03 A1-P04).
"""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from portfolio_studio.model import Repository

API_ROOT = "https://api.github.com/repos"
TIMEOUT_SECONDS = 10
MAX_BODY_BYTES = 256 * 1024
CACHE_SECONDS = 600
FAILURE_CACHE_SECONDS = 60
# OSI-approved SPDX identifiers that earn "Open source · <id>" (FR4.10). Anything else, "other"
# and NOASSERTION earn "Source available".
OSI_SPDX: frozenset[str] = frozenset(
    {
        "0BSD",
        "AFL-3.0",
        "AGPL-3.0",
        "Apache-2.0",
        "Artistic-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "BSL-1.0",
        "CECILL-2.1",
        "ECL-2.0",
        "EPL-1.0",
        "EPL-2.0",
        "EUPL-1.1",
        "EUPL-1.2",
        "GPL-2.0",
        "GPL-3.0",
        "ISC",
        "LGPL-2.1",
        "LGPL-3.0",
        "LPPL-1.3c",
        "MIT",
        "MIT-0",
        "MPL-2.0",
        "MS-PL",
        "MS-RL",
        "MulanPSL-2.0",
        "NCSA",
        "OFL-1.1",
        "OSL-3.0",
        "PostgreSQL",
        "UPL-1.0",
        "Unlicense",
        "Zlib",
    }
)

logger = logging.getLogger("portfolio_studio.github")

# Fetch(url) -> (HTTP status, body bytes). Raises OSError on a transport failure.
Fetch = Callable[[str], tuple[int, bytes]]


@dataclass(frozen=True)
class RepositoryCheck:
    """What GitHub said about one owner-entered repository address."""

    url: str
    confirmed_public: bool
    name: str | None = None
    licence: str | None = None
    checked_at: float = 0.0
    note: str = ""

    def open_source_licence(self) -> str | None:
        """The SPDX id when it is OSI-approved, else None."""
        return self.licence if self.licence in OSI_SPDX else None


def urllib_fetch(url: str) -> tuple[int, bytes]:
    """GET ``url`` without credentials, reading at most MAX_BODY_BYTES."""
    request = urllib.request.Request(  # noqa: S310 - fixed https://api.github.com prefix
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "architect-portfolio-local-studio",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            return int(response.status), response.read(MAX_BODY_BYTES)
    except urllib.error.HTTPError as error:
        return int(error.code), b""


def _private(url: str, note: str) -> RepositoryCheck:
    return RepositoryCheck(url=url, confirmed_public=False, checked_at=time.time(), note=note)


def interpret(repository: Repository, status: int, body: bytes) -> RepositoryCheck:
    """Map a GitHub answer to a check; anything but a clear public answer is private."""
    owner, name = repository.owner_and_name()
    if status == 404:
        return _private(repository.url, "not found or private")
    if status in (403, 429):
        return _private(repository.url, "GitHub rate limit or refusal")
    if status != 200:
        return _private(repository.url, f"GitHub answered {status}")
    try:
        document = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _private(repository.url, "unreadable answer")
    if not isinstance(document, dict):
        return _private(repository.url, "unexpected answer")
    full_name = document.get("full_name")
    if document.get("private") is not False or document.get("visibility") != "public":
        return _private(repository.url, "not public")
    if not isinstance(full_name, str) or full_name.lower() != f"{owner}/{name}".lower():
        return _private(repository.url, "renamed or moved")
    licence = document.get("license")
    spdx = licence.get("spdx_id") if isinstance(licence, dict) else None
    return RepositoryCheck(
        url=f"https://github.com/{full_name}",
        confirmed_public=True,
        name=full_name.split("/", 1)[1],
        licence=spdx if isinstance(spdx, str) and spdx not in ("NOASSERTION", "") else None,
        checked_at=time.time(),
        note="public",
    )


class RepositoryChecker:
    """Checks repositories, with a short cache so previews do not exhaust the rate limit."""

    def __init__(
        self,
        fetch: Fetch = urllib_fetch,
        cache_seconds: float = CACHE_SECONDS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._fetch = fetch
        self._cache_seconds = cache_seconds
        self._clock = clock
        self._cache: dict[str, RepositoryCheck] = {}
        self._lock = threading.Lock()

    def check(self, repository: Repository, fresh: bool = False) -> RepositoryCheck:
        """Check one repository; ``fresh`` skips the cache (used for the Publish review)."""
        with self._lock:
            cached = None if fresh else self._cache.get(repository.url)
            if cached is not None:
                limit = self._cache_seconds if cached.confirmed_public else FAILURE_CACHE_SECONDS
                if self._clock() - cached.checked_at < min(limit, self._cache_seconds):
                    return cached
        owner, name = repository.owner_and_name()
        try:
            status, body = self._fetch(f"{API_ROOT}/{owner}/{name}")
            result = interpret(repository, status, body)
        except (OSError, ValueError) as error:
            logger.info(
                "repository check failed", extra={"fields": {"error": type(error).__name__}}
            )
            result = _private(repository.url, "GitHub could not be reached")
        result = RepositoryCheck(
            url=result.url,
            confirmed_public=result.confirmed_public,
            name=result.name,
            licence=result.licence,
            checked_at=self._clock(),
            note=result.note,
        )
        with self._lock:
            self._cache[repository.url] = result
        return result
