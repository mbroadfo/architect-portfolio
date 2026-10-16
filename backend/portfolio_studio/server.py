"""The Studio's local server: the Studio page and its API on one loopback origin (ADR-013).

There is no sign-in: the Studio is reachable only from this machine. Defences for a loopback
administration server:

- it binds 127.0.0.1 only (``check_bind_host``);
- the Host header must be ``127.0.0.1:<port>`` or ``localhost:<port>`` (DNS rebinding);
- any request whose ``Sec-Fetch-Site`` is present and is neither ``same-origin`` nor ``none``
  (direct navigation) is refused on every route, so another site cannot even start a preview;
- every request that changes data must carry the Studio's own Origin, the custom header
  ``X-Studio-Request: 1`` (which a cross-site form or image cannot send without a CORS
  preflight this server never grants) and, when the browser sends it,
  ``Sec-Fetch-Site: same-origin``;
- strict security headers: CSP ``default-src 'self'`` with ``frame-ancestors 'none'``, except
  the preview pages, which only the Studio itself may frame and which are sandboxed;
- request logs carry the method, route template, status and duration, never content.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from portfolio_api.slice.observability import JsonFormatter
from portfolio_api.slice.site_store import STATIC_ASSET
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from portfolio_studio.build import SiteBuilder, run_build
from portfolio_studio.errors import (
    NotFoundError,
    StudioError,
    ValidationFailedError,
)
from portfolio_studio.images import MAX_UPLOAD_BYTES, read_limited
from portfolio_studio.location import code_root
from portfolio_studio.model import (
    CreateRequest,
    FeaturedOrderRequest,
    PublishRequest,
    SaveRequest,
    TakeDownRequest,
)
from portfolio_studio.pages import package_pages
from portfolio_studio.service import StudioService
from portfolio_studio.store import check_asset_ref, check_id

LOOPBACK = "127.0.0.1"
MUTATING = frozenset({"POST", "PUT", "PATCH", "DELETE"})
STUDIO_HEADER = "X-Studio-Request"
MAX_BODY_BYTES = MAX_UPLOAD_BYTES + 256 * 1024
UI_CSP = (
    "default-src 'self'; img-src 'self'; style-src 'self'; script-src 'self'; "
    "font-src 'self'; connect-src 'self'; frame-src 'self'; object-src 'none'; "
    "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)
# Preview pages: no scripts, no forms, no top navigation; framed only by the Studio itself.
PREVIEW_CSP = (
    "default-src 'none'; img-src 'self'; style-src 'self'; font-src 'self'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'self'; sandbox allow-same-origin"
)
PREVIEW_PAGES = {"exhibit", "home", "work"}
MISSING_UI = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Studio</title></head><body><main><h1>The Studio page is not built</h1>
<p>Run <code>npm --prefix web/local-studio ci</code> and
<code>npm --prefix web/local-studio run build</code>, then reload.</p></main></body></html>"""

logger = logging.getLogger("portfolio_studio.requests")


class BindError(StudioError):
    code = "BIND"


def check_bind_host(host: str) -> str:
    """The Studio listens on the loopback address only."""
    if host != LOOPBACK:
        raise BindError(f"the Studio binds {LOOPBACK} only (refused {host!r})")
    return host


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger("portfolio_studio")
    if not any(getattr(h, "_studio_json", False) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler._studio_json = True  # type: ignore[attr-defined]
        root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


@dataclass(frozen=True)
class ServerConfig:
    port: int
    ui_dir: Path
    static_dir: Path
    site_output: Path
    site_url: str | None = None
    scanner: Path | None = None
    extra_hosts: tuple[str, ...] = ()

    @property
    def allowed_hosts(self) -> frozenset[str]:
        return frozenset({f"{LOOPBACK}:{self.port}", f"localhost:{self.port}", *self.extra_hosts})

    @property
    def allowed_origins(self) -> frozenset[str]:
        return frozenset(f"http://{host}" for host in self.allowed_hosts)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"code": code, "message": message}, status_code=status)


def _refusal(request: Request, config: ServerConfig) -> JSONResponse | None:
    """Host, Origin and custom-header checks; None when the request may proceed."""
    if request.headers.get("host", "") not in config.allowed_hosts:
        return _error(421, "HOST_REFUSED", "this server answers on its loopback address only")
    # LS-3: a page on another site may not make the Studio do anything, not even a preview
    # (which runs the renderer and may call GitHub). Direct navigation sends "none".
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site is not None and fetch_site not in ("same-origin", "none"):
        return _error(403, "CROSS_SITE_REFUSED", "requests from other sites are refused")
    length = request.headers.get("content-length")
    if length is not None and (not length.isdigit() or int(length) > MAX_BODY_BYTES):
        return _error(413, "TOO_LARGE", "the request is too large")
    if request.method in MUTATING:
        if request.headers.get("origin", "") not in config.allowed_origins:
            return _error(403, "ORIGIN_REFUSED", "changes are accepted only from the Studio page")
        if request.headers.get(STUDIO_HEADER) != "1":
            return _error(403, "HEADER_REQUIRED", "changes need the Studio's request header")
        if fetch_site == "none":
            return _error(403, "ORIGIN_REFUSED", "changes are accepted only from the Studio page")
        if length is None and request.headers.get("transfer-encoding"):
            return _error(411, "LENGTH_REQUIRED", "send a Content-Length")
    return None


def _security_headers(response: Response, path: str) -> None:
    preview = path.startswith("/preview/")
    response.headers["Content-Security-Policy"] = PREVIEW_CSP if preview else UI_CSP
    response.headers["X-Frame-Options"] = "SAMEORIGIN" if preview else "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    if not path.startswith("/ui/"):
        response.headers["Cache-Control"] = "no-store"


def create_app(service: StudioService, builder: SiteBuilder, config: ServerConfig) -> FastAPI:
    """The Studio application; every route below sits behind the checks in ``guard``."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def guard(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = time.perf_counter()
        response = _refusal(request, config) or await call_next(request)
        _security_headers(response, request.url.path)
        route = request.scope.get("route")
        logger.info(
            "request",
            extra={
                "fields": {
                    "method": request.method,
                    "route": getattr(route, "path", "unmatched"),
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            },
        )
        return response

    @app.exception_handler(StudioError)
    async def studio_error(_: Request, error: StudioError) -> JSONResponse:
        if error.status_code >= 500:
            logger.error("operation failed", extra={"fields": {"code": error.code}})
        return _error(error.status_code, error.code, error.message)

    @app.exception_handler(RequestValidationError)
    async def invalid(_: Request, error: RequestValidationError) -> JSONResponse:
        details = "; ".join(
            f"{'.'.join(str(p) for p in e.get('loc', ())[1:])}: {e.get('msg', 'invalid')}"
            for e in error.errors()
        )
        return _error(422, "VALIDATION_FAILED", details or "the request is invalid")

    _api_routes(app, service, builder, config)
    _page_routes(app, service, config)
    return app


def _api_routes(
    app: FastAPI, service: StudioService, builder: SiteBuilder, config: ServerConfig
) -> None:
    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/projects")
    def list_projects() -> dict[str, Any]:
        return {"projects": service.list_projects()}

    @app.post("/api/projects", status_code=201)
    def create(body: CreateRequest) -> dict[str, Any]:
        return service.create(body)

    @app.get("/api/projects/{project_id}")
    def get(project_id: str) -> dict[str, Any]:
        return service.get(check_id(project_id))

    @app.put("/api/projects/{project_id}")
    def save(project_id: str, body: SaveRequest) -> dict[str, Any]:
        return service.save(check_id(project_id), body)

    @app.post("/api/projects/{project_id}/images", status_code=201)
    async def upload(project_id: str, request: Request) -> dict[str, Any]:
        check_id(project_id)
        form = await request.form(max_files=1, max_fields=2, max_part_size=1024)
        try:
            file, revision = form.get("file"), form.get("revision")
            if not isinstance(file, UploadFile) or not isinstance(revision, str):
                raise ValidationFailedError("send one image file and the revision")
            if not revision.isdigit():
                raise ValidationFailedError("the revision must be a number")
            data = await run_in_threadpool(read_limited, file.file)
        finally:
            await form.close()
        return await run_in_threadpool(service.upload_image, project_id, int(revision), data)

    @app.post("/api/projects/{project_id}/review")
    def review(project_id: str) -> dict[str, Any]:
        return service.prepare_review(check_id(project_id))

    @app.post("/api/projects/{project_id}/publish")
    def publish(project_id: str, body: PublishRequest) -> dict[str, Any]:
        return service.publish(check_id(project_id), body)

    @app.post("/api/projects/{project_id}/take-down")
    def take_down(project_id: str, body: TakeDownRequest) -> dict[str, Any]:
        return service.take_down(check_id(project_id), body.confirmTitle)

    @app.get("/api/featured")
    def featured() -> dict[str, Any]:
        return service.featured()

    @app.put("/api/featured")
    def update_featured(body: FeaturedOrderRequest) -> dict[str, Any]:
        return service.update_featured_order(body)

    @app.get("/api/activity")
    def activity() -> dict[str, Any]:
        return {"entries": service.activity()}

    @app.get("/api/site")
    def site() -> dict[str, Any]:
        return {"output": str(config.site_output), "url": config.site_url}

    @app.post("/api/site/package")
    def package() -> dict[str, Any]:
        """Package the last scanned build for Pages, staging only (noindex)."""
        scanner = config.scanner or code_root() / "scripts" / "scan_output.py"
        with service.lock:
            result = package_pages(service.store.root, config.site_output, scanner)
        return {
            "artifact": str(result.artifact),
            "mode": result.mode,
            "files": result.file_count,
            "bytes": result.total_bytes,
            "buildId": result.build_id,
            "exhibits": result.exhibits,
            "scan": result.scan,
            "manifestSha256": result.manifest_sha256,
            "dryRun": f"python -m portfolio_studio deploy-pages --artifact {result.artifact}",
        }

    @app.post("/api/site/build")
    def build() -> dict[str, Any]:
        with service.lock:
            result = run_build(builder, config.site_output)
        return {
            "output": str(result.output),
            "pages": result.pages,
            "exhibits": result.exhibits,
            "files": result.files,
            "scan": result.scan,
            "url": config.site_url,
        }


def _page_routes(app: FastAPI, service: StudioService, config: ServerConfig) -> None:
    @app.get("/preview/{project_id}/{page}")
    def preview(project_id: str, page: str) -> HTMLResponse:
        if page not in PREVIEW_PAGES:
            raise NotFoundError("no such preview page")
        draft = service.store.draft(check_id(project_id))
        pages = service.preview(project_id)
        path = "/" if page == "home" else ("/work/" if page == "work" else f"/work/{draft.slug}")
        return HTMLResponse(pages[path])

    @app.get("/media/{asset_ref}/{name}")
    def media(asset_ref: str, name: str) -> FileResponse:
        path = service.store.derivative_file(check_asset_ref(asset_ref), name)
        if path is None:
            raise NotFoundError("no such image")
        media_type = "image/webp" if name.endswith(".webp") else "image/jpeg"
        return FileResponse(path, media_type=media_type)

    @app.get("/assets/{name}")
    def renderer_asset(name: str) -> Response:
        return _renderer_asset(config.static_dir, name)

    @app.get("/ui/{name:path}")
    def ui_asset(name: str) -> FileResponse:
        return _ui_file(config.ui_dir, f"ui/{name}")

    @app.get("/")
    def index() -> Response:
        page = config.ui_dir / "index.html"
        if not page.is_file():
            return HTMLResponse(MISSING_UI)
        return FileResponse(page, media_type="text/html; charset=utf-8")

    @app.get("/{rest:path}")
    def not_found(rest: str) -> Response:
        return _error(404, "NOT_FOUND", "not found")


def _ui_file(ui_dir: Path, relative: str) -> FileResponse:
    root = ui_dir.resolve()
    path = (root / relative).resolve()
    if not path.is_file() or root not in path.parents:
        raise NotFoundError("not found")
    return FileResponse(path)


def _renderer_asset(static_dir: Path, name: str) -> Response:
    """The renderer's hashed static assets for the preview pages, checked against the hash."""
    match = STATIC_ASSET.match(f"/assets/{name}")
    if not match:
        raise NotFoundError("not found")
    source = static_dir / f"{match['stem']}.{match['ext']}"
    if not source.is_file():
        raise NotFoundError("not found")
    data = source.read_bytes()
    if not hashlib.sha256(data).hexdigest().startswith(match["hash"]):
        raise NotFoundError("not found")
    types = {"css": "text/css", "js": "text/javascript", "woff2": "font/woff2"}
    return Response(data, media_type=types[match["ext"]])
