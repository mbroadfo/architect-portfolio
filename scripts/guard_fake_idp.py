"""Fake identity provider guard (BR1.2, NFR1.3).

Scans every non-local build output for traces of the local-only fake identity provider:

- the marker ``AIDLC_LOCAL_ONLY_FAKE_IDP``;
- the fake provider's package name ``fake_idp``;
- the fake issuer URL, read at scan time from ``local/compose.env`` (skipped when absent);
- PEM or JWK private-key material.

Default targets are the deployable build outputs ``backend/dist/*`` and ``web/*/dist/**``.
Archives (wheels, zips and tarballs) are opened and every member is scanned.
The guard never scans ``scripts/`` or ``local/``, so it cannot match itself or the fake
provider's own source. It fails when it scanned zero files, so a broken build cannot pass.

Exit codes: 0 clean, 1 contamination found or nothing scanned, 2 usage error.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import tarfile
import zipfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

MARKER = b"AIDLC_LOCAL_ONLY_FAKE_IDP"
PACKAGE_NAME = re.compile(rb"(?<![A-Za-z0-9_])fake_idp(?![A-Za-z0-9_])")
PEM_PRIVATE_KEY = re.compile(rb"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")
JWK_KTY = re.compile(rb'"kty"\s*:\s*"(?:EC|RSA|OKP)"')
JWK_PRIVATE_D = re.compile(rb'"d"\s*:\s*"[A-Za-z0-9_-]{16,}"')

ISSUER_ENV_KEY = "AUTH_ISSUER"
COMPOSE_ENV = Path("local") / "compose.env"
DEFAULT_TARGET_GLOBS: tuple[str, ...] = ("backend/dist/*", "web/*/dist/**/*")
EXCLUDED_TOP_LEVEL: frozenset[str] = frozenset({"scripts", "local"})
ZIP_SUFFIXES: tuple[str, ...] = (".whl", ".zip", ".jar")
TAR_SUFFIXES: tuple[str, ...] = (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")


@dataclass(frozen=True)
class Finding:
    """One contamination finding: where it is and what was matched."""

    location: str
    reason: str


@dataclass
class ScanResult:
    """The outcome of a scan: how many files were read and what was found."""

    files_scanned: int
    findings: list[Finding]


def read_fake_issuer(root: Path) -> str | None:
    """Return the fake issuer URL from ``local/compose.env``, or None when it is absent."""
    env_file = root / COMPOSE_ENV
    if not env_file.is_file():
        return None
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == ISSUER_ENV_KEY:
            issuer = value.strip().strip('"').strip("'")
            return issuer or None
    return None


def build_patterns(fake_issuer: str | None) -> list[tuple[str, re.Pattern[bytes]]]:
    """Return the (reason, pattern) pairs every scanned file is checked against."""
    patterns: list[tuple[str, re.Pattern[bytes]]] = [
        ("fake identity provider marker", re.compile(re.escape(MARKER))),
        ("fake identity provider package name", PACKAGE_NAME),
        ("PEM private key", PEM_PRIVATE_KEY),
    ]
    if fake_issuer:
        issuer = fake_issuer.rstrip("/").encode("utf-8")
        patterns.append(("fake issuer URL", re.compile(re.escape(issuer))))
    return patterns


def scan_bytes(
    location: str, data: bytes, patterns: Sequence[tuple[str, re.Pattern[bytes]]]
) -> list[Finding]:
    """Return every finding in one blob of bytes."""
    findings = [Finding(location, reason) for reason, pattern in patterns if pattern.search(data)]
    if JWK_KTY.search(data) and JWK_PRIVATE_D.search(data):
        findings.append(Finding(location, "JWK private key"))
    return findings


def _is_excluded(path: Path, root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return bool(relative.parts) and relative.parts[0] in EXCLUDED_TOP_LEVEL


def _iter_archive_members(path: Path) -> Iterator[tuple[str, bytes]]:
    name = path.name.lower()
    if name.endswith(ZIP_SUFFIXES):
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if not info.is_dir():
                    yield info.filename, archive.read(info)
        return
    with tarfile.open(path) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            extracted = archive.extractfile(member)
            if extracted is not None:
                yield member.name, extracted.read()


def _is_archive(path: Path) -> bool:
    return path.name.lower().endswith(ZIP_SUFFIXES + TAR_SUFFIXES)


def scan_file(
    path: Path, patterns: Sequence[tuple[str, re.Pattern[bytes]]]
) -> tuple[int, list[Finding]]:
    """Scan one file, opening archives; return (files scanned, findings)."""
    if not _is_archive(path):
        return 1, scan_bytes(str(path), path.read_bytes(), patterns)
    scanned = 1
    findings: list[Finding] = []
    for member_name, member_data in _iter_archive_members(path):
        scanned += 1
        location = f"{path}!{member_name}"
        member_name_bytes = member_name.encode("utf-8")
        findings.extend(scan_bytes(location, member_name_bytes + b"\n" + member_data, patterns))
        if _is_archive(Path(member_name)):
            nested = io.BytesIO(member_data)
            findings.extend(_scan_nested_archive(location, member_name, nested, patterns))
    return scanned, findings


def _scan_nested_archive(
    location: str,
    member_name: str,
    data: io.BytesIO,
    patterns: Sequence[tuple[str, re.Pattern[bytes]]],
) -> list[Finding]:
    findings: list[Finding] = []
    if member_name.lower().endswith(ZIP_SUFFIXES):
        with zipfile.ZipFile(data) as archive:
            for info in archive.infolist():
                if not info.is_dir():
                    findings.extend(
                        scan_bytes(f"{location}!{info.filename}", archive.read(info), patterns)
                    )
    return findings


def collect_targets(root: Path, explicit: Sequence[str]) -> list[Path]:
    """Return the files to scan: the explicit targets, or the default build-output globs."""
    candidates: list[Path] = []
    if explicit:
        for target in explicit:
            path = (root / target) if not Path(target).is_absolute() else Path(target)
            if path.is_dir():
                candidates.extend(p for p in sorted(path.rglob("*")) if p.is_file())
            elif path.is_file():
                candidates.append(path)
    else:
        for pattern in DEFAULT_TARGET_GLOBS:
            candidates.extend(p for p in sorted(root.glob(pattern)) if p.is_file())
    unique: dict[Path, None] = {}
    for candidate in candidates:
        if not _is_excluded(candidate, root):
            unique[candidate] = None
    return list(unique)


def run_scan(root: Path, explicit_targets: Sequence[str] = ()) -> ScanResult:
    """Scan the targets under ``root`` and return the result."""
    patterns = build_patterns(read_fake_issuer(root))
    files_scanned = 0
    findings: list[Finding] = []
    for target in collect_targets(root, explicit_targets):
        try:
            scanned, file_findings = scan_file(target, patterns)
        except (OSError, zipfile.BadZipFile, tarfile.TarError) as error:
            findings.append(Finding(str(target), f"unreadable build output ({error})"))
            continue
        files_scanned += scanned
        findings.extend(file_findings)
    return ScanResult(files_scanned=files_scanned, findings=findings)


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    parser.add_argument(
        "targets",
        nargs="*",
        help="files or directories to scan instead of the default build outputs",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        print(f"guard: root {root} is not a directory", file=sys.stderr)
        return 2

    result = run_scan(root, args.targets)
    if result.files_scanned == 0:
        print(
            "guard: FAIL - zero files scanned. Build the deployable outputs first "
            "(backend/dist, web/*/dist); scripts/ and local/ are never scanned.",
            file=sys.stderr,
        )
        return 1
    if result.findings:
        print(f"guard: FAIL - {len(result.findings)} finding(s):", file=sys.stderr)
        for finding in result.findings:
            print(f"  {finding.location}: {finding.reason}", file=sys.stderr)
        return 1
    print(f"guard: OK - {result.files_scanned} file(s) scanned, no fake identity provider traces.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
