"""Content-bound security-review check (BR5.2; provisional).

For a pull request that touches a path listed in ``.github/security-sensitive-paths.txt``,
require a review record under ``docs/security-reviews/`` whose ``patch-id:`` equals the
pull request's current patch identity and whose ``verdict:`` is ``READY``. Any record for
that identity with another verdict (for example ``NOT-READY``) fails the check, even when
another record says ``READY``.

The path list is read from the base revision, not from the pull request, so a change cannot
narrow the list that judges it. CI also runs this script as it is on the base (see
``.github/workflows/ci.yml``, review-check). Only when the base has no list yet (the pull
request that introduces the check) is the head's list used, with a printed notice.

The patch identity is ``git patch-id --verbatim`` over the diff from
``merge-base(<base>, <head>)`` to ``<head>``, excluding ``docs/security-reviews/``.
``--verbatim`` (git 2.39 or later; it implies ``--stable``) hashes every whitespace byte, so
re-indenting Python or YAML, or changing a space inside a string, gives a new identity and
needs a new review (security re-review S0-1; ``--stable`` alone dropped whitespace).
Adding the review record does not change the identity it must match, and a rebase that keeps
the same content keeps the same identity (patch-id ignores line numbers).

Usage::

    python scripts/check_security_review.py --base origin/main --head HEAD

Exit codes: 0 pass (or no sensitive path touched), 1 review missing or not READY, 2 error.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

PATHS_FILE = ".github/security-sensitive-paths.txt"
REVIEWS_DIR = "docs/security-reviews"
PATCH_ID_LINE = re.compile(r"^patch-id:\s*([0-9a-f]{40,64})\s*$", re.MULTILINE)
VERDICT_LINE = re.compile(r"^verdict:\s*(\S+)\s*$", re.MULTILINE)
READY = "READY"


class GitError(RuntimeError):
    """A git command failed."""


@dataclass(frozen=True)
class ReviewRecord:
    """A parsed review record."""

    path: str
    patch_id: str | None
    verdict: str | None


@dataclass(frozen=True)
class CheckResult:
    """The outcome of the check."""

    ok: bool
    message: str
    sensitive_paths: tuple[str, ...] = ()
    patch_id: str | None = None
    notices: tuple[str, ...] = ()


def git_bytes(repo: Path, *args: str, stdin: bytes | None = None) -> bytes:
    """Run a git command in ``repo`` and return its exact standard output bytes.

    Bytes, not text: a text-mode pipe on Windows would rewrite line endings and so change
    what ``git patch-id`` hashes.
    """
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        input=stdin,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(f"git {' '.join(args)} failed: {stderr}")
    return completed.stdout


def git(repo: Path, *args: str) -> str:
    """Run a git command in ``repo`` and return its standard output as text."""
    return git_bytes(repo, *args).decode("utf-8", errors="surrogateescape")


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a path pattern (``**``, ``*``, ``?``) into an anchored regular expression."""
    parts: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    return re.compile("^" + "".join(parts) + "$")


def parse_patterns(text: str) -> list[str]:
    """Return the non-comment, non-blank patterns of the security-sensitive paths list."""
    patterns = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def path_matches(path: str, pattern: str) -> bool:
    """Return True when ``path`` is covered by ``pattern``.

    A pattern ending in ``/`` covers everything below that directory. Any other pattern
    covers a path when it matches the path itself or one of its parent directories.
    """
    if pattern.endswith("/"):
        prefix = pattern
        if not any(char in prefix for char in "*?"):
            return path.startswith(prefix)
        regex = glob_to_regex(prefix.rstrip("/"))
    else:
        regex = glob_to_regex(pattern)
    segments = path.split("/")
    candidates = ["/".join(segments[: count + 1]) for count in range(len(segments))]
    return any(regex.match(candidate) for candidate in candidates)


def sensitive_paths(changed: Sequence[str], patterns: Sequence[str]) -> list[str]:
    """Return the changed paths that a pattern covers."""
    return [path for path in changed if any(path_matches(path, p) for p in patterns)]


def compute_patch_id(repo: Path, merge_base: str, head: str) -> str | None:
    """Return the verbatim patch identity of ``merge_base..head`` without the review records.

    Whitespace is part of the identity: an indentation-only change is a new identity.
    """
    diff = git_bytes(
        repo,
        "diff",
        "--no-color",
        "--no-ext-diff",
        "--no-renames",
        "--full-index",
        "--binary",
        merge_base,
        head,
        "--",
        ".",
        f":(exclude){REVIEWS_DIR}/",
    )
    if not diff.strip():
        return None
    output = git_bytes(repo, "patch-id", "--verbatim", stdin=diff).decode("ascii").strip()
    if not output:
        return None
    return output.split()[0]


def load_records(repo: Path, head: str) -> list[ReviewRecord]:
    """Read every review record under ``docs/security-reviews/`` at ``head``."""
    listing = git(repo, "ls-tree", "-r", "--name-only", head, "--", f"{REVIEWS_DIR}/")
    records = []
    for path in listing.splitlines():
        if not path.endswith(".md") or path.endswith("/README.md"):
            continue
        text = git(repo, "show", f"{head}:{path}")
        patch_match = PATCH_ID_LINE.search(text)
        verdict_match = VERDICT_LINE.search(text)
        records.append(
            ReviewRecord(
                path=path,
                patch_id=patch_match.group(1) if patch_match else None,
                verdict=verdict_match.group(1) if verdict_match else None,
            )
        )
    return records


def read_patterns(repo: Path, revision: str) -> list[str]:
    """Read the security-sensitive paths list at ``revision``."""
    try:
        return parse_patterns(git(repo, "show", f"{revision}:{PATHS_FILE}"))
    except GitError as error:
        raise GitError(f"cannot read {PATHS_FILE} at {revision}: {error}") from error


def trusted_patterns(repo: Path, base: str, head: str) -> tuple[list[str], str | None]:
    """Read the list from the base, never from the change under review.

    Only when the base has no list yet (the pull request that introduces it) is the head's
    list used, and a notice says so. Returns (patterns, notice).
    """
    try:
        return read_patterns(repo, base), None
    except GitError:
        notice = (
            f"bootstrap: {base} has no {PATHS_FILE}; using the pull request's own list. "
            "This pull request introduces the check, so its review rests on Michael's review."
        )
        return read_patterns(repo, head), notice


def run_check(repo: Path, base: str, head: str) -> CheckResult:
    """Run the check for the pull request ``base...head``."""
    merge_base = git(repo, "merge-base", base, head).strip()
    changed = git(repo, "diff", "--name-only", "--no-renames", merge_base, head).splitlines()
    patterns, notice = trusted_patterns(repo, base, head)
    notices = (notice,) if notice else ()
    touched = sensitive_paths(changed, patterns)
    if not touched:
        return CheckResult(
            ok=True, message="no security-sensitive path touched; no review needed", notices=notices
        )
    patch_id = compute_patch_id(repo, merge_base, head)
    if patch_id is None:
        return CheckResult(
            ok=True, message="no content change outside the review records", notices=notices
        )
    matching = [r for r in load_records(repo, head) if r.patch_id == patch_id]
    not_ready = [r for r in matching if r.verdict != READY]
    if matching and not not_ready:
        message = f"review {matching[0].path} is READY for patch-id {patch_id}"
    elif not_ready:
        verdicts = ", ".join(f"{r.path}: verdict {r.verdict or '(none)'}" for r in not_ready)
        message = f"a review for patch-id {patch_id} is not READY ({verdicts})"
    else:
        message = f"no review record in {REVIEWS_DIR}/ has patch-id {patch_id}"
    return CheckResult(
        ok=bool(matching) and not not_ready,
        message=message,
        sensitive_paths=tuple(touched),
        patch_id=patch_id,
        notices=notices,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Content-bound security-review check (BR5.2).")
    parser.add_argument("--repo", default=".", help="repository path (default: .)")
    parser.add_argument(
        "--base", default="origin/main", help="base revision (default: origin/main)"
    )
    parser.add_argument("--head", default="HEAD", help="head revision (default: HEAD)")
    args = parser.parse_args(argv)
    try:
        result = run_check(Path(args.repo), args.base, args.head)
    except GitError as error:
        print(f"check_security_review: ERROR - {error}", file=sys.stderr)
        return 2
    for notice in result.notices:
        print(f"check_security_review: NOTICE - {notice}")
    if result.ok:
        print(f"check_security_review: OK - {result.message}")
        return 0
    print(f"check_security_review: FAIL - {result.message}", file=sys.stderr)
    print("  Security-sensitive paths that need a review:", file=sys.stderr)
    for path in result.sensitive_paths:
        print(f"    {path}", file=sys.stderr)
    print(
        f"  Record a review in {REVIEWS_DIR}/ with 'patch-id: {result.patch_id}' "
        f"and 'verdict: READY' (see {REVIEWS_DIR}/README.md).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
