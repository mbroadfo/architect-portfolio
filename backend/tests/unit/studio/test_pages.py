"""Cloudflare Pages packaging and the guarded deploy. No Cloudflare call is ever made: the
deploy runner is injected, and the real one is never used here."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pytest
from portfolio_studio import pages
from portfolio_studio.build import SiteBuilder, default_output, manifest_path
from portfolio_studio.cli import cmd_deploy_pages
from portfolio_studio.errors import ContentLocationError
from portfolio_studio.location import code_root
from portfolio_studio.pages import (
    PagesError,
    headers_file,
    package_pages,
    plan_deploy,
    served_file,
    verify_artifact,
)
from portfolio_studio.service import StudioService

from .conftest import publish, ready_project

SCANNER = code_root() / "scripts" / "scan_output.py"
TOKEN = "cf-secret-token-value-1234567890"
ACCOUNT = "account-id-abcdef0123456789"
CREDENTIALS = {"CLOUDFLARE_API_TOKEN": TOKEN, "CLOUDFLARE_ACCOUNT_ID": ACCOUNT}


@pytest.fixture
def built(service: StudioService, builder: SiteBuilder) -> Path:
    """A throwaway content repository with STARS published and the site built."""
    ready_project(service, "STARS")
    publish(service, "stars")
    output = default_output(service.store.root)
    builder.build(output)
    return output


def package(built: Path, **options: Any) -> pages.PackageResult:
    return package_pages(built, built.parent, SCANNER, **options)


class Runner:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], Path, dict[str, str]]] = []

    def __call__(self, argv: list[str], cwd: Path, environment: dict[str, str]) -> int:
        self.calls.append((argv, cwd, environment))
        return 0


def deploy_args(artifact: Path, **options: Any) -> argparse.Namespace:
    values = {
        "artifact": artifact,
        "project": None,
        "branch": None,
        "production": False,
        "authorized": False,
        "execute": False,
    }
    values.update(options)
    return argparse.Namespace(**values)


# --- packaging ------------------------------------------------------------------------------


def test_package_copies_the_build_and_adds_only_headers(built: Path) -> None:
    result = package(built)
    site = result.upload_dir
    build = json.loads(manifest_path(built).read_text(encoding="utf-8"))
    present = {p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file()}
    assert present == set(build["files"]) | {"_headers"}
    assert not (site / "_redirects").exists()
    assert not (site / "manifest.json").exists()  # the manifest is never uploaded
    manifest = json.loads((result.artifact / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["mode"] == "staging" and manifest["noindex"] is True
    assert manifest["sourceBuild"]["buildId"] == build["buildId"]
    assert manifest["sourceBuild"]["scan"]["passed"] is True
    assert manifest["packageScan"]["summary"].startswith("scan_output: OK")
    assert [(e["projectId"], e["sourceRevision"]) for e in manifest["exhibits"]] == [("stars", 3)]
    assert manifest["fileCount"] == len(present)
    assert manifest["totalBytes"] == sum((site / k).stat().st_size for k in present)
    assert set(manifest["files"]) == present
    assert result.artifact.parent == built.parent
    assert result.artifact.name.startswith("pages-")


def test_c9_addresses_map_to_pages_files(built: Path) -> None:
    """/work/<slug> is work/<slug>/index.html; anything else gets the root 404.html (404)."""
    site = package(built).upload_dir
    assert served_file(site, "/") == ("index.html", 200)
    assert served_file(site, "/work/") == ("work/index.html", 200)
    assert served_file(site, "/work/stars") == ("work/stars/index.html", 200)
    assert served_file(site, "/work/stars/") == ("work/stars/index.html", 200)
    assert served_file(site, "/category/astronomy") == ("category/astronomy/index.html", 200)
    assert served_file(site, "/category/woodworking") == ("404.html", 404)
    assert served_file(site, "/work/risk") == ("404.html", 404)
    assert served_file(site, "/work/../_headers") == ("404.html", 404)
    assert served_file(site, "/404.html") == ("404.html", 404)
    media = next((site / "media").rglob("w480.jpg")).relative_to(site).as_posix()
    assert served_file(site, f"/{media}") == (media, 200)


def test_headers_file_content() -> None:
    staging = headers_file("staging", [])
    assert "/*\n" in staging
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
    assert "immutable" in staging.split("/media/*\n", 1)[1]
    assert "Content-Disposition" not in staging
    production = headers_file("production", ["files/ast_abcdefghijklmnop/plans.pdf"])
    assert "X-Robots-Tag" not in production
    download = production.split("/files/ast_abcdefghijklmnop/plans.pdf\n", 1)[1]
    assert "Content-Disposition: attachment" in download
    assert "Content-Type: application/pdf" in download and "! Content-Type" in download


def test_too_many_header_rules_are_refused() -> None:
    keys = [f"files/ast_abcdefghijklmnop/f{n}.zip" for n in range(120)]
    with pytest.raises(PagesError, match="header rules"):
        headers_file("staging", keys)


def test_staging_package_sends_noindex(built: Path) -> None:
    headers = (package(built).upload_dir / "_headers").read_text(encoding="utf-8")
    assert "X-Robots-Tag: noindex" in headers


def test_production_needs_the_owner_authorization_flag(built: Path) -> None:
    with pytest.raises(PagesError, match="i-have-owner-authorization"):
        package(built, mode="production")
    result = package(built, mode="production", owner_authorized=True)
    assert "X-Robots-Tag" not in (result.upload_dir / "_headers").read_text(encoding="utf-8")


def test_missing_build_is_refused(service: StudioService) -> None:
    with pytest.raises(PagesError, match="run 'build' first"):
        package(default_output(service.store.root))


def test_build_without_a_passed_scan_is_refused(built: Path) -> None:
    path = manifest_path(built)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["scan"]["passed"] = False
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(PagesError, match="scan did not pass"):
        package(built)
    del manifest["schema"]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(PagesError, match="no scan record"):
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


def test_artifacts_inside_the_code_repository_are_refused(built: Path) -> None:
    with pytest.raises(ContentLocationError):
        package_pages(built, code_root() / "pages-out", SCANNER)


# --- deploy ---------------------------------------------------------------------------------


def test_tampered_artifact_is_detected(built: Path) -> None:
    artifact = package(built).artifact
    verify_artifact(artifact)
    (artifact / "site" / "index.html").write_text("<p>swapped</p>", encoding="utf-8")
    with pytest.raises(PagesError, match="changed after packaging"):
        verify_artifact(artifact)
    (artifact / "site" / "extra.html").write_text("x", encoding="utf-8")
    with pytest.raises(PagesError, match="differ from its manifest"):
        plan_deploy(artifact, "portfolio", None, False, False, CREDENTIALS)


def test_dry_run_prints_the_command_and_summary_and_never_the_token(
    built: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artifact = package(built).artifact
    runner = Runner()
    code = cmd_deploy_pages(
        deploy_args(artifact, project="portfolio"), environment=CREDENTIALS, runner=runner
    )
    out = capsys.readouterr().out
    assert code == 0 and runner.calls == []
    assert "DRY RUN" in out and "stars (revision 3)" in out
    assert f"wrangler@{pages.WRANGLER_VERSION} pages deploy" in out
    assert "--project-name portfolio --branch staging" in out
    assert "CLOUDFLARE_API_TOKEN set" in out and "Add --execute" in out
    assert TOKEN not in out and ACCOUNT not in out


def test_execute_runs_nothing_without_every_guard(
    built: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artifact = package(built).artifact
    runner = Runner()
    refused = [
        ({"execute": True}, CREDENTIALS, "--project"),
        ({"execute": True, "project": "portfolio", "branch": "main"}, CREDENTIALS, "staging"),
        ({"execute": True, "project": "Bad Name"}, CREDENTIALS, "lowercase"),
        ({"execute": True, "project": "portfolio"}, {}, "CLOUDFLARE_API_TOKEN"),
        (
            {"execute": True, "project": "portfolio", "production": True, "branch": "main"},
            CREDENTIALS,
            "i-have-owner-authorization",
        ),
        (
            {
                "execute": True,
                "project": "portfolio",
                "production": True,
                "authorized": True,
                "branch": "main",
            },
            CREDENTIALS,
            "packaged for staging",
        ),
    ]
    for options, environment, reason in refused:
        code = cmd_deploy_pages(deploy_args(artifact, **options), environment, runner)
        out = capsys.readouterr().out
        assert code == 1, options
        assert reason in out, (reason, out)
        assert TOKEN not in out
    assert runner.calls == []
    with pytest.raises(PagesError):
        pages.execute_deploy(
            plan_deploy(artifact, None, None, False, False, CREDENTIALS), CREDENTIALS, runner
        )
    assert runner.calls == []


def test_execute_with_every_guard_runs_wrangler_once_without_git(
    built: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    artifact = package(built).artifact
    runner = Runner()
    code = cmd_deploy_pages(
        deploy_args(artifact, project="portfolio", branch="staging", execute=True),
        environment=CREDENTIALS,
        runner=runner,
    )
    out = capsys.readouterr().out
    assert code == 0 and len(runner.calls) == 1
    argv, cwd, environment = runner.calls[0]
    assert argv[6:10] == ["--project-name", "portfolio", "--branch", "staging"]
    assert argv[5] == str(artifact.resolve() / "site")
    assert TOKEN not in " ".join(argv)  # credentials only through the environment
    assert environment["CLOUDFLARE_API_TOKEN"] == TOKEN
    assert environment["WRANGLER_SEND_METRICS"] == "false"
    assert environment["GIT_DIR"].endswith("no-git")
    assert artifact not in cwd.parents and cwd != artifact
    assert TOKEN not in out and "EXECUTING" in out


def test_production_deploy_needs_production_artifact_and_flags(built: Path) -> None:
    artifact = package(built, mode="production", owner_authorized=True).artifact
    runner = Runner()
    plan = plan_deploy(artifact, "portfolio", "main", True, True, CREDENTIALS)
    assert plan.executable
    assert pages.execute_deploy(plan, CREDENTIALS, runner) == 0
    staging_plan = plan_deploy(artifact, "portfolio", "staging", False, False, CREDENTIALS)
    assert "packaged for production" in " ".join(staging_plan.refusals)
    no_branch = plan_deploy(artifact, "portfolio", None, True, True, CREDENTIALS)
    assert "production branch" in " ".join(no_branch.refusals)


def test_deploy_pages_through_main_is_a_dry_run(
    built: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from portfolio_studio.cli import main

    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", TOKEN)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    artifact = package(built).artifact
    assert main(["deploy-pages", "--artifact", str(artifact), "--project", "portfolio"]) == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out and "CLOUDFLARE_ACCOUNT_ID NOT set" in out and TOKEN not in out
    assert main(["deploy-pages", "--artifact", str(artifact), "--execute"]) == 1
    assert TOKEN not in capsys.readouterr().out


def test_only_the_scanned_site_is_uploaded_and_nothing_private_is_in_it(built: Path) -> None:
    """LS-7: deploy uploads only site/; the artifact manifest, <out>.build.json and the scan
    inputs stay outside it, and no private repository value (commit count) is inside."""
    artifact = package(built).artifact
    plan = plan_deploy(artifact, "portfolio", "staging", False, False, CREDENTIALS)
    upload = Path(plan.command[5])
    assert upload == artifact.resolve() / "site"
    names = {p.name for p in upload.rglob("*")}
    assert not names & {"manifest.json", "site.build.json", "snapshot.json", "media-digests.json"}
    assert not any(name.endswith((".build.json", ".scan-inputs")) for name in names)
    for path in upload.rglob("*"):
        if path.suffix in (".html", ".json") or path.name == "_headers":
            assert "generation" not in path.read_text(encoding="utf-8")
    build = json.loads(manifest_path(built).read_text(encoding="utf-8"))
    assert build["generation"] == 0  # not the content repository's commit count
    inputs = built.with_name("site.scan-inputs") / "snapshot.json"
    assert json.loads(inputs.read_text(encoding="utf-8"))["generation"] == 0
