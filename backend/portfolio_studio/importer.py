"""Seed a Draft from the approved prototype's draft copy and live captures.

``import-prototype --project stars|baduk`` reads ``prototype/data.js`` (evaluated by Node in
an isolated context with no access to anything but its own text) and the live captures under
``prototype/assets/live/``. The images go through the normal upload pipeline; the copy, alt
text, captions, category and access fields go through the normal save. Nothing is published:
the project is a Draft until Michael reviews it and confirms Publish himself.

Only STARS and Baduk can be imported. Monopoly Arena and Risk are never imported (rights
review outstanding; Risk's repository is private and its live URL is withheld, FR10.6,
FR10.7). The prototype's simulated publication approvals are ignored, and the live URL is
left neither included nor authorized: Michael chooses that at Publish.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from portfolio_studio.errors import StudioError, ValidationFailedError
from portfolio_studio.location import code_root, code_roots
from portfolio_studio.model import CreateRequest, SaveRequest
from portfolio_studio.service import StudioService

IMPORTABLE = ("stars", "baduk")
PROTOTYPE_RELATIVE = (
    "aidlc/spaces/default/intents/261010-architect-portfolio/inception/refined-mockups/prototype"
)
NARRATIVE_KEYS = {
    "inspiration": "inspiration",
    "challenges": "designChallenges",
    "decisions": "architecturalDecisions",
    "implementation": "implementation",
    "outcomes": "outcomes",
    "lessons": "lessonsLearned",
}
LIVE_URLS = {
    "stars": "https://stars.xaminisalamini.com",
    "baduk": "https://baduk.xaminisalamini.com",
}
READ_DATA_JS = """
const fs = require("fs");
const vm = require("vm");
const context = { window: {} };
vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"), context, { timeout: 2000 });
const project = context.window.PORTFOLIO.find(process.argv[2]);
process.stdout.write(JSON.stringify(project || null));
"""


@dataclass(frozen=True)
class PrototypeImage:
    file: Path
    alt: str
    caption: str
    lead: bool


def default_prototype_dir() -> Path:
    """The prototype in this work tree, else in the main checkout or another work tree."""
    others = sorted(code_roots() - {code_root()}, key=lambda p: (len(p.parts), str(p)))
    candidates = [code_root(), *others]
    for root in candidates:
        if (root / PROTOTYPE_RELATIVE / "data.js").is_file():
            return root / PROTOTYPE_RELATIVE
    return code_root() / PROTOTYPE_RELATIVE


def read_prototype_project(prototype_dir: Path, slug: str, node: str = "node") -> dict[str, Any]:
    """Evaluate ``data.js`` in an isolated Node context and return one project."""
    if slug not in IMPORTABLE:
        raise ValidationFailedError(f"only {', '.join(IMPORTABLE)} can be imported")
    data_js = prototype_dir / "data.js"
    if not data_js.is_file():
        raise ValidationFailedError(f"no prototype data at {data_js}")
    try:
        completed = subprocess.run(  # noqa: S603 - fixed script, argument list, no shell
            [node, "-e", READ_DATA_JS, str(data_js), slug],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise StudioError(f"node could not read the prototype: {error}") from error
    if completed.returncode != 0:
        raise StudioError(f"node could not read the prototype: {completed.stderr.strip()[:200]}")
    project = json.loads(completed.stdout)
    if not isinstance(project, dict) or project.get("slug") != slug:
        raise ValidationFailedError(f"the prototype has no project '{slug}'")
    return project


def prototype_images(prototype_dir: Path, project: dict[str, Any]) -> list[PrototypeImage]:
    """The live captures: the lead first, then the rest of the gallery (no draft art)."""
    lead = project.get("lead") or {}
    captions = {g["src"]: g.get("caption", "") for g in project.get("gallery", [])}
    images: list[PrototypeImage] = []
    seen: set[str] = set()
    entries = [{**lead, "isLead": True}, *project.get("gallery", [])]
    for entry in entries:
        src = str(entry.get("src", ""))
        if src in seen or entry.get("kind") != "live" or not src.startswith("assets/live/"):
            continue
        seen.add(src)
        images.append(
            PrototypeImage(
                file=prototype_dir / src,
                alt=str(entry.get("alt", "")),
                caption=str(captions.get(src, entry.get("caption", ""))),
                lead=bool(entry.get("isLead")),
            )
        )
    return images


def import_project(service: StudioService, prototype_dir: Path, slug: str) -> dict[str, Any]:
    """Create the Draft, upload its images through the pipeline, then save its fields."""
    project = read_prototype_project(prototype_dir, slug)
    if slug in service.store.project_ids():
        raise ValidationFailedError(f"a project '{slug}' already exists; nothing was imported")
    created = service.create(CreateRequest(title=str(project["title"])))
    project_id = str(created["id"])
    revision = int(created["revision"])
    images = prototype_images(prototype_dir, project)
    for image in images:
        view = service.upload_image(project_id, revision, image.file.read_bytes())
        revision = int(view["revision"])
    draft = service.store.draft(project_id)
    edits = [
        {
            "assetRef": stored.assetRef,
            "altText": source.alt,
            "caption": source.caption,
            "lead": source.lead,
        }
        for stored, source in zip(draft.images, images, strict=True)
    ]
    narrative = project.get("narrative", {})
    access = project.get("access", {})
    repositories = [{"url": r["url"]} for r in project.get("repos", []) if r.get("url")]
    request = SaveRequest.model_validate(
        {
            "revision": revision,
            "title": project["title"],
            "slug": slug,
            "summary": project.get("summary", ""),
            "sections": {
                target: str(narrative.get(source, "")) for source, target in NARRATIVE_KEYS.items()
            },
            "primaryCategory": project.get("category"),
            "featured": bool(project.get("featured")),
            "links": [],
            "liveUrl": LIVE_URLS[slug],
            "liveUrlIncluded": False,
            "liveUrlAuthorized": False,
            "access": access.get("requirement", "open"),
            "phone": access.get("phone", "unknown"),
            "repositories": repositories,
            "rightsReviewRequired": False,
            "rightsReviewComplete": False,
            "images": edits,
        }
    )
    return service.save(project_id, request)
