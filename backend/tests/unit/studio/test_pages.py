"""Cloudflare Pages packaging, the package register and the guarded staging deploy.

No Cloudflare call is ever made: wrangler and the Cloudflare API are injected fakes, and the
real runner and HTTP client are never used here. Each reviewer bypass from the security
re-review (NP-1) is reproduced and shown refused."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pytest
from portfolio_studio import pages, pages_deploy
from portfolio_studio.build import SiteBuilder, default_output, manifest_path
from portfolio_studio.cli import cmd_deploy_pages, cmd_prune_deployments, main
from portfolio_studio.errors import ContentLocationError, StudioError
from portfolio_studio.gitrepo import ContentRepo
from portfolio_studio.location import code_root
from portfolio_studio.pages import (
    REGISTER,
    PagesError,
    headers_file,
    load_register,
    package_pages,
    served_file,
)
from portfolio_studio.pages_deploy import Completed, Deployer, stale_deployments
from portfolio_studio.scan import sha256_file, tree_digests
from portfolio_studio.service import StudioService

from .conftest import publish, ready_project

SCANNER = code_root() / "scripts" / "scan_output.py"
TOKEN = "cf-secret-token-value-1234567890"
ACCOUNT = "0123456789abcdef0123456789abcdef"
CREDENTIALS = {"CLOUDFLARE_API_TOKEN": TOKEN, "CLOUDFLARE_ACCOUNT_ID": ACCOUNT}
LISTING = [
    {"Id": "aaaa1111-0000-4000-8000-000000000003", "Environment": "Preview", "Branch": "staging"},
    {"Id": "aaaa1111-0000-4000-8000-000000000002", "Environment": "Preview", "Branch": "staging"},
    {"Id": "aaaa1111-0000-4000-8000-000000000001", "Environment": "Preview", "Branch": "staging"},
    {"Id": "bbbb2222-0000-4000-8000-000000000001", "Environment": "Production", "Branch": "main"},
]


@pytest.fixture
def built(service: StudioService, builder: SiteBuilder) -> Path:
    """A throwaway content repository with STARS published and the site built."""
    ready_project(service, "STARS")
    publish(service, "stars")
    output = default_output(service.store.root)
    builder.build(output)
    return output


def content_of(built: Path) -> Path:
    return built.parent.parent


def package(built: Path, mode: pages.Mode = "staging") -> pages.PackageResult:
    return package_pages(content_of(built), built, SCANNER, mode=mode)


class FakeWrangler:
    """Records every wrangler call; answers ``deployment list --json`` with LISTING."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], Path, dict[str, str], bool]] = []

    def __call__(
        self, argv: list[str], cwd: Path, environment: dict[str, str], capture: bool
    ) -> Completed:
        self.calls.append((argv, cwd, environment, capture))
        return Completed(0, json.dumps(LISTING) if "list" in argv else "")


class FakeApi:
    def __init__(self, status: int = 200, branch: str | None = "production") -> None:
        self.status, self.branch = status, branch
        self.requests: list[tuple[str, str, dict[str, str]]] = []

    def __call__(self, method: str, url: str, headers: Any) -> tuple[int, bytes]:
        self.requests.append((method, url, dict(headers)))
        result: dict[str, str] = {"name": "portfolio"}
        if self.branch is not None:
            result["production_branch"] = self.branch
        return self.status, json.dumps({"success": True, "result": result}).encode()


@pytest.fixture
def wrangler(tmp_path: Path) -> Path:
    """A stand-in for tools/pages-deploy/node_modules/wrangler at the pinned version."""
    root = tmp_path / "tools" / "node_modules" / "wrangler"
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "wrangler.js").write_text("// fake", encoding="utf-8")
    (root / "package.json").write_text(json.dumps({"version": "4.149.0"}), encoding="utf-8")
    return root / "bin" / "wrangler.js"


@pytest.fixture(autouse=True)
def plain_node(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pages_deploy, "node_executable", lambda: "node")


def deployer(
    built: Path,
    wrangler: Path,
    runner: FakeWrangler | None = None,
    api: FakeApi | None = None,
    environment: dict[str, str] | None = None,
    lines: list[str] | None = None,
) -> Deployer:
    sink = lines if lines is not None else []
    return Deployer(
        content=content_of(built),
        environment=CREDENTIALS if environment is None else environment,
        runner=runner or FakeWrangler(),
        fetch=api or FakeApi(),
        wrangler=wrangler,
        out=sink.append,
    )


def forge_registration(content: Path, artifact: Path, **changes: Any) -> None:
    """What a determined editor would also do: rewrite the manifest AND re-register it."""
    manifest_file = artifact / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    site = artifact / "site"
    manifest["files"] = {
        key: {"sha256": digest, "bytes": (site / key).stat().st_size}
        for key, digest in tree_digests(site).items()
    }
    manifest.update(changes)
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    register = load_register(content)
    for entry in register["packages"]:
        if entry["artifact"] == artifact.name:
            entry["manifestSha256"] = sha256_file(manifest_file)
            entry["mode"] = manifest["mode"]
    (content / REGISTER).write_text(json.dumps(register), encoding="utf-8")


# --- packaging and the register --------------------------------------------------------------


def test_package_adds_only_headers_and_is_registered_in_the_content_repo(built: Path) -> None:
    result = package(built)
    site = result.upload_dir
    build = json.loads(manifest_path(built).read_text(encoding="utf-8"))
    present = {p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file()}
    assert present == set(build["files"]) | {"_headers"}
    assert not (site / "manifest.json").exists() and not (site / "scan-inputs").exists()
    assert (result.artifact / "scan-inputs" / "snapshot.json").is_file()
    [entry] = load_register(content_of(built))["packages"]
    assert entry["manifestSha256"] == sha256_file(result.artifact / "manifest.json")
    assert entry["manifestSha256"] == result.manifest_sha256
    assert entry["mode"] == "staging" and entry["artifact"] == result.artifact.name
    assert [(e["projectId"], e["sourceRevision"]) for e in entry["exhibits"]] == [("stars", 3)]
    assert entry["publicFiles"] and all(k.startswith("media/") for k in entry["publicFiles"])
    subject = ContentRepo(content_of(built)).log(1)[0].subject
    assert subject.startswith("Register Pages package")


def test_c9_addresses_map_to_pages_files(built: Path) -> None:
    site = package(built).upload_dir
    assert served_file(site, "/") == ("index.html", 200)
    assert served_file(site, "/work/") == ("work/index.html", 200)
    assert served_file(site, "/work/stars") == ("work/stars/index.html", 200)
    assert served_file(site, "/category/astronomy") == ("category/astronomy/index.html", 200)
    assert served_file(site, "/category/woodworking") == ("404.html", 404)
    assert served_file(site, "/work/risk") == ("404.html", 404)
    assert served_file(site, "/work/../_headers") == ("404.html", 404)


def test_headers_file_content() -> None:
    staging = headers_file("staging", [])
    for line in (
        "  Content-Security-Policy: default-src 'self'; frame-ancestors 'none'",
        "  Strict-Transport-Security: max-age=31536000",
        "  X-Content-Type-Options: nosniff",
        "  Referrer-Policy: strict-origin-when-cross-origin",
        "  Cache-Control: no-cache",
        "  X-Robots-Tag: noindex",
    ):
        assert line in staging.splitlines()
    assets = staging.split("/assets/*\n", 1)[1].split("/media/*", 1)[0]
    assert "! Cache-Control" in assets and "immutable" in assets
    assert "X-Robots-Tag" not in headers_file("production", [])


def test_download_headers_are_exactly_fr4_4() -> None:
    """NP-5: octet-stream for every type (PDF too), attachment, nosniff, sandboxing CSP."""
    text = headers_file("staging", ["files/ast_abcdefghijklmnop/plans.pdf"])
    rule = text.split("/files/ast_abcdefghijklmnop/plans.pdf\n", 1)[1].splitlines()
    assert rule == [
        "  ! Cache-Control",
        "  Cache-Control: public, max-age=31536000, immutable",
        "  ! Content-Type",
        "  Content-Type: application/octet-stream",
        "  Content-Disposition: attachment",
        "  ! X-Content-Type-Options",
        "  X-Content-Type-Options: nosniff",
        "  ! Content-Security-Policy",
        "  Content-Security-Policy: sandbox; default-src 'none'",
    ]


def test_too_many_header_rules_are_refused() -> None:
    keys = [f"files/ast_abcdefghijklmnop/f{n}.zip" for n in range(120)]
    with pytest.raises(PagesError, match="header rules"):
        headers_file("staging", keys)


def test_missing_build_is_refused(service: StudioService) -> None:
    with pytest.raises(PagesError, match="run 'build' first"):
        package_pages(service.store.root, default_output(service.store.root), SCANNER)


def test_build_without_a_passed_scan_is_refused(built: Path) -> None:
    path = manifest_path(built)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["scan"]["passed"] = False
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(PagesError, match="scan did not pass"):
        package(built)
    path.unlink()
    with pytest.raises(PagesError, match="manifest"):
        package(built)


def test_build_changed_after_its_scan_is_refused(built: Path) -> None:
    (built / "work" / "stars" / "index.html").write_text("<p>edited by hand</p>", "utf-8")
    with pytest.raises(PagesError, match="changed after it was built"):
        package(built)


def test_oversize_file_is_refused(built: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pages, "MAX_FILE_BYTES", 100)
    with pytest.raises(PagesError, match="25 MiB"):
        package(built)


def test_too_many_files_are_refused(built: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pages, "MAX_FILES", 3)
    with pytest.raises(PagesError, match="over the Pages limit of 3"):
        package(built)
    assert not [p for p in built.parent.iterdir() if p.name.startswith("pages-")]
    assert load_register(content_of(built))["packages"] == []


def test_artifacts_inside_the_code_repository_are_refused(built: Path) -> None:
    with pytest.raises(ContentLocationError):
        package_pages(code_root(), built, SCANNER)


def test_package_rename_retries_transient_windows_errors(
    built: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NP-7: the final rename uses rename_with_retry."""
    import portfolio_studio.build as build_module

    monkeypatch.setattr(build_module, "RENAME_BACKOFF_SECONDS", 0.0)
    original = Path.rename
    failures = {"left": 2}

    def rename(self: Path, target: Any) -> Path:
        if self.name.endswith(".tmp") and failures["left"]:
            failures["left"] -= 1
            error = PermissionError(13, "Access is denied")
            error.winerror = 5  # type: ignore[attr-defined]
            raise error
        return original(self, target)

    monkeypatch.setattr(Path, "rename", rename)
    assert package(built).artifact.is_dir() and failures["left"] == 0


# --- deploy: validation against the register (NP-1) ------------------------------------------


def test_registered_artifact_dry_run(built: Path, wrangler: Path) -> None:
    artifact = package(built).artifact
    lines: list[str] = []
    runner = FakeWrangler()
    code = deployer(built, wrangler, runner, lines=lines).deploy(artifact, "portfolio", False)
    out = "\n".join(lines)
    assert code == 0 and runner.calls == []
    assert "DRY RUN" in out and "stars (revision 3)" in out and "Add --execute" in out
    assert f"Registered: manifest sha256 {sha256_file(artifact / 'manifest.json')}" in out
    assert "_headers regenerated and identical" in out and "scan_output: OK" in out
    assert "wrangler.js pages deploy" in out and "npx" not in out
    assert "--project-name portfolio --branch staging" in out
    assert TOKEN not in out and ACCOUNT not in out


def test_bypass_worker_and_private_text_with_recomputed_manifest(
    built: Path, wrangler: Path
) -> None:
    """Re-review probe 1: _worker.js plus private text, manifest recomputed (and even
    re-registered): the special-file check and the re-run scan refuse it."""
    artifact = package(built).artifact
    (artifact / "site" / "_worker.js").write_text("export default {}", encoding="utf-8")
    (artifact / "site" / "index.html").write_text("<p>PRIVATE DRAFT TEXT</p>", "utf-8")
    forge_registration(content_of(built), artifact)
    with pytest.raises(PagesError, match="special files"):
        deployer(built, wrangler).deploy(artifact, "portfolio", False)
    (artifact / "site" / "_worker.js").unlink()
    forge_registration(content_of(built), artifact)
    with pytest.raises(StudioError, match="public-output scan failed"):
        deployer(built, wrangler).deploy(artifact, "portfolio", False)


def test_bypass_recomputed_manifest_without_registration(built: Path, wrangler: Path) -> None:
    artifact = package(built).artifact
    (artifact / "site" / "index.html").write_text("<p>PRIVATE DRAFT TEXT</p>", "utf-8")
    manifest_file = artifact / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["files"]["index.html"]["sha256"] = sha256_file(artifact / "site" / "index.html")
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(PagesError, match="not in the package register"):
        deployer(built, wrangler).deploy(artifact, "portfolio", False)


def test_bypass_headers_stripped(built: Path, wrangler: Path) -> None:
    """Re-review probe 2: _headers without CSP or noindex, manifest recomputed."""
    artifact = package(built).artifact
    (artifact / "site" / "_headers").write_text("/*\n  X-Frame-Options: DENY\n", "utf-8")
    forge_registration(content_of(built), artifact)
    with pytest.raises(PagesError, match="_headers differs"):
        deployer(built, wrangler).deploy(artifact, "portfolio", False)


def test_bypass_staging_relabelled_production(built: Path, wrangler: Path) -> None:
    """Re-review probe 3: the manifest says production while the register says staging; and
    with the register forged as well, production is still never deployed."""
    artifact = package(built).artifact
    manifest_file = artifact / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["mode"] = "production"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    register = load_register(content_of(built))
    register["packages"][0]["manifestSha256"] = sha256_file(manifest_file)
    (content_of(built) / REGISTER).write_text(json.dumps(register), encoding="utf-8")
    with pytest.raises(PagesError, match="mode differs from the register"):
        deployer(built, wrangler).deploy(artifact, "portfolio", False)
    forge_registration(content_of(built), artifact, mode="production")
    with pytest.raises(PagesError, match="only staging artifacts"):
        deployer(built, wrangler).deploy(artifact, "portfolio", False)


def test_bypass_hand_made_folder(built: Path, wrangler: Path) -> None:
    """Re-review probe 4: a folder with a forged artifact manifest and arbitrary HTML."""
    fake = content_of(built) / "build" / "pages-20990101T000000Z"
    (fake / "site").mkdir(parents=True)
    (fake / "site" / "index.html").write_text("<p>anything</p>", encoding="utf-8")
    manifest = {
        "schema": "portfolio-pages-artifact/1",
        "uploadDir": "site",
        "mode": "staging",
        "files": {"index.html": {"sha256": sha256_file(fake / "site" / "index.html"), "bytes": 15}},
    }
    (fake / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(PagesError, match="not in the package register"):
        deployer(built, wrangler).deploy(fake, "portfolio", False)


@pytest.mark.parametrize(
    "extra",
    ["functions/api.js", "_routes.json", "_redirects", ".well-known/x.txt", "work/.hidden"],
)
def test_pages_special_files_and_dotfiles_are_refused(
    built: Path, wrangler: Path, extra: str
) -> None:
    artifact = package(built).artifact
    path = artifact / "site" / extra
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    forge_registration(content_of(built), artifact)
    with pytest.raises(PagesError, match="special files or dotfiles"):
        deployer(built, wrangler).deploy(artifact, "portfolio", False)


def test_worker_directory_is_refused(built: Path, wrangler: Path) -> None:
    artifact = package(built).artifact
    (artifact / "site" / "_worker.js").mkdir()
    (artifact / "site" / "_worker.js" / "index.js").write_text("x", encoding="utf-8")
    forge_registration(content_of(built), artifact)
    with pytest.raises(PagesError, match="special files"):
        deployer(built, wrangler).deploy(artifact, "portfolio", False)


def test_tampered_file_and_scan_inputs_are_refused(built: Path, wrangler: Path) -> None:
    artifact = package(built).artifact
    (artifact / "scan-inputs" / "snapshot.json").write_text("{}", encoding="utf-8")
    with pytest.raises(PagesError, match="scan inputs differ"):
        deployer(built, wrangler).deploy(artifact, "portfolio", False)
    second = package(built).artifact
    (second / "site" / "404.html").write_text("<p>swapped</p>", encoding="utf-8")
    with pytest.raises(PagesError, match="changed after packaging"):
        deployer(built, wrangler).deploy(second, "portfolio", False)


@pytest.mark.parametrize(
    "path",
    ["relative/pages-20261015T000000Z", "{build}/pages-x&calc", "{build}/pages-%TOKEN%"],
)
def test_artifact_path_is_validated(built: Path, wrangler: Path, path: str) -> None:
    """NP-4: absolute, no shell metacharacters, a pages-<timestamp> folder in build/."""
    artifact = Path(path.format(build=content_of(built) / "build"))
    with pytest.raises(PagesError, match=r"absolute|not allowed|pages-<timestamp>"):
        deployer(built, wrangler).deploy(artifact, "portfolio", False)
    other = content_of(built).parent / "pages-20261015T000000Z"
    with pytest.raises(PagesError, match="pages-<timestamp>"):
        deployer(built, wrangler).deploy(other, "portfolio", False)


# --- deploy: staging only (NP-2) and the production branch (NP-6) ----------------------------


@pytest.mark.parametrize(
    "flags",
    [
        ["--production"],
        ["--branch", "main"],
        ["--branch", "staging"],
        ["--i-have-owner-authorization"],
    ],
)
def test_no_production_or_branch_flags_exist(tmp_path: Path, flags: list[str]) -> None:
    with pytest.raises(SystemExit):
        main(["deploy-pages", "--artifact", str(tmp_path), *flags])


def test_production_package_never_deploys(built: Path, wrangler: Path) -> None:
    artifact = package(built, mode="production").artifact
    assert "X-Robots-Tag" not in (artifact / "site" / "_headers").read_text(encoding="utf-8")
    runner = FakeWrangler()
    with pytest.raises(PagesError, match="only staging artifacts"):
        deployer(built, wrangler, runner).deploy(artifact, "portfolio", True)
    assert runner.calls == []


def test_execute_deploys_to_staging_once_without_git_or_shell(built: Path, wrangler: Path) -> None:
    artifact = package(built).artifact
    runner, api, lines = FakeWrangler(), FakeApi(), []
    code = deployer(built, wrangler, runner, api, lines=lines).deploy(artifact, "portfolio", True)
    assert code == 0 and len(runner.calls) == 1
    argv, cwd, environment, _ = runner.calls[0]
    assert argv[:4] == ["node", str(wrangler), "pages", "deploy"]
    assert argv[4] == str(artifact.resolve() / "site")
    assert argv[argv.index("--branch") + 1] == "staging"
    assert all(TOKEN not in part for part in argv)
    assert environment["CLOUDFLARE_API_TOKEN"] == TOKEN
    assert environment["GIT_DIR"].endswith("no-git") and cwd != artifact
    assert api.requests[0][1].endswith(f"/accounts/{ACCOUNT}/pages/projects/portfolio")
    assert api.requests[0][2]["Authorization"] == f"Bearer {TOKEN}"
    out = "\n".join(lines)
    assert "EXECUTING the staging deploy" in out and TOKEN not in out
    deployment = load_register(content_of(built))["deployments"][-1]
    assert deployment["branch"] == "staging"
    assert deployment["manifestSha256"] == sha256_file(artifact / "manifest.json")


@pytest.mark.parametrize(("status", "branch"), [(200, "staging"), (200, None), (403, "x")])
def test_staging_refused_when_the_production_branch_is_unsafe(
    built: Path, wrangler: Path, status: int, branch: str | None
) -> None:
    """NP-6: a project whose production branch is staging, unset or unreadable is refused."""
    artifact = package(built).artifact
    runner = FakeWrangler()
    with pytest.raises(PagesError, match=r"production branch|Cloudflare answered"):
        deployer(built, wrangler, runner, FakeApi(status, branch)).deploy(
            artifact, "portfolio", True
        )
    assert runner.calls == []


def test_unreachable_api_is_refused_without_the_token(built: Path, wrangler: Path) -> None:
    def broken(method: str, url: str, headers: Any) -> tuple[int, bytes]:
        raise OSError(f"cannot connect; headers were {headers}")

    artifact = package(built).artifact
    deploy = Deployer(
        content=content_of(built),
        environment=CREDENTIALS,
        runner=FakeWrangler(),
        fetch=broken,
        wrangler=wrangler,
        out=lambda _: None,
    )
    with pytest.raises(PagesError) as raised:
        deploy.deploy(artifact, "portfolio", True)
    assert TOKEN not in str(raised.value)


@pytest.mark.parametrize(
    ("project", "environment", "reason"),
    [
        (None, CREDENTIALS, "--project"),
        ("Bad Name", CREDENTIALS, "lowercase"),
        ("portfolio", {}, "CLOUDFLARE_API_TOKEN"),
        ("portfolio", {"CLOUDFLARE_API_TOKEN": TOKEN, "CLOUDFLARE_ACCOUNT_ID": "x"}, "32 hex"),
    ],
)
def test_execute_runs_nothing_without_every_guard(
    built: Path, wrangler: Path, project: str | None, environment: dict[str, str], reason: str
) -> None:
    artifact = package(built).artifact
    runner, api, lines = FakeWrangler(), FakeApi(), []
    code = deployer(built, wrangler, runner, api, environment, lines).deploy(
        artifact, project, True
    )
    out = "\n".join(lines)
    assert code == 1 and runner.calls == [] and api.requests == []
    assert reason in out and TOKEN not in out


def test_wrangler_must_be_the_pinned_local_install(
    built: Path, wrangler: Path, tmp_path: Path
) -> None:
    artifact = package(built).artifact
    (wrangler.parent.parent / "package.json").write_text('{"version": "4.0.0"}', "utf-8")
    with pytest.raises(PagesError, match=r"4.149.0 is required"):
        deployer(built, wrangler).deploy(artifact, "portfolio", True)
    with pytest.raises(PagesError, match="npm --prefix tools/pages-deploy ci"):
        deployer(built, tmp_path / "missing" / "wrangler.js").deploy(artifact, "portfolio", True)


def test_node_must_not_be_a_batch_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.undo()
    monkeypatch.setattr(pages_deploy.shutil, "which", lambda _: "C:\\npm\\node.CMD")
    with pytest.raises(PagesError, match="node is not installed"):
        pages_deploy.node_executable()


def test_a_wrangler_configuration_on_the_path_is_refused(tmp_path: Path) -> None:
    (tmp_path / "wrangler.toml").write_text('name = "x"', encoding="utf-8")
    folder = tmp_path / "a" / "b"
    folder.mkdir(parents=True)
    with pytest.raises(PagesError, match="Wrangler configuration"):
        pages_deploy.check_no_wrangler_config(folder)


def test_only_the_scanned_site_is_uploaded_and_nothing_private_is_in_it(built: Path) -> None:
    """LS-7: deploy uploads only site/; manifests and scan inputs stay outside it."""
    artifact = package(built).artifact
    upload = artifact / "site"
    names = {p.name for p in upload.rglob("*")}
    assert not names & {"manifest.json", "site.build.json", "snapshot.json", "media-digests.json"}
    for path in upload.rglob("*"):
        if path.suffix in (".html", ".json") or path.name == "_headers":
            assert "generation" not in path.read_text(encoding="utf-8")
    assert json.loads(manifest_path(built).read_text(encoding="utf-8"))["generation"] == 0


# --- prune after take-down (NP-3) ------------------------------------------------------------


def test_deploy_after_take_down_prunes_older_staging_deployments(
    service: StudioService, builder: SiteBuilder, built: Path, wrangler: Path
) -> None:
    ready_project(service, "Baduk")
    publish(service, "baduk")
    builder.build(built)
    first = package(built).artifact
    runner = FakeWrangler()
    deployer(built, wrangler, runner).deploy(first, "portfolio", True)
    assert [argv[3] for argv, *_ in runner.calls] == ["deploy"]  # nothing removed: no prune
    service.take_down("baduk", "Baduk")
    builder.build(built)
    second = package(built).artifact
    runner, lines = FakeWrangler(), []
    deployer(built, wrangler, runner, lines=lines).deploy(second, "portfolio", True)
    assert runner.calls[0][0][3] == "deploy"
    assert runner.calls[1][0][3:5] == ["deployment", "list"]
    deleted = [argv[5] for argv, *_ in runner.calls if argv[4:5] == ["delete"]]
    assert deleted == [LISTING[1]["Id"], LISTING[2]["Id"]]  # never the newest or production
    assert all("--force" in argv for argv, *_ in runner.calls if "delete" in argv)
    out = "\n".join(lines)
    assert "pruning older deployments" in out and "cached" in out and TOKEN not in out


def test_prune_is_a_dry_run_by_default(built: Path, wrangler: Path) -> None:
    runner, lines = FakeWrangler(), []
    assert deployer(built, wrangler, runner, lines=lines).prune("portfolio", False) == 0
    assert runner.calls == [] and "DRY RUN" in "\n".join(lines)
    assert deployer(built, wrangler, runner, lines=lines).prune(None, True) == 1
    assert runner.calls == []
    assert deployer(built, wrangler, runner, lines=lines).prune("portfolio", True) == 0
    assert len([1 for argv, *_ in runner.calls if "delete" in argv]) == 2


def test_stale_deployments_parsing() -> None:
    stale, skipped = stale_deployments(json.dumps(LISTING))
    assert stale == [LISTING[1]["Id"], LISTING[2]["Id"]] and skipped == 1
    with pytest.raises(PagesError):
        stale_deployments("not json")
    odd = [{"Id": "x; rm", "Environment": "Preview", "Branch": "staging"}] * 2
    with pytest.raises(PagesError):
        stale_deployments(json.dumps(odd))


# --- CLI -------------------------------------------------------------------------------------


def test_cli_deploy_and_prune_dry_runs(
    built: Path,
    wrangler: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", TOKEN)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    artifact = package(built).artifact
    content = str(content_of(built))
    assert main(["deploy-pages", "--content", content, "--artifact", str(artifact)]) == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out and "CLOUDFLARE_ACCOUNT_ID NOT set" in out and TOKEN not in out
    code = main(["deploy-pages", "--content", content, "--artifact", str(artifact), "--execute"])
    assert code == 1 and TOKEN not in capsys.readouterr().out
    assert main(["prune-deployments", "--content", content]) == 0
    assert "DRY RUN" in capsys.readouterr().out
    args = argparse.Namespace(artifact=artifact, project="portfolio", execute=False)
    fake = deployer(built, wrangler)
    assert cmd_deploy_pages(args, content_of(built), fake) == 0
    assert cmd_prune_deployments(args, content_of(built), fake) == 0
