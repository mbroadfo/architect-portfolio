"""Guarded Cloudflare Pages Direct Upload, staging only, and pruning of old deployments.

Production cannot be deployed from here at all. Team practice puts every production deploy
in a run of the GitHub ``production`` environment that Michael approves, and Michael approved
Pages for staging only (security re-review NP-2). The branch is always ``staging``.

Before anything is uploaded, ``validate_artifact`` re-checks the artifact against the
**register** in the private content repository, not against the artifact's own claims (NP-1):

1. the artifact folder is ``<content>/build/pages-<timestamp>``, an absolute path without
   shell metacharacters (NP-4);
2. the SHA-256 of its ``manifest.json`` is registered, the register entry and the manifest
   agree (build id, exhibits, mode), and the mode is ``staging``;
3. ``site/`` holds exactly the manifest's files with their digests, and no Pages special file
   (``_worker.js``, ``functions/``, ``_routes.json``, ``_redirects``) and no dotfile;
4. ``_headers`` is byte-identical to the one this code generates for the mode;
5. the copied scan inputs match the digests in the register, and ``scripts/scan_output.py``
   passes again on ``site/`` without ``_headers``.

Executing also needs ``--project`` and both credentials in the environment. Before the
upload, the project's production branch is read from the Cloudflare API: it must be set and
must not be ``staging``, so a staging deploy can never become a production deploy (NP-6).
Wrangler is the pinned copy in ``tools/pages-deploy`` (``npm ci``), run as
``node .../wrangler.js`` with an argument list and no shell (NP-4), from an empty temporary
folder with Git disabled, after checking that no Wrangler configuration file exists there or
in any parent folder. The credentials go only through the environment and are never printed.

After a deploy that drops any exhibit or public file the previously deployed package had,
``prune`` deletes every older staging deployment, because each Pages deployment keeps a
permanent address of its own (NP-3, FR8). Rollback means redeploying an earlier registered
artifact, never keeping old deployments.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from portfolio_studio.location import code_root
from portfolio_studio.pages import (
    ARTIFACT_NAME,
    ARTIFACT_SCHEMA,
    HEADERS,
    MANIFEST,
    REGISTER,
    SCAN_INPUTS,
    UPLOAD_DIR,
    PagesError,
    downloads_of,
    find_package,
    headers_file,
    load_json,
    load_register,
    save_register,
)
from portfolio_studio.scan import ScanInputs, run_scan, sha256_file, tree_digests

BRANCH = "staging"
WRANGLER_VERSION = "4.149.0"
TOKEN = "CLOUDFLARE_API_TOKEN"  # noqa: S105 - the variable name, not a value
ACCOUNT = "CLOUDFLARE_ACCOUNT_ID"
API_ROOT = "https://api.cloudflare.com/client/v4"
PROJECT_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,56}[a-z0-9])?$")
ACCOUNT_ID = re.compile(r"^[0-9a-f]{32}$")
DEPLOYMENT_ID = re.compile(r"^[0-9a-f-]{8,64}$")
UNSAFE_PATH = re.compile(r"[&%^|<>\"'\r\n`!]")
SPECIAL_FILES = frozenset({"_worker.js", "_routes.json", "_redirects", "functions"})
WRANGLER_CONFIGS = ("wrangler.toml", "wrangler.json", "wrangler.jsonc")
CACHE_WARNING = (
    "Note: copies already cached by browsers or by Cloudflare may persist briefly after a "
    "take-down; media is cached as immutable. Purge the cache as part of a production "
    "take-down."
)


# --- process and HTTP boundaries (injected in tests) -------------------------------------------


@dataclass(frozen=True)
class Completed:
    code: int
    stdout: str = ""


Runner = Callable[[list[str], Path, dict[str, str], bool], Completed]
# Fetch(method, url, headers) -> (status, body). Raises OSError on a transport failure.
Fetch = Callable[[str, str, Mapping[str, str]], tuple[int, bytes]]


def subprocess_runner(
    argv: list[str], cwd: Path, environment: dict[str, str], capture: bool
) -> Completed:
    """Run without a shell; output is shown unless captured. The environment is never printed."""
    completed = subprocess.run(  # noqa: S603 - node and wrangler.js by absolute path, no shell
        argv,
        cwd=cwd,
        env=environment,
        check=False,
        capture_output=capture,
        text=True,
        encoding="utf-8",
    )
    return Completed(completed.returncode, completed.stdout if capture else "")


def urllib_fetch(method: str, url: str, headers: Mapping[str, str]) -> tuple[int, bytes]:
    request = urllib.request.Request(url, method=method, headers=dict(headers))  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - fixed https
            return int(response.status), response.read(1024 * 1024)
    except urllib.error.HTTPError as error:
        return int(error.code), b""


# --- the artifact against the register ----------------------------------------------------


@dataclass
class Validated:
    artifact: Path
    manifest: dict[str, Any]
    entry: dict[str, Any]
    manifest_sha256: str
    scan: str
    problems: list[str] = field(default_factory=list)


def check_artifact_path(content: Path, artifact: Path) -> Path:
    """Absolute, no shell metacharacters, and ``<content>/build/pages-<timestamp>`` (NP-4)."""
    raw = str(artifact)
    if not artifact.is_absolute():
        raise PagesError("give the artifact as an absolute path")
    if UNSAFE_PATH.search(raw):
        raise PagesError("the artifact path contains characters that are not allowed")
    resolved = artifact.resolve()
    if resolved.parent != (content / "build").resolve() or not ARTIFACT_NAME.match(resolved.name):
        raise PagesError(f"the artifact must be a pages-<timestamp> folder in {content / 'build'}")
    return resolved


def _special(key: str) -> bool:
    parts = key.split("/")
    if any(part.startswith(".") for part in parts):
        return True
    return parts[0] in SPECIAL_FILES or (parts[0].startswith("_") and key != HEADERS)


def validate_artifact(content: Path, artifact: Path, scanner: Path | None = None) -> Validated:
    """Re-check an artifact against the register and re-run the scan (NP-1)."""
    artifact = check_artifact_path(content, artifact)
    manifest_file = artifact / MANIFEST
    digest = sha256_file(manifest_file) if manifest_file.is_file() else ""
    entry = find_package(load_register(content), digest) if digest else None
    if entry is None:
        raise PagesError(
            f"this artifact is not in the package register ({REGISTER}); only artifacts made "
            "by package-pages can be deployed"
        )
    manifest = load_json(manifest_file, "the artifact manifest")
    if manifest.get("schema") != ARTIFACT_SCHEMA or manifest.get("uploadDir") != UPLOAD_DIR:
        raise PagesError("this is not a Pages artifact made by package-pages")
    if entry.get("artifact") != artifact.name or manifest.get("artifact") != artifact.name:
        raise PagesError("the register names another folder for this manifest")
    if entry.get("mode") != manifest.get("mode"):
        raise PagesError("the artifact's mode differs from the register")
    if entry.get("mode") != "staging":
        raise PagesError(
            "only staging artifacts can be deployed; production needs a separate, "
            "owner-approved mechanism"
        )
    if entry.get("buildId") != manifest.get("sourceBuild", {}).get("buildId") or entry.get(
        "exhibits"
    ) != manifest.get("exhibits"):
        raise PagesError("the artifact's build or exhibits differ from the register")
    _check_site(artifact / UPLOAD_DIR, manifest)
    _check_headers(artifact / UPLOAD_DIR, manifest)
    scan = _rescan(artifact, entry, scanner or code_root() / "scripts" / "scan_output.py")
    return Validated(artifact, manifest, entry, digest, scan)


def _check_site(site: Path, manifest: dict[str, Any]) -> None:
    files = manifest.get("files")
    if not isinstance(files, dict) or not site.is_dir():
        raise PagesError("the artifact has no upload folder or file list")
    present = {p.relative_to(site).as_posix() for p in site.rglob("*")}
    special = sorted(key for key in present if _special(key))
    if special:
        raise PagesError(f"Pages special files or dotfiles are not allowed: {', '.join(special)}")
    regular = {key for key in present if (site / key).is_file()}
    if regular != set(files):
        extra = sorted(regular ^ set(files))
        raise PagesError(f"the artifact's files differ from its manifest: {', '.join(extra[:5])}")
    for key in regular:
        entry = files[key]
        path = site / key
        if sha256_file(path) != entry.get("sha256") or path.stat().st_size != entry.get("bytes"):
            raise PagesError(f"{key} was changed after packaging; package again")


def _check_headers(site: Path, manifest: dict[str, Any]) -> None:
    expected = headers_file("staging", downloads_of(list(manifest["files"])))
    if (site / HEADERS).read_text(encoding="utf-8") != expected:
        raise PagesError("_headers differs from the headers this code generates; package again")


def _rescan(artifact: Path, entry: dict[str, Any], scanner: Path) -> str:
    inputs = artifact / SCAN_INPUTS
    if not inputs.is_dir() or tree_digests(inputs) != entry.get("scanInputs"):
        raise PagesError("the artifact's scan inputs differ from the register; package again")
    with tempfile.TemporaryDirectory(prefix="pages-rescan-") as folder:
        copy = Path(folder) / "site"
        shutil.copytree(artifact / UPLOAD_DIR, copy)
        (copy / HEADERS).unlink()
        return run_scan(scanner, copy, ScanInputs(inputs), "nothing was uploaded")


# --- the deploy -------------------------------------------------------------------------------


def wrangler_js(root: Path | None = None) -> Path:
    return (
        (root or code_root())
        / "tools"
        / "pages-deploy"
        / "node_modules"
        / "wrangler"
        / ("bin/wrangler.js")
    )


def check_wrangler(path: Path) -> None:
    package = path.parent.parent / "package.json"
    if not path.is_file() or not package.is_file():
        raise PagesError("wrangler is not installed; run 'npm --prefix tools/pages-deploy ci'")
    version = load_json(package, "wrangler's package.json").get("version")
    if version != WRANGLER_VERSION:
        raise PagesError(f"wrangler {version} is installed; {WRANGLER_VERSION} is required")


def node_executable() -> str:
    node = shutil.which("node")
    if node is None or Path(node).suffix.lower() in (".cmd", ".bat"):
        raise PagesError("node is not installed as an executable on PATH")
    return node


def deploy_command(node: str, wrangler: Path, validated: Validated, project: str) -> list[str]:
    return [
        node,
        str(wrangler),
        "pages",
        "deploy",
        str(validated.artifact / UPLOAD_DIR),
        "--project-name",
        project,
        "--branch",
        BRANCH,
        "--commit-message",
        f"{validated.entry['buildId']} (staging)",
        "--commit-dirty=true",
    ]


def describe(
    validated: Validated,
    command: list[str],
    environment: Mapping[str, str],
    refusals: list[str],
    executing: bool,
) -> str:
    """The deploy report. Credentials are reported as set or not set, never shown."""
    manifest = validated.manifest
    exhibits = ", ".join(
        f"{e['projectId']} (revision {e['sourceRevision']})" for e in manifest["exhibits"]
    )
    lines = [
        "EXECUTING the staging deploy below." if executing else "DRY RUN: nothing was uploaded.",
        f"Artifact:   {validated.artifact}",
        f"Registered: manifest sha256 {validated.manifest_sha256}",
        f"Built from: {validated.entry['buildId']}; mode staging (noindex), branch {BRANCH}",
        f"Re-scan:    {validated.scan}",
        f"Exhibits:   {exhibits or 'none'}",
        f"Files:      {manifest['fileCount']} ({manifest['totalBytes']} bytes); match the "
        "manifest and the register; _headers regenerated and identical",
        "Credentials: "
        + ", ".join(f"{n} {'set' if environment.get(n) else 'NOT set'}" for n in (TOKEN, ACCOUNT)),
        "Command:    " + " ".join(command),
    ]
    if refusals:
        lines.append("It would not execute until:")
        lines.extend(f"  - {reason}" for reason in refusals)
    elif not executing:
        lines.append("Add --execute to run it.")
    return "\n".join(lines)


def refusals_for(project: str | None, environment: Mapping[str, str]) -> list[str]:
    found = []
    if project is None:
        found.append("name the Pages project with --project")
    elif not PROJECT_NAME.match(project):
        found.append("the project name must be lowercase letters, digits and hyphens")
    if not environment.get(TOKEN):
        found.append(f"set {TOKEN} in the environment (it is never printed)")
    account = environment.get(ACCOUNT, "")
    if not ACCOUNT_ID.match(account):
        found.append(f"set {ACCOUNT} (32 hexadecimal characters) in the environment")
    return found


def production_branch(project: str, environment: Mapping[str, str], fetch: Fetch) -> str | None:
    """The project's production branch, read from the Cloudflare API (NP-6)."""
    url = f"{API_ROOT}/accounts/{environment[ACCOUNT]}/pages/projects/{project}"
    try:
        status, body = fetch("GET", url, _auth(environment))
    except OSError as error:
        raise PagesError(f"Cloudflare could not be reached: {type(error).__name__}") from error
    if status != 200:
        raise PagesError(f"Cloudflare answered {status} for project {project}; nothing uploaded")
    try:
        result = json.loads(body).get("result") or {}
    except (json.JSONDecodeError, AttributeError) as error:
        raise PagesError("Cloudflare's answer about the project was unreadable") from error
    branch = result.get("production_branch") if isinstance(result, dict) else None
    return branch if isinstance(branch, str) and branch else None


def _auth(environment: Mapping[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {environment[TOKEN]}", "Accept": "application/json"}


def _child_environment(environment: Mapping[str, str], folder: Path) -> dict[str, str]:
    return {
        **environment,
        "WRANGLER_SEND_METRICS": "false",
        "GIT_DIR": str(folder / "no-git"),
        "GIT_CEILING_DIRECTORIES": str(folder),
    }


def check_no_wrangler_config(folder: Path) -> None:
    """Pages commands read a Wrangler configuration from the working folder or its parents;
    none may exist on that path (wrangler 4.149 ``pages deploy`` has no ``--config``)."""
    for directory in [folder, *folder.parents]:
        for name in WRANGLER_CONFIGS:
            if (directory / name).exists():
                raise PagesError(f"a Wrangler configuration exists at {directory / name}")


@dataclass(frozen=True)
class Deployer:
    content: Path
    environment: Mapping[str, str]
    runner: Runner = subprocess_runner
    fetch: Fetch = urllib_fetch
    wrangler: Path | None = None
    scanner: Path | None = None
    out: Callable[[str], None] = print

    def plan(self, artifact: Path, project: str | None) -> tuple[Validated, list[str], list[str]]:
        validated = validate_artifact(self.content, artifact, self.scanner)
        wrangler = self.wrangler or wrangler_js()
        command = deploy_command(
            _node_or_placeholder(), wrangler, validated, project or "<project>"
        )
        return validated, command, refusals_for(project, self.environment)

    def deploy(self, artifact: Path, project: str | None, execute: bool) -> int:
        """Dry run unless ``execute``; executing needs every guard (see the module docs)."""
        validated, command, refusals = self.plan(artifact, project)
        if not execute or refusals:
            self.out(describe(validated, command, self.environment, refusals, executing=False))
            return 1 if execute else 0
        assert project is not None  # noqa: S101 - refusals_for requires it
        wrangler = self.wrangler or wrangler_js()
        check_wrangler(wrangler)
        command = deploy_command(node_executable(), wrangler, validated, project)
        branch = production_branch(project, self.environment, self.fetch)
        if branch is None or branch == BRANCH:
            raise PagesError(
                f"the project's production branch is {branch or 'not set'}; it must be set and "
                f"must not be '{BRANCH}' (create the project with production branch 'production')"
            )
        validate_artifact(self.content, validated.artifact, self.scanner)  # right before upload
        self.out(describe(validated, command, self.environment, [], executing=True))
        code = self._run(command, capture=False).code
        if code != 0:
            raise PagesError(f"wrangler failed (exit {code}); the previous deployment stands")
        removed = self._record(validated, project)
        if removed:
            self.out(
                f"This deploy removes {len(removed)} public item(s); pruning older deployments."
            )
            self.prune(project, execute=True)
            self.out(CACHE_WARNING)
        return 0

    def _run(self, argv: list[str], capture: bool) -> Completed:
        with tempfile.TemporaryDirectory(prefix="pages-wrangler-") as folder:
            path = Path(folder)
            check_no_wrangler_config(path)
            return self.runner(argv, path, _child_environment(self.environment, path), capture)

    def _record(self, validated: Validated, project: str) -> list[str]:
        """Record the deployment in the register; return what it removed since the last one."""
        register = load_register(self.content)
        previous = next(
            (
                find_package(register, d["manifestSha256"])
                for d in reversed(register["deployments"])
                if d.get("project") == project and d.get("branch") == BRANCH
            ),
            None,
        )
        removed: list[str] = []
        if previous is not None:
            now_files = set(validated.entry.get("publicFiles", []))
            now_ids = {e["projectId"] for e in validated.entry.get("exhibits", [])}
            removed = sorted(set(previous.get("publicFiles", [])) - now_files)
            removed += sorted(
                f"exhibit {e['projectId']}"
                for e in previous.get("exhibits", [])
                if e["projectId"] not in now_ids
            )
        register["deployments"].append(
            {
                "artifact": validated.artifact.name,
                "manifestSha256": validated.manifest_sha256,
                "project": project,
                "branch": BRANCH,
                "deployedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        save_register(
            self.content,
            register,
            f"Record staging deploy of {validated.artifact.name} to {project}",
        )
        return removed

    # --- prune ----------------------------------------------------------------------------------

    def prune(self, project: str | None, execute: bool) -> int:
        """Delete every staging deployment except the newest (FR8 on Pages, NP-3)."""
        wrangler = self.wrangler or wrangler_js()
        listing = [
            _node_or_placeholder(),
            str(wrangler),
            "pages",
            "deployment",
            "list",
            "--project-name",
            project or "<project>",
            "--environment",
            "preview",
            "--json",
        ]
        refusals = refusals_for(project, self.environment)
        if not execute or refusals:
            self.out("DRY RUN: no deployment was listed or deleted.")
            self.out("Would list:   " + " ".join(listing))
            self.out(
                "Would delete: every 'staging' preview deployment except the newest, with "
                "'pages deployment delete <id> --project-name <project> --force'. Production "
                "deployments are never touched."
            )
            for reason in refusals:
                self.out(f"  - {reason}")
            return 1 if execute else 0
        assert project is not None  # noqa: S101 - refusals_for requires it
        check_wrangler(wrangler)
        listing[0] = node_executable()
        listed = self._run(listing, capture=True)
        if listed.code != 0:
            raise PagesError(f"wrangler could not list deployments (exit {listed.code})")
        stale, skipped = stale_deployments(listed.stdout)
        for deployment_id in stale:
            delete = [
                listing[0],
                str(wrangler),
                "pages",
                "deployment",
                "delete",
                deployment_id,
                "--project-name",
                project,
                "--force",
            ]
            if self._run(delete, capture=False).code != 0:
                raise PagesError(f"wrangler could not delete deployment {deployment_id}")
        self.out(f"Pruned {len(stale)} older staging deployment(s); kept the newest.")
        if skipped:
            self.out(f"Left {skipped} deployment(s) on other branches untouched.")
        return 0


def _node_or_placeholder() -> str:
    found = shutil.which("node")
    return found if found and Path(found).suffix.lower() not in (".cmd", ".bat") else "node"


def stale_deployments(listing: str) -> tuple[list[str], int]:
    """From ``pages deployment list --json`` (newest first): the staging deployments to delete
    (all but the newest) and how many deployments on other branches were left alone."""
    try:
        rows = json.loads(listing)
    except json.JSONDecodeError as error:
        raise PagesError("wrangler's deployment list was not JSON") from error
    if not isinstance(rows, list):
        raise PagesError("wrangler's deployment list was not a list")
    staging = [
        str(row.get("Id"))
        for row in rows
        if isinstance(row, dict)
        and row.get("Branch") == BRANCH
        and str(row.get("Environment", "")).lower() == "preview"
    ]
    if any(not DEPLOYMENT_ID.match(deployment_id) for deployment_id in staging):
        raise PagesError("wrangler listed a deployment id in an unexpected form")
    return staging[1:], len(rows) - len(staging)
