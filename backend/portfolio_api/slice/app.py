"""The slice API application (Step 17).

Run locally (inside the Compose stack) with::

    uvicorn --factory portfolio_api.slice.app:create_app --host 0.0.0.0 --port 8000

``create_app()`` reads the settings from the environment and refuses to start with a
local-class issuer outside ``APP_ENV=local`` (BR1.3). FastAPI's ``/docs``, ``/redoc`` and
``/openapi.json`` are disabled, so ``/health`` is the only unauthenticated route.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from portfolio_api.auth import AuthError, JwksClient, TokenVerifier
from portfolio_api.settings import ConfigurationError, Settings, load_settings
from portfolio_api.slice.api import SliceServices, health_router, slice_router
from portfolio_api.slice.errors import SliceError
from portfolio_api.slice.mongo import (
    MongoProjectRepository,
    MongoPublicationRepository,
    connect,
    ensure_indexes,
)
from portfolio_api.slice.observability import (
    configure_logging,
    request_id_for,
    request_logging_middleware,
)
from portfolio_api.slice.publish import PublishService
from portfolio_api.slice.renderer import SubprocessRenderer
from portfolio_api.slice.service import PreviewService, ProjectService
from portfolio_api.slice.site_store import SiteStore
from portfolio_api.slice.snapshot import FixtureImage, SiteConfig

logger = logging.getLogger("portfolio_api.slice.app")


@dataclass
class AppComponents:
    """Everything the app needs; tests build it with in-memory doubles."""

    services: SliceServices
    token_verifier: TokenVerifier
    startup: list[Callable[[], object]] = field(default_factory=list)


def build_components(settings: Settings) -> AppComponents:
    """Wire the real collaborators: MongoDB, the issuer's keys, the renderer, the site folder."""
    client = connect(settings.mongo_uri)
    database = client[settings.mongo_db]
    projects = MongoProjectRepository(database)
    publications = MongoPublicationRepository(client, database)
    fixture = FixtureImage.load(settings.fixture_dir)
    site_config = SiteConfig(settings.site_owner_name, settings.site_github_url)
    site = SiteStore(settings.site_dir, settings.fixture_dir, settings.renderer_assets_dir)
    project_service = ProjectService(projects, publications)
    publish = PublishService(
        projects,
        publications,
        SubprocessRenderer(settings.renderer_command),
        site,
        site_config,
        fixture,
    )
    verifier = TokenVerifier(
        JwksClient(settings.jwks_url),
        settings.auth_issuer,
        settings.auth_audience,
        settings.owner_subject,
    )
    return AppComponents(
        services=SliceServices(
            project_service, PreviewService(project_service, site_config, fixture), publish
        ),
        token_verifier=verifier,
        startup=[lambda: ensure_indexes(database), publish.reconcile],
    )


def _error(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    body = {"code": code, "message": message, "requestId": request_id_for(request)}
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(body, status_code=status_code, headers=headers)


def _validation_message(error: RequestValidationError) -> str:
    parts = []
    for item in error.errors():
        location = ".".join(str(p) for p in item.get("loc", ()) if p != "body")
        parts.append(
            f"{location}: {item.get('msg', 'invalid')}" if location else str(item.get("msg"))
        )
    return "; ".join(parts) or "the request is invalid"


def install_error_handlers(app: FastAPI) -> None:
    """Every error body is the C1 ``Error`` shape with a closed code and the request id."""

    @app.exception_handler(AuthError)
    async def auth_error(request: Request, error: AuthError) -> JSONResponse:
        return _error(request, error.status_code, error.code, error.message)

    @app.exception_handler(SliceError)
    async def slice_error(request: Request, error: SliceError) -> JSONResponse:
        if error.status_code >= 500:
            logger.error("request failed", extra={"fields": {"error": type(error).__name__}})
        return _error(request, error.status_code, error.code, error.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        return _error(request, 422, "VALIDATION_FAILED", _validation_message(error))

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.exception(
            "unexpected error", extra={"fields": {"request_id": request_id_for(request)}}
        )
        return _error(request, 500, "INTERNAL", "Something went wrong; nothing was published.")


def create_app(
    settings: Settings | None = None, components: AppComponents | None = None
) -> FastAPI:
    """Build the API; raise ConfigurationError (refusing to start) on unsafe settings."""
    resolved = settings if settings is not None else load_settings()
    if not resolved.allowed_hosts or "*" in resolved.allowed_hosts:
        raise ConfigurationError("the API needs an explicit Host allow-list (ALLOWED_HOSTS)")
    configure_logging()
    parts = components if components is not None else build_components(resolved)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        for step in parts.startup:
            step()
        yield

    app = FastAPI(
        title="Architect Portfolio slice API",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.services = parts.services
    app.state.token_verifier = parts.token_verifier
    app.middleware("http")(request_logging_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[resolved.cors_origin],
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "If-Match", "X-Request-Id"],
        expose_headers=["ETag", "X-Request-Id"],
        allow_credentials=False,
    )
    # SL-3: added last, so it runs first. A foreign Host (DNS rebinding) gets 400 before
    # logging, CORS or any route.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(resolved.allowed_hosts))
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(slice_router)
    return app
