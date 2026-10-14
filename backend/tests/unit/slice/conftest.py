"""Shared harness for the slice unit tests: in-memory repositories, a fixed renderer, a
temporary site folder and a test signing key. Nothing touches MongoDB, Node or a network."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from portfolio_api.auth import JwksClient, TokenVerifier
from portfolio_api.settings import Settings
from portfolio_api.slice.api import SliceServices
from portfolio_api.slice.app import AppComponents, create_app
from portfolio_api.slice.publish import PublishService
from portfolio_api.slice.service import PreviewService, ProjectService
from portfolio_api.slice.site_store import LinkOps, SiteStore, SymlinkOps
from portfolio_api.slice.snapshot import FixtureImage, SiteConfig

from tests.unit.slice import tokens
from tests.unit.slice.fakes import (
    FixedRenderer,
    InMemoryProjectRepository,
    InMemoryPublicationRepository,
    PointerFileOps,
)

ASSET_REF = "ast_PlaceholderAsset0001"
CSS = b"body{margin:0}\n"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00placeholder"
WEBP = b"RIFF\x10\x00\x00\x00WEBPVP8 placeholder"


def _symlinks_supported() -> bool:
    with tempfile.TemporaryDirectory() as directory:
        try:
            os.symlink("target", Path(directory) / "link", target_is_directory=True)
        except OSError:
            return False
    return True


SYMLINKS = _symlinks_supported()
needs_symlinks = pytest.mark.skipif(
    not SYMLINKS, reason="this host cannot create symbolic links (Windows without Developer Mode)"
)


class Clock:
    """A controllable clock: each call advances one second."""

    def __init__(self) -> None:
        self.now = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


class Ids:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.count = 0

    def __call__(self) -> str:
        self.count += 1
        return f"{self.prefix}{self.count:04d}"


@pytest.fixture
def link_ops() -> LinkOps:
    """Real symbolic links wherever the host allows them; the pointer-file fake otherwise."""
    return SymlinkOps() if SYMLINKS else PointerFileOps()


@pytest.fixture
def fixture_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "fixtures"
    (directory / ASSET_REF).mkdir(parents=True)
    (directory / ASSET_REF / "w480.jpg").write_bytes(JPEG)
    (directory / ASSET_REF / "w480.webp").write_bytes(WEBP)
    manifest = {
        "assetRef": ASSET_REF,
        "altText": "Placeholder illustration",
        "width": 400,
        "height": 300,
    }
    (directory / "fixture.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "static"
    directory.mkdir()
    (directory / "site.css").write_bytes(CSS)
    return directory


@pytest.fixture
def site(tmp_path: Path, fixture_dir: Path, static_dir: Path, link_ops: LinkOps) -> SiteStore:
    return SiteStore(tmp_path / "site", fixture_dir, static_dir, links=link_ops)


@dataclass
class Harness:
    """The app plus direct handles on its collaborators."""

    app: FastAPI
    client: TestClient
    projects: InMemoryProjectRepository
    publications: InMemoryPublicationRepository
    renderer: FixedRenderer
    site: SiteStore
    publish: PublishService
    signing_key: tokens.SigningKey
    handler_calls: list[str] = field(default_factory=list)

    def token(self, subject: str = tokens.OWNER) -> str:
        return tokens.sign(self.signing_key, tokens.claims(sub=subject))

    def headers(self, subject: str = tokens.OWNER, **extra: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token(subject)}", **extra}

    def create(self, title: str = "Placeholder project", summary: str = "") -> dict[str, object]:
        response = self.client.post(
            "/slice/projects", json={"title": title, "summary": summary}, headers=self.headers()
        )
        assert response.status_code == 201, response.text
        body: dict[str, object] = response.json()
        return body

    def save(self, project_id: object, revision: object, **changes: str) -> httpx.Response:
        return self.client.patch(
            f"/slice/projects/{project_id}",
            json=changes,
            headers=self.headers(**{"If-Match": f'"{revision}"'}),
        )

    def publish_revision(self, project_id: object, revision: object) -> httpx.Response:
        return self.client.post(
            f"/slice/projects/{project_id}/publish",
            json={"revision": revision},
            headers=self.headers(),
        )


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        auth_issuer=tokens.ISSUER,
        auth_audience=tokens.AUDIENCE,
        owner_subject=tokens.OWNER,
        jwks_url=f"{tokens.ISSUER}/.well-known/jwks.json",
        mongo_uri="mongodb://unused.test.example",
        mongo_db="unused",
        site_dir=tmp_path / "site",
        fixture_dir=tmp_path / "fixtures",
        renderer_command=("node", "cli.cjs"),
        renderer_assets_dir=tmp_path / "static",
        site_owner_name="Placeholder Owner",
        site_github_url="https://github.com/example",
        # SL-3: the test client's Host; outside APP_ENV=local the list must be explicit.
        allowed_hosts=("testserver", "localhost"),
    )


@pytest.fixture
def harness(tmp_path: Path, site: SiteStore, fixture_dir: Path) -> Iterator[Harness]:
    projects = InMemoryProjectRepository()
    publications = InMemoryPublicationRepository(projects)
    renderer = FixedRenderer(hashlib.sha256(CSS).hexdigest()[:10])
    fixture = FixtureImage.load(fixture_dir)
    site_config = SiteConfig("Placeholder Owner", "https://github.com/example")
    clock = Clock()
    project_service = ProjectService(projects, publications, clock=clock, new_id=Ids("p"))
    publish = PublishService(
        projects, publications, renderer, site, site_config, fixture, clock=clock, new_id=Ids("v")
    )
    signing_key = tokens.ec_key()
    jwks = tokens.jwks(signing_key)
    verifier = TokenVerifier(
        JwksClient(f"{tokens.ISSUER}/jwks", fetch=lambda _url: jwks),
        tokens.ISSUER,
        tokens.AUDIENCE,
        tokens.OWNER,
    )
    components = AppComponents(
        services=SliceServices(
            project_service,
            PreviewService(project_service, site_config, fixture, clock=clock),
            publish,
        ),
        token_verifier=verifier,
        startup=[publish.reconcile],
    )
    app = create_app(make_settings(tmp_path), components)
    with TestClient(app) as client:
        yield Harness(app, client, projects, publications, renderer, site, publish, signing_key)
