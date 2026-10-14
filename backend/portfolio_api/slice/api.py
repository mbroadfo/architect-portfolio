"""Slice HTTP routes (C1 error shape; BR1.1, BR2.1, BR3.1, BR4.1).

Only ``GET /health`` is registered outside the owner-protected router. Every ``/slice`` route
depends on ``require_owner`` at router level, so no handler runs for a refused caller.

Authentication also runs before the body is read (security re-review SL-1). No route declares
a FastAPI body parameter, which FastAPI would read and parse before any dependency runs (so a
stranger's malformed JSON got 422 instead of 401). Instead each body is a dependency,
``owner_body(Model)``, that itself depends on ``require_owner``: the body is read, size-checked
and validated only after the caller is known to be the owner.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

from portfolio_api.auth import OwnerPrincipal, require_owner
from portfolio_api.slice.errors import RevisionRequiredError, ValidationFailedError
from portfolio_api.slice.models import (
    CreateProjectRequest,
    ProjectView,
    PublishRequest,
    UpdateProjectRequest,
)
from portfolio_api.slice.publish import PublishService
from portfolio_api.slice.service import PreviewService, ProjectService
from portfolio_api.slice.snapshot import format_timestamp

IF_MATCH = re.compile(r'^\s*(?:W/)?"?(\d+)"?\s*$')
# The largest request body an owner route reads; the slice's bodies are a few hundred bytes.
MAX_BODY_BYTES = 64 * 1024


def owner_body[BodyModel: BaseModel](
    model: type[BodyModel],
) -> Callable[..., Awaitable[BodyModel]]:
    """A dependency that reads and validates the JSON body only after ``require_owner``."""

    async def read_body(
        request: Request, _owner: Annotated[OwnerPrincipal, Depends(require_owner)]
    ) -> BodyModel:
        declared = request.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > MAX_BODY_BYTES:
            raise ValidationFailedError(f"the request body is larger than {MAX_BODY_BYTES} bytes")
        raw = await request.body()
        if len(raw) > MAX_BODY_BYTES:
            raise ValidationFailedError(f"the request body is larger than {MAX_BODY_BYTES} bytes")
        try:
            return model.model_validate_json(raw)
        except ValidationError as error:
            details = [{**item, "loc": ("body", *item["loc"])} for item in error.errors()]
            raise RequestValidationError(details) from error

    return read_body


@dataclass(frozen=True)
class SliceServices:
    """The collaborators the routes use, built once per app."""

    projects: ProjectService
    preview: PreviewService
    publish: PublishService


def services(request: Request) -> SliceServices:
    built: SliceServices = request.app.state.services
    return built


Services = Annotated[SliceServices, Depends(services)]
IfMatch = Annotated[str | None, Header()]
CreateBody = Annotated[CreateProjectRequest, Depends(owner_body(CreateProjectRequest))]
UpdateBody = Annotated[UpdateProjectRequest, Depends(owner_body(UpdateProjectRequest))]
PublishBody = Annotated[PublishRequest, Depends(owner_body(PublishRequest))]

health_router = APIRouter()
slice_router = APIRouter(prefix="/slice", dependencies=[Depends(require_owner)])


@health_router.get("/health")
def health() -> dict[str, str]:
    """C10: a fixed body; no dependency checks, so it cannot leak state (NFR11.2)."""
    return {"status": "ok"}


def _view(view: ProjectView, response: Response) -> dict[str, Any]:
    response.headers["ETag"] = f'"{view.revision}"'
    return view.model_dump(by_alias=True, mode="json")


def parse_if_match(value: str | None) -> int:
    """The base revision from ``If-Match`` (428 when absent, 422 when malformed)."""
    if value is None or not value.strip():
        raise RevisionRequiredError("an edit needs If-Match with the revision it is based on")
    match = IF_MATCH.match(value)
    if not match:
        raise ValidationFailedError("If-Match must carry the numeric revision")
    return int(match.group(1))


@slice_router.get("/projects")
def list_projects(svc: Services) -> dict[str, Any]:
    views = svc.projects.list()
    return {"projects": [view.model_dump(by_alias=True, mode="json") for view in views]}


@slice_router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(body: CreateBody, response: Response, svc: Services) -> dict[str, Any]:
    """W1: create at revision 1 with a proposed unique slug."""
    project = svc.projects.create(body)
    return _view(svc.projects.view(project), response)


@slice_router.get("/projects/{project_id}")
def get_project(project_id: str, response: Response, svc: Services) -> dict[str, Any]:
    return _view(svc.projects.view(svc.projects.get(project_id)), response)


@slice_router.patch("/projects/{project_id}")
def save_project(
    project_id: str,
    body: UpdateBody,
    response: Response,
    svc: Services,
    if_match: IfMatch = None,
) -> dict[str, Any]:
    """W2: save based on the If-Match revision; 409 STALE_REVISION when it is not current."""
    project = svc.projects.save(project_id, parse_if_match(if_match), body)
    return _view(svc.projects.view(project), response)


@slice_router.get("/projects/{project_id}/preview")
def preview_project(project_id: str, svc: Services) -> dict[str, Any]:
    """W3: the candidate snapshot of the current revision; nothing is written."""
    candidate = svc.preview.candidate(project_id)
    return {
        "revision": candidate.revision,
        "snapshot": candidate.snapshot,
        "imageAddresses": candidate.image_addresses,
    }


@slice_router.post("/projects/{project_id}/publish")
def publish_project(project_id: str, body: PublishBody, svc: Services) -> dict[str, Any]:
    """W4: publish the reviewed revision, or refuse with 409 and write nothing."""
    result = svc.publish.publish(project_id, body.revision)
    view = svc.projects.view(svc.projects.get(project_id))
    return {
        "versionId": result.version_id,
        "sourceRevision": result.source_revision,
        "publishedAt": format_timestamp(result.published_at),
        "status": view.status.value,
    }
