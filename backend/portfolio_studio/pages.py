"""Cloudflare Pages packaging and a guarded Direct Upload deploy (staging first).

``package_pages`` turns the last successful, scanned build into a Pages artifact::

    <artifacts>/pages-<UTC timestamp>/
        site/          the folder Pages uploads: the build's files plus ``_headers``
        manifest.json  every file with its SHA-256 and size, the source build id and its scan
                       result, the published exhibits and revisions, the mode (never uploaded)

It refuses a missing build, a build without a passed scan, a build whose files no longer
match the digests recorded when it passed, a file over 25 MiB and more than 20,000 files.
It re-verifies every copied file and re-runs ``scripts/scan_output.py`` on the packaged
pages with the build's saved scan inputs, before ``_headers`` is added. ``_headers`` is the
only file a package adds. No ``_redirects`` file is needed.

Staging packages (the default) send ``X-Robots-Tag: noindex`` on every path. A production
package omits it and needs ``owner_authorized`` (``--i-have-owner-authorization``).

``plan_deploy`` and ``execute_deploy`` build the ``wrangler pages deploy`` command for an
artifact. The default is a dry run that changes nothing. Executing needs the project, branch
``staging`` (or ``--production`` with the owner-authorization flag and a production
artifact) and the Cloudflare credentials in the environment, which are never printed,
stored or passed on the command line. Wrangler runs from an empty temporary folder with Git
disabled, so it can never read or send the private content repository's commit messages.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from portfolio_studio.build import manifest_path, scan_inputs_dir
from portfolio_studio.errors import StudioError
from portfolio_studio.location import check_outside_code
from portfolio_studio.scan import ScanInputs, run_scan, sha256_file, tree_digests

Mode = Literal["staging", "production"]

MAX_FILE_BYTES = 25 * 1024 * 1024  # Pages: 25 MiB per file
MAX_FILES = 20_000  # Pages Free plan
MAX_HEADER_RULES = 100
MAX_HEADER_LINE = 2_000
ARTIFACT_SCHEMA = "portfolio-pages-artifact/1"
BUILD_MANIFEST_SCHEMA = "portfolio-site-build/1"
UPLOAD_DIR = "site"
MANIFEST = "manifest.json"
HEADERS = "_headers"
STAGING_BRANCH = "staging"
WRANGLER_VERSION = "4.146.0"
TOKEN_VARIABLES = ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")
PROJECT_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,56}[a-z0-9])?$")
BRANCH_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,62}$")

# NFR15 / C9: the same headers the U0 public server sends, plus HSTS (Pages is HTTPS only).
SITE_HEADERS: tuple[tuple[str, str], ...] = (
    ("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'"),
    ("Strict-Transport-Security", "max-age=31536000"),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ("Cache-Control", "no-cache"),
)
IMMUTABLE = "public, max-age=31536000, immutable"
# FR4.4: downloads are always attachments with a fixed safe type for their file type.
DOWNLOAD_TYPES: Mapping[str, str] = {
    "pdf": "application/pdf",
    "skp": "application/octet-stream",
    "fcstd": "application/octet-stream",
    "dxf": "application/octet-stream",
    "stl": "application/octet-stream",
    "zip": "application/zip",
    "vsdx": "application/octet-stream",
}


class PagesError(StudioError):
    """Packaging or deployment was refused; nothing was uploaded."""

    status_code = 422
    code = "PAGES_REFUSED"


# --- packaging -------------------------------------------------------------------------------


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


def _load_json(path: Path, what: str) -> dict[str, Any]:
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
    manifest = _load_json(manifest_path(build_output), "the build manifest")
    if manifest.get("schema") != BUILD_MANIFEST_SCHEMA:
        raise PagesError("the build has no scan record; run 'build' again")
    scan = manifest.get("scan")
    if not isinstance(scan, dict) or scan.get("passed") is not True:
        raise PagesError("the build's public-output scan did not pass; nothing was packaged")
    _check_digests(build_output, manifest.get("files"), "the built site")
    _check_digests(scan_inputs_dir(build_output), manifest.get("scanInputs"), "the scan inputs")
    return manifest


def _check_digests(root: Path, expected: object, what: str) -> None:
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
    for key in downloads:
        extension = key.rsplit(".", 1)[-1].lower()
        rules.append(
            (
                f"/{key}",
                [
                    "! Cache-Control",
                    f"Cache-Control: {IMMUTABLE}",
                    "! Content-Type",
                    f"Content-Type: {DOWNLOAD_TYPES.get(extension, 'application/octet-stream')}",
                    "Content-Disposition: attachment",
                ],
            )
        )
    if len(rules) > MAX_HEADER_RULES:
        raise PagesError(f"{len(rules)} header rules is over the Pages limit of {MAX_HEADER_RULES}")
    lines = [f"# Generated by portfolio_studio package-pages ({mode}). Do not edit."]
    for path, values in rules:
        lines.append(path)
        lines.extend(f"  {value}" for value in values)
    if any(len(line) > MAX_HEADER_LINE for line in lines):
        raise PagesError("a header rule is longer than the Pages limit of 2,000 characters")
    return "\n".join(lines) + "\n"


def _artifact_dir(root: Path) -> Path:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    candidate, number = root / f"pages-{stamp}", 2
    while candidate.exists() or candidate.with_name(candidate.name + ".tmp").exists():
        candidate, number = root / f"pages-{stamp}-{number}", number + 1
    return candidate


def package_pages(
    build_output: Path,
    artifacts_root: Path,
    scanner: Path,
    mode: Mode = "staging",
    owner_authorized: bool = False,
) -> PackageResult:
    """Package the last successful, scanned build for Cloudflare Pages Direct Upload."""
    if mode == "production" and not owner_authorized:
        raise PagesError(
            "a production package needs --i-have-owner-authorization (Michael's explicit "
            "authorization); staging is the default"
        )
    artifacts_root = check_outside_code(artifacts_root, "Pages artifact folder")
    build = load_build(build_output)
    check_limits(build_output)
    target = _artifact_dir(artifacts_root)
    temporary = target.with_name(target.name + ".tmp")
    try:
        site = temporary / UPLOAD_DIR
        shutil.copytree(build_output, site)
        _check_digests(site, build["files"], "the copied site")
        scan = run_scan(
            scanner,
            site,
            ScanInputs(scan_inputs_dir(build_output)),
            "nothing was packaged",
        )
        downloads = sorted(key for key in build["files"] if key.startswith("files/"))
        (site / HEADERS).write_text(headers_file(mode, downloads), encoding="utf-8", newline="\n")
        if set(tree_digests(site)) != set(build["files"]) | {HEADERS}:
            raise PagesError("the package contains files other than the build and _headers")
        file_count, total = check_limits(site, extra_files=0)
        manifest = _artifact_manifest(site, build, mode, scan, total)
        (temporary / MANIFEST).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        temporary.rename(target)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
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


# --- deployment ------------------------------------------------------------------------------


@dataclass(frozen=True)
class DeployPlan:
    artifact: Path
    manifest: dict[str, Any]
    command: list[str]
    refusals: list[str]

    @property
    def executable(self) -> bool:
        return not self.refusals


def verify_artifact(artifact: Path) -> dict[str, Any]:
    """Check the upload folder against the artifact manifest, file by file."""
    manifest = _load_json(artifact / MANIFEST, "the artifact manifest")
    if manifest.get("schema") != ARTIFACT_SCHEMA or manifest.get("uploadDir") != UPLOAD_DIR:
        raise PagesError("this is not a Pages artifact made by package-pages")
    site = artifact / UPLOAD_DIR
    files = manifest.get("files")
    if not isinstance(files, dict) or not site.is_dir():
        raise PagesError("the artifact has no upload folder or file list")
    present = {p.relative_to(site).as_posix(): p for p in site.rglob("*") if p.is_file()}
    if set(present) != set(files):
        extra = sorted(set(present) ^ set(files))
        raise PagesError(f"the artifact's files differ from its manifest: {', '.join(extra[:5])}")
    for key, path in present.items():
        entry = files[key]
        if sha256_file(path) != entry.get("sha256") or path.stat().st_size != entry.get("bytes"):
            raise PagesError(f"{key} was changed after packaging; package again")
    return manifest


def plan_deploy(
    artifact: Path,
    project: str | None,
    branch: str | None,
    production: bool,
    owner_authorized: bool,
    environment: Mapping[str, str],
    npx: str = "npx",
) -> DeployPlan:
    """Verify the artifact and describe the deploy; ``refusals`` lists why it cannot execute."""
    artifact = artifact.resolve()
    manifest = verify_artifact(artifact)
    refusals: list[str] = []
    if project is None:
        refusals.append("name the Pages project with --project")
    elif not PROJECT_NAME.match(project):
        refusals.append("the project name must be lowercase letters, digits and hyphens")
    branch = branch or (None if production else STAGING_BRANCH)
    if production:
        if not owner_authorized:
            refusals.append("a production deploy needs --i-have-owner-authorization")
        if manifest.get("mode") != "production":
            refusals.append("this artifact was packaged for staging; package with --production")
        if branch is None or not BRANCH_NAME.match(branch) or branch == STAGING_BRANCH:
            refusals.append("a production deploy needs --branch <the project's production branch>")
    else:
        if branch != STAGING_BRANCH:
            refusals.append("staging deploys use --branch staging only")
        if manifest.get("mode") != "staging":
            refusals.append("this artifact was packaged for production; use --production")
    for variable in TOKEN_VARIABLES:
        if not environment.get(variable):
            refusals.append(f"set {variable} in the environment (it is never printed)")
    command = [
        npx,
        "--yes",
        f"wrangler@{WRANGLER_VERSION}",
        "pages",
        "deploy",
        str(artifact / UPLOAD_DIR),
        "--project-name",
        project or "<project>",
        "--branch",
        branch or "<production branch>",
        "--commit-message",
        f"{manifest['sourceBuild']['buildId']} ({manifest['mode']})",
        "--commit-dirty=true",
    ]
    return DeployPlan(artifact=artifact, manifest=manifest, command=command, refusals=refusals)


def describe_plan(plan: DeployPlan, environment: Mapping[str, str], execute: bool) -> str:
    """The dry-run report. Credentials are reported as set or not set, never shown."""
    manifest = plan.manifest
    exhibits = ", ".join(
        f"{e['projectId']} (revision {e['sourceRevision']})" for e in manifest["exhibits"]
    )
    lines = [
        "DRY RUN: nothing was uploaded." if not execute else "EXECUTING the deploy below.",
        f"Artifact:   {plan.artifact}",
        f"Mode:       {manifest['mode']} (noindex: {'yes' if manifest['noindex'] else 'no'})",
        f"Built from: {manifest['sourceBuild']['buildId']} at {manifest['sourceBuild']['builtAt']}",
        f"Scan:       {manifest['packageScan']['summary']}",
        f"Exhibits:   {exhibits or 'none'}",
        f"Files:      {manifest['fileCount']} ({manifest['totalBytes']} bytes); all match the "
        "manifest",
        "Credentials: "
        + ", ".join(
            f"{name} {'set' if environment.get(name) else 'NOT set'}" for name in TOKEN_VARIABLES
        ),
        "Command:    " + " ".join(_quote(part) for part in plan.command),
    ]
    if plan.refusals:
        lines.append("It would not execute until:")
        lines.extend(f"  - {reason}" for reason in plan.refusals)
    elif not execute:
        lines.append("Add --execute to run it.")
    return "\n".join(lines)


def _quote(part: str) -> str:
    return f'"{part}"' if any(c in part for c in " ()<>") else part


Runner = Callable[[list[str], Path, dict[str, str]], int]


def subprocess_runner(argv: list[str], cwd: Path, environment: dict[str, str]) -> int:
    """Run wrangler with its output shown; the environment is passed, never printed."""
    completed = subprocess.run(argv, cwd=cwd, env=environment, check=False)  # noqa: S603
    return completed.returncode


def execute_deploy(plan: DeployPlan, environment: Mapping[str, str], runner: Runner) -> int:
    """Run the planned upload; refuse unless every guard passed."""
    if plan.refusals:
        raise PagesError("the deploy is refused: " + "; ".join(plan.refusals))
    verify_artifact(plan.artifact)  # once more, right before upload
    child = {**environment, "WRANGLER_SEND_METRICS": "false"}
    with tempfile.TemporaryDirectory(prefix="pages-deploy-") as folder:
        # No Git: wrangler must not read the private content repository's history.
        child["GIT_DIR"] = str(Path(folder) / "no-git")
        child["GIT_CEILING_DIRECTORIES"] = folder
        return runner(plan.command, Path(folder), child)
