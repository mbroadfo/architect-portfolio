"""Cloudflare Pages packaging (Direct Upload artifacts) and the package register.

``package_pages`` turns the last successful, scanned build into a Pages artifact::

    <content>/build/pages-<UTC timestamp>/
        site/          the folder Pages uploads: the build's files plus ``_headers``
        scan-inputs/   a copy of the build's scan inputs (snapshot, media digests,
                       vocabulary, static sources), so a deploy can re-run the same scan
        manifest.json  every file with its SHA-256 and size, the source build id and its scan
                       result, the published exhibits and revisions, the mode

Only ``site/`` is ever uploaded. Packaging:

- refuses a missing build, a build without a passed scan, a build whose files no longer
  match the digests recorded when it passed, a file over 25 MiB and more than 20,000 files;
- re-verifies every copied file and re-runs ``scripts/scan_output.py`` on the packaged pages
  with the build's saved scan inputs, before ``_headers`` is added;
- adds ``_headers`` and nothing else (no ``_redirects``, ``_routes.json``, ``_worker.js`` or
  ``functions/``);
- **registers** the artifact in ``<content>/deployments/packages.json`` and commits it in the
  private content repository: the SHA-256 of ``manifest.json``, the build id, the mode, the
  exhibits and revisions, the public media and downloads, the digests of the scan inputs.

The deploy (``pages_deploy``) trusts nothing inside the artifact on its own: it requires the
artifact's manifest to be registered and re-validates everything against the register
(security re-review NP-1).

Staging packages (the default) send ``X-Robots-Tag: noindex`` on every path. A production
package omits it. It can be packaged for inspection, but this tool never deploys it
(re-review NP-2: production needs a separate, owner-approved mechanism).
"""

from __future__ import annotations

import json
import re
import shutil
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from portfolio_studio.build import manifest_path, rename_with_retry, scan_inputs_dir
from portfolio_studio.errors import StudioError
from portfolio_studio.gitrepo import ContentRepo
from portfolio_studio.location import check_outside_code
from portfolio_studio.scan import ScanInputs, run_scan, sha256_file, tree_digests

Mode = Literal["staging", "production"]

MAX_FILE_BYTES = 25 * 1024 * 1024  # Pages: 25 MiB per file
MAX_FILES = 20_000  # Pages Free plan
MAX_HEADER_RULES = 100
MAX_HEADER_LINE = 2_000
ARTIFACT_SCHEMA = "portfolio-pages-artifact/1"
BUILD_MANIFEST_SCHEMA = "portfolio-site-build/1"
REGISTER_SCHEMA = "portfolio-pages-register/1"
REGISTER = "deployments/packages.json"
UPLOAD_DIR = "site"
SCAN_INPUTS = "scan-inputs"
MANIFEST = "manifest.json"
HEADERS = "_headers"
ARTIFACT_NAME = re.compile(r"^pages-\d{8}T\d{6}Z(-\d{1,4})?$")

# NFR15 / C9: the same headers the U0 public server sends, plus HSTS (Pages is HTTPS only).
SITE_HEADERS: tuple[tuple[str, str], ...] = (
    ("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'"),
    ("Strict-Transport-Security", "max-age=31536000"),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ("Cache-Control", "no-cache"),
)
IMMUTABLE = "public, max-age=31536000, immutable"
# FR4.4: every download is an attachment of a fixed, safe type, never rendered or run.
DOWNLOAD_HEADERS: tuple[str, ...] = (
    "! Cache-Control",
    f"Cache-Control: {IMMUTABLE}",
    "! Content-Type",
    "Content-Type: application/octet-stream",
    "Content-Disposition: attachment",
    "! X-Content-Type-Options",
    "X-Content-Type-Options: nosniff",
    "! Content-Security-Policy",
    "Content-Security-Policy: sandbox; default-src 'none'",
)


class PagesError(StudioError):
    """Packaging or deployment was refused; nothing was uploaded."""

    status_code = 422
    code = "PAGES_REFUSED"


def served_file(site: Path, path: str) -> tuple[str, int]:
    """How Pages serves a C9 address from the packaged files: (file, status).

    The build already writes Pages-servable files: ``/`` is ``index.html``, ``/work/`` is
    ``work/index.html`` and ``/work/<slug>`` is ``work/<slug>/index.html``. Pages answers
    ``/work/<slug>`` by redirecting to ``/work/<slug>/`` and serving that folder's
    ``index.html``; the renderer's links and the scan accept both forms. An address with no
    file gets the nearest ``404.html`` with status 404. Only the root one exists, so it
    serves both "not on display" cases (an exhibit and a category). ``category-404.html``
    stays in the package because the scan expects it, but Pages never uses it as an error page.
    """
    clean = path.split("?", 1)[0].split("#", 1)[0].strip("/")
    parts = clean.split("/") if clean else []
    if any(part in ("", ".", "..") for part in parts):
        return "404.html", 404
    if not parts:
        candidate = "index.html"
    elif "." in parts[-1]:
        candidate = clean
    else:
        candidate = f"{clean}/index.html"
    if (site / candidate).is_file() and candidate != "404.html":
        return candidate, 200
    return "404.html", 404


@dataclass(frozen=True)
class PackageResult:
    artifact: Path
    upload_dir: Path
    mode: Mode
    file_count: int
    total_bytes: int
    exhibits: list[dict[str, Any]]
    build_id: str
    scan: str
    manifest_sha256: str


def load_json(path: Path, what: str) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PagesError(f"{what} is missing or unreadable ({path})") from error
    if not isinstance(document, dict):
        raise PagesError(f"{what} is not a JSON object ({path})")
    return document


def load_build(build_output: Path) -> dict[str, Any]:
    """The manifest of the build in place, checked: it passed its scan and is unchanged."""
    if not (build_output / "index.html").is_file():
        raise PagesError(f"there is no built site in {build_output}; run 'build' first")
    manifest = load_json(manifest_path(build_output), "the build manifest")
    if manifest.get("schema") != BUILD_MANIFEST_SCHEMA:
        raise PagesError("the build has no scan record; run 'build' again")
    scan = manifest.get("scan")
    if not isinstance(scan, dict) or scan.get("passed") is not True:
        raise PagesError("the build's public-output scan did not pass; nothing was packaged")
    check_digests(build_output, manifest.get("files"), "the built site")
    check_digests(scan_inputs_dir(build_output), manifest.get("scanInputs"), "the scan inputs")
    return manifest


def check_digests(root: Path, expected: object, what: str) -> None:
    if not isinstance(expected, dict) or not expected:
        raise PagesError(f"{what} has no recorded digests; run 'build' again")
    actual = tree_digests(root) if root.is_dir() else {}
    if actual != expected:
        changed = sorted(set(actual) ^ set(expected)) or sorted(
            key for key in actual if actual[key] != expected.get(key)
        )
        raise PagesError(
            f"{what} changed after it was built and scanned ({', '.join(changed[:5])}); "
            "run 'build' again"
        )


def check_limits(root: Path, extra_files: int = 1) -> tuple[int, int]:
    """Pages limits: no file over 25 MiB, at most 20,000 files. Returns (files, bytes)."""
    files = [p for p in root.rglob("*") if p.is_file()]
    if len(files) + extra_files > MAX_FILES:
        raise PagesError(f"{len(files) + extra_files} files is over the Pages limit of {MAX_FILES}")
    total = 0
    for path in files:
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            name = path.relative_to(root).as_posix()
            raise PagesError(f"{name} is {size} bytes, over the Pages limit of 25 MiB per file")
        total += size
    return len(files), total


def headers_file(mode: Mode, downloads: Sequence[str]) -> str:
    """The ``_headers`` rules for every path; staging adds ``X-Robots-Tag: noindex``."""
    site = list(SITE_HEADERS)
    if mode == "staging":
        site.append(("X-Robots-Tag", "noindex"))
    rules: list[tuple[str, list[str]]] = [
        ("/*", [f"{name}: {value}" for name, value in site]),
        ("/assets/*", ["! Cache-Control", f"Cache-Control: {IMMUTABLE}"]),
        ("/media/*", ["! Cache-Control", f"Cache-Control: {IMMUTABLE}"]),
    ]
    rules.extend((f"/{key}", list(DOWNLOAD_HEADERS)) for key in sorted(downloads))
    if len(rules) > MAX_HEADER_RULES:
        raise PagesError(f"{len(rules)} header rules is over the Pages limit of {MAX_HEADER_RULES}")
    lines = [f"# Generated by portfolio_studio package-pages ({mode}). Do not edit."]
    for path, values in rules:
        lines.append(path)
        lines.extend(f"  {value}" for value in values)
    if any(len(line) > MAX_HEADER_LINE for line in lines):
        raise PagesError("a header rule is longer than the Pages limit of 2,000 characters")
    return "\n".join(lines) + "\n"


def downloads_of(keys: Sequence[str]) -> list[str]:
    return sorted(key for key in keys if key.startswith("files/"))


def _artifact_dir(root: Path) -> Path:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    candidate, number = root / f"pages-{stamp}", 2
    while candidate.exists() or candidate.with_name(candidate.name + ".tmp").exists():
        candidate, number = root / f"pages-{stamp}-{number}", number + 1
    return candidate


# --- the register ------------------------------------------------------------------------------


def empty_register() -> dict[str, Any]:
    return {"schema": REGISTER_SCHEMA, "packages": [], "deployments": []}


def load_register(content: Path) -> dict[str, Any]:
    """``<content>/deployments/packages.json`` (empty when nothing was ever packaged)."""
    path = content / REGISTER
    if not path.exists():
        return empty_register()
    register = load_json(path, "the package register")
    if register.get("schema") != REGISTER_SCHEMA or not isinstance(register.get("packages"), list):
        raise PagesError("the package register is not a portfolio-pages-register/1 document")
    register.setdefault("deployments", [])
    return register


def save_register(content: Path, register: dict[str, Any], message: str) -> None:
    """Write and commit the register; only that file is committed."""
    path = content / REGISTER
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(register, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    ContentRepo(content).commit([REGISTER], message)


def find_package(register: dict[str, Any], manifest_sha256: str) -> dict[str, Any] | None:
    for entry in register["packages"]:
        if isinstance(entry, dict) and entry.get("manifestSha256") == manifest_sha256:
            return entry
    return None


# --- packaging -----------------------------------------------------------------------------------


def package_pages(
    content: Path,
    build_output: Path,
    scanner: Path,
    mode: Mode = "staging",
) -> PackageResult:
    """Package the last successful, scanned build for Pages and register it."""
    artifacts_root = check_outside_code(content / "build", "Pages artifact folder")
    build = load_build(build_output)
    check_limits(build_output)
    target = _artifact_dir(artifacts_root)
    temporary = target.with_name(target.name + ".tmp")
    try:
        site = temporary / UPLOAD_DIR
        shutil.copytree(build_output, site)
        shutil.copytree(scan_inputs_dir(build_output), temporary / SCAN_INPUTS)
        check_digests(site, build["files"], "the copied site")
        check_digests(temporary / SCAN_INPUTS, build["scanInputs"], "the copied scan inputs")
        scan = run_scan(scanner, site, ScanInputs(temporary / SCAN_INPUTS), "nothing packaged")
        downloads = downloads_of(list(build["files"]))
        (site / HEADERS).write_text(headers_file(mode, downloads), encoding="utf-8", newline="\n")
        if set(tree_digests(site)) != set(build["files"]) | {HEADERS}:
            raise PagesError("the package contains files other than the build and _headers")
        file_count, total = check_limits(site, extra_files=0)
        manifest = _artifact_manifest(site, build, mode, scan, total)
        manifest["artifact"] = target.name  # each package's manifest digest is unique
        (temporary / MANIFEST).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        rename_with_retry(temporary, target)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    digest = sha256_file(target / MANIFEST)
    try:
        _register(content, target, manifest, digest)
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)  # an unregistered artifact can never deploy
        raise
    return PackageResult(
        artifact=target,
        upload_dir=target / UPLOAD_DIR,
        mode=mode,
        file_count=file_count,
        total_bytes=total,
        exhibits=list(build["exhibits"]),
        build_id=str(build["buildId"]),
        scan=scan,
        manifest_sha256=digest,
    )


def _register(content: Path, target: Path, manifest: dict[str, Any], digest: str) -> None:
    register = load_register(content)
    keys = list(manifest["files"])
    register["packages"].append(
        {
            "artifact": target.name,
            "manifestSha256": digest,
            "buildId": manifest["sourceBuild"]["buildId"],
            "mode": manifest["mode"],
            "registeredAt": manifest["createdAt"],
            "exhibits": manifest["exhibits"],
            "publicFiles": sorted(k for k in keys if k.startswith(("media/", "files/"))),
            "scanInputs": tree_digests(target / SCAN_INPUTS),
        }
    )
    save_register(
        content,
        register,
        f"Register Pages package {target.name} ({manifest['mode']}, manifest {digest[:12]})",
    )


def _artifact_manifest(
    site: Path, build: dict[str, Any], mode: Mode, scan: str, total: int
) -> dict[str, Any]:
    files = {
        key: {"sha256": digest, "bytes": (site / key).stat().st_size}
        for key, digest in tree_digests(site).items()
    }
    return {
        "schema": ARTIFACT_SCHEMA,
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": mode,
        "noindex": mode == "staging",
        "uploadDir": UPLOAD_DIR,
        "sourceBuild": {
            "buildId": build["buildId"],
            "builtAt": build["builtAt"],
            "generation": build["generation"],
            "scan": build["scan"],
        },
        "packageScan": {"passed": True, "summary": scan},
        "exhibits": build["exhibits"],
        "fileCount": len(files),
        "totalBytes": total,
        "files": files,
    }
