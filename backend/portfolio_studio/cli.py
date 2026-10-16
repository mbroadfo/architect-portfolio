"""``python -m portfolio_studio <command>``.

Commands::

    init              --content <dir>
    serve             --content <dir> [--port 8765] [--site-port 8766]
    import-prototype  --content <dir> --project stars|baduk [--prototype <dir>]
    build             --content <dir> [--out <dir>]
    serve-site        --content <dir> [--out <dir>] [--port 8766]
    backup            --content <dir> --to <file.bundle>
    package-pages     --content <dir> [--site <build>] [--staging | --production]
                      (registers the artifact in <content>/deployments/packages.json)
    deploy-pages      --content <dir> --artifact <content>/build/pages-<ts> [--project P]
                      [--execute]     (dry run unless --execute; staging branch only)
    prune-deployments --content <dir> [--project P] [--execute]
                      (dry run unless --execute; deletes older staging deployments)

``--content`` defaults to ``architect-portfolio-content`` beside the code repository.
Exit codes: 0 success; 1 the operation failed; 2 usage error.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from portfolio_api.slice.renderer import Mode

from portfolio_studio.build import RendererAssets, SiteBuilder, default_output, run_build
from portfolio_studio.errors import ContentLocationError, StudioError
from portfolio_studio.github import RepositoryChecker
from portfolio_studio.importer import default_prototype_dir, import_project
from portfolio_studio.location import (
    check_content_dir,
    check_outside_code,
    code_root,
    default_content_dir,
)
from portfolio_studio.locking import ContentLock
from portfolio_studio.pages import package_pages
from portfolio_studio.pages_deploy import Deployer
from portfolio_studio.renderer import (
    CliRenderer,
    RenderOutput,
    StudioRenderer,
    cli_path,
    default_renderer_root,
)
from portfolio_studio.server import LOOPBACK, ServerConfig, check_bind_host, configure_logging
from portfolio_studio.service import StudioService
from portfolio_studio.store import ContentStore

DEFAULT_PORT = 8765
RENDERER_HELP = "the renderer folder (default: web/slice-renderer; uses dist/cli.cjs)"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m portfolio_studio")
    commands = parser.add_subparsers(dest="command", required=True)

    def command(name: str, help_text: str) -> argparse.ArgumentParser:
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--content", type=Path, default=None, help="the content repository")
        return sub

    command("init", "create the private content repository")
    serve = command("serve", "start the Studio on 127.0.0.1")
    serve.add_argument("--host", default=LOOPBACK, help=argparse.SUPPRESS)
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--site-port", type=int, default=None, help="default: port + 1; 0 = off")
    serve.add_argument("--renderer-root", type=Path, default=None, help=RENDERER_HELP)
    seed = command("import-prototype", "create a Draft from the prototype (never publishes)")
    seed.add_argument("--project", choices=("stars", "baduk"), required=True)
    seed.add_argument("--prototype", type=Path, default=None, help="the prototype folder")
    build = command("build", "generate the public site from published versions only")
    build.add_argument("--out", type=Path, default=None)
    build.add_argument("--renderer-root", type=Path, default=None, help=RENDERER_HELP)
    site = command("serve-site", "serve the generated site on 127.0.0.1")
    site.add_argument("--out", type=Path, default=None)
    site.add_argument("--port", type=int, default=DEFAULT_PORT + 1)
    backup = command("backup", "write a Git bundle of the content repository")
    backup.add_argument("--to", type=Path, required=True)
    package = command("package-pages", "package the last scanned build for Cloudflare Pages")
    package.add_argument("--site", type=Path, default=None, help="the build (default build/site)")
    modes = package.add_mutually_exclusive_group()
    modes.add_argument("--staging", action="store_true", help="the default: noindex everywhere")
    modes.add_argument(
        "--production", action="store_true", help="no noindex; packaged only, never deployed here"
    )
    deploy = command("deploy-pages", "dry run (default) or the staging Pages upload of an artifact")
    deploy.add_argument(
        "--artifact", type=Path, required=True, help="a registered pages-<ts> folder"
    )
    deploy.add_argument("--project", default=None, help="the Pages project name")
    deploy.add_argument("--execute", action="store_true", help="actually upload (default: dry run)")
    prune = command("prune-deployments", "dry run (default) or delete older staging deployments")
    prune.add_argument("--project", default=None, help="the Pages project name")
    prune.add_argument("--execute", action="store_true", help="actually delete (default: dry run)")
    return parser


def _renderer_root(path: Path | None) -> Path:
    return path or default_renderer_root(code_root())


def _renderer(root: Path) -> CliRenderer:
    cli = cli_path(root)
    if not cli.is_file():
        raise StudioError(
            f"the renderer CLI {cli} is missing; run 'npm --prefix web/slice-renderer ci' and "
            "'npm --prefix web/slice-renderer run build:cli'"
        )
    node = shutil.which("node")
    if node is None:
        raise StudioError("node is not installed or not on PATH")
    return CliRenderer((node, str(cli)))


def _service(store: ContentStore, renderer: StudioRenderer) -> StudioService:
    return StudioService(store, renderer, RepositoryChecker())


def cmd_init(content: Path) -> int:
    resolved = check_content_dir(content, must_exist=False)
    if resolved.exists() and any(resolved.iterdir()):
        raise ContentLocationError(f"{resolved} already exists and is not empty")
    resolved.mkdir(parents=True, exist_ok=True)
    store = ContentStore(resolved)
    store.git.init()
    check_content_dir(resolved)
    store.initialize()
    store.git.commit(
        ["README.md", ".gitignore", "studio.json", "projects", "published", "withdrawn"],
        "Create the private content repository",
    )
    print(f"Created the private content repository at {resolved}")
    print("It has no remote. Never push it to a public remote.")
    return 0


def _open_store(content: Path) -> ContentStore:
    store = ContentStore(check_content_dir(content))
    if store.git.is_dirty():
        raise StudioError(
            f"{store.root} has uncommitted changes; commit or discard them first "
            "(the Studio commits every change it makes)"
        )
    return store


def cmd_serve(args: argparse.Namespace, content: Path) -> int:
    import uvicorn

    from portfolio_studio.server import create_app
    from portfolio_studio.site_server import start_in_background

    host = check_bind_host(args.host)
    store = _open_store(content)
    with ContentLock(store.root):
        renderer_root = _renderer_root(args.renderer_root)
        renderer = _renderer(renderer_root)
        service = _service(store, renderer)
        assets = RendererAssets.from_renderer_root(renderer_root)
        output = default_output(store.root)
        site_port = args.port + 1 if args.site_port is None else args.site_port
        site_url = f"http://{LOOPBACK}:{site_port}/" if site_port else None
        if site_port:
            output.mkdir(parents=True, exist_ok=True)
            start_in_background(output, host, site_port)
        config = ServerConfig(
            port=args.port,
            ui_dir=code_root() / "web" / "local-studio" / "dist",
            static_dir=assets.static_dir,
            site_output=output,
            site_url=site_url,
        )
        app = create_app(service, SiteBuilder(store, renderer, assets), config)
        print(f"Studio: http://{LOOPBACK}:{args.port}/  (content: {store.root})")
        if site_url:
            print(f"Generated site: {site_url}  (from {output})")
        uvicorn.run(app, host=host, port=args.port, log_level="warning", access_log=False)
    return 0


def cmd_import(args: argparse.Namespace, content: Path) -> int:
    store = _open_store(content)
    with ContentLock(store.root):
        service = _service(store, _NoRenderer())
        view = import_project(service, args.prototype or default_prototype_dir(), args.project)
    print(f"Imported {view['title']} as a Draft (revision {view['revision']}); nothing published.")
    return 0


class _NoRenderer:
    """Importing renders nothing."""

    def render(
        self, snapshot: dict[str, Any], mode: Mode, preview_slug: str | None = None
    ) -> RenderOutput:  # pragma: no cover - never called
        raise StudioError("the importer does not render")


def cmd_build(args: argparse.Namespace, content: Path) -> int:
    store = _open_store(content)
    with ContentLock(store.root):
        renderer_root = _renderer_root(args.renderer_root)
        builder = SiteBuilder(
            store, _renderer(renderer_root), RendererAssets.from_renderer_root(renderer_root)
        )
        result = run_build(builder, args.out or default_output(store.root))
    print(f"Built {result.exhibits} exhibit(s), {result.pages} page(s) into {result.output}")
    print(result.scan)
    return 0


def cmd_serve_site(args: argparse.Namespace, content: Path) -> int:
    from portfolio_studio.site_server import create_site_server

    store = ContentStore(check_content_dir(content))
    output = args.out or default_output(store.root)
    if not (output / "index.html").is_file():
        raise StudioError(f"no built site in {output}; run 'build' first")
    server = create_site_server(output, LOOPBACK, args.port)
    print(f"Serving {output} at http://{LOOPBACK}:{args.port}/ (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def cmd_backup(args: argparse.Namespace, content: Path) -> int:
    store = ContentStore(check_content_dir(content))
    target = check_outside_code(args.to, "backup bundle")
    if target.exists():
        raise StudioError(f"{target} already exists; choose a new file name")
    target.parent.mkdir(parents=True, exist_ok=True)
    store.git.bundle(target)
    print(f"Wrote and verified {target}. Keep it private: it contains every draft and original.")
    return 0


def cmd_package_pages(args: argparse.Namespace, content: Path) -> int:
    store = _open_store(content)
    with ContentLock(store.root):
        result = package_pages(
            store.root,
            args.site or default_output(store.root),
            code_root() / "scripts" / "scan_output.py",
            mode="production" if args.production else "staging",
        )
    exhibits = ", ".join(f"{e['projectId']} r{e['sourceRevision']}" for e in result.exhibits)
    print(f"Packaged {result.build_id} for Pages ({result.mode}) at {result.artifact}")
    print(f"{result.file_count} files, {result.total_bytes} bytes; exhibits: {exhibits or 'none'}")
    print(f"Registered: manifest sha256 {result.manifest_sha256}")
    print(result.scan)
    if result.mode == "staging":
        print(f"Next: python -m portfolio_studio deploy-pages --artifact {result.artifact}")
    else:
        print("Production packages are never deployed by this tool (owner-approved mechanism).")
    return 0


def _deployer(content: Path, environment: Mapping[str, str] | None) -> Deployer:
    env = dict(os.environ) if environment is None else dict(environment)
    return Deployer(content=content, environment=env)


def cmd_deploy_pages(
    args: argparse.Namespace, content: Path, deployer: Deployer | None = None
) -> int:
    """Dry run unless --execute. Reads only the register and the artifact; staging only."""
    store = ContentStore(check_content_dir(content))
    with ContentLock(store.root):
        active = deployer or _deployer(store.root, None)
        return active.deploy(args.artifact, args.project, args.execute)


def cmd_prune_deployments(
    args: argparse.Namespace, content: Path, deployer: Deployer | None = None
) -> int:
    store = ContentStore(check_content_dir(content))
    active = deployer or _deployer(store.root, None)
    return active.prune(args.project, args.execute)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    configure_logging(logging.WARNING)
    content = getattr(args, "content", None) or default_content_dir()
    handlers = {
        "init": lambda: cmd_init(content),
        "serve": lambda: cmd_serve(args, content),
        "import-prototype": lambda: cmd_import(args, content),
        "build": lambda: cmd_build(args, content),
        "serve-site": lambda: cmd_serve_site(args, content),
        "backup": lambda: cmd_backup(args, content),
        "package-pages": lambda: cmd_package_pages(args, content),
        "deploy-pages": lambda: cmd_deploy_pages(args, content),
        "prune-deployments": lambda: cmd_prune_deployments(args, content),
    }
    try:
        return handlers[args.command]()
    except StudioError as error:
        print(f"error: {error.message}", file=sys.stderr)
        return 1
