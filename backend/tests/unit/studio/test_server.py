"""The loopback server: Host, Origin and header checks, security headers and the API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from portfolio_studio.build import SiteBuilder, default_output
from portfolio_studio.server import (
    PREVIEW_CSP,
    BindError,
    ServerConfig,
    check_bind_host,
    create_app,
)
from portfolio_studio.service import StudioService

from .conftest import make_image, ready_project

ORIGIN = "http://testserver"
CHANGE = {"Origin": ORIGIN, "X-Studio-Request": "1"}


@pytest.fixture
def ui_dir(tmp_path: Path) -> Path:
    folder = tmp_path / "ui-dist"
    (folder / "ui").mkdir(parents=True)
    (folder / "index.html").write_text("<!doctype html><title>Studio</title>", encoding="utf-8")
    (folder / "ui" / "app.js").write_text("console.log(1)", encoding="utf-8")
    return folder


@pytest.fixture
def client(service: StudioService, builder: SiteBuilder, ui_dir: Path, assets: Any) -> TestClient:
    (assets.static_dir / "site.css").write_bytes(b"body{}")
    config = ServerConfig(
        port=8765,
        ui_dir=ui_dir,
        static_dir=assets.static_dir,
        site_output=default_output(service.store.root),
        site_url="http://127.0.0.1:8766/",
        extra_hosts=("testserver",),
    )
    return TestClient(create_app(service, builder, config))


def test_bind_host_must_be_loopback() -> None:
    assert check_bind_host("127.0.0.1") == "127.0.0.1"
    for host in ("0.0.0.0", "::", "192.168.1.5", "localhost"):  # noqa: S104 - refused hosts
        with pytest.raises(BindError):
            check_bind_host(host)


def test_foreign_host_header_is_refused(client: TestClient) -> None:
    """DNS rebinding: a request for another host name is refused."""
    response = client.get("/api/projects", headers={"Host": "evil.example"})
    assert response.status_code == 421
    assert response.json()["code"] == "HOST_REFUSED"


@pytest.mark.parametrize(
    ("headers", "code"),
    [
        ({}, "ORIGIN_REFUSED"),
        ({"Origin": "http://evil.example", "X-Studio-Request": "1"}, "ORIGIN_REFUSED"),
        ({"Origin": "null", "X-Studio-Request": "1"}, "ORIGIN_REFUSED"),
        ({"Origin": ORIGIN}, "HEADER_REQUIRED"),
        ({**CHANGE, "Sec-Fetch-Site": "cross-site"}, "ORIGIN_REFUSED"),
    ],
)
def test_changes_need_the_studio_origin_and_header(
    client: TestClient, headers: dict[str, str], code: str
) -> None:
    response = client.post("/api/projects", json={"title": "x"}, headers=headers)
    assert response.status_code == 403
    assert response.json()["code"] == code
    assert client.get("/api/projects").json() == {"projects": []}


def test_oversized_request_is_refused(client: TestClient) -> None:
    response = client.post(
        "/api/projects", headers={**CHANGE, "Content-Length": str(50 * 1024 * 1024)}
    )
    assert response.status_code == 413


def test_security_headers(client: TestClient) -> None:
    response = client.get("/api/projects")
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
    page = client.get("/")
    assert page.status_code == 200 and "Studio" in page.text
    assert client.get("/ui/app.js").status_code == 200
    assert client.get("/ui/../index.html").status_code == 404
    assert client.get("/nothing-here").status_code == 404


def test_full_flow_through_the_api(client: TestClient, service: StudioService) -> None:
    """Create, upload, save, preview, review, publish, build, take down — over HTTP."""
    created = client.post("/api/projects", json={"title": "STARS"}, headers=CHANGE)
    assert created.status_code == 201
    project = created.json()
    upload = client.post(
        "/api/projects/stars/images",
        files={"file": ("photo.jpg", make_image(gps=True), "image/jpeg")},
        data={"revision": str(project["revision"])},
        headers=CHANGE,
    )
    assert upload.status_code == 201, upload.text
    view = upload.json()
    image = view["images"][0]
    assert "originalFile" not in image and image["lead"] is True
    media = client.get(f"/media/{image['assetRef']}/w480.jpg")
    assert media.status_code == 200 and media.headers["content-type"] == "image/jpeg"
    assert b"Exif" not in media.content
    body = {
        "revision": view["revision"],
        "title": "STARS",
        "slug": "stars",
        "images": [{"assetRef": image["assetRef"], "altText": "Stars", "lead": True}],
    }
    saved = client.put("/api/projects/stars", json=body, headers=CHANGE)
    assert saved.status_code == 200 and saved.json()["blockers"] == []
    stale = client.put("/api/projects/stars", json=body, headers=CHANGE)
    assert stale.status_code == 409 and stale.json()["code"] == "STALE_REVISION"
    preview = client.get("/preview/stars/exhibit")
    assert preview.status_code == 200 and "Preview — not public" in preview.text
    assert preview.headers["content-security-policy"] == PREVIEW_CSP
    assert preview.headers["x-frame-options"] == "SAMEORIGIN"
    assert client.get("/preview/stars/home").status_code == 200
    review = client.post("/api/projects/stars/review", headers=CHANGE).json()
    published = client.post(
        "/api/projects/stars/publish",
        json={"revision": review["revision"], "reviewId": review["reviewId"]},
        headers=CHANGE,
    )
    assert published.status_code == 200 and published.json()["status"] == "Published"
    built = client.post("/api/site/build", headers=CHANGE)
    assert built.status_code == 200, built.text
    assert built.json()["exhibits"] == 1
    assert client.get("/api/site").json()["url"] == "http://127.0.0.1:8766/"
    assert client.get("/api/featured").status_code == 200
    activity = client.get("/api/activity").json()["entries"]
    assert activity[0]["action"] == "Publish STARS (revision 3)"
    down = client.post(
        "/api/projects/stars/take-down", json={"confirmTitle": "STARS"}, headers=CHANGE
    )
    assert down.json()["status"] == "Taken down"
    assert client.put("/api/featured", json={"order": []}, headers=CHANGE).status_code == 200


def test_errors_use_the_studio_error_shape(client: TestClient, service: StudioService) -> None:
    assert client.get("/api/projects/missing").status_code == 404
    assert client.get("/api/projects/..%2F..%2Fetc").status_code == 404
    invalid = client.post("/api/projects", json={"title": ""}, headers=CHANGE)
    assert invalid.status_code == 422 and invalid.json()["code"] == "VALIDATION_FAILED"
    assert client.get("/media/ast_aaaaaaaaaaaaaaaaaaaa/w480.jpg").status_code == 404
    assert client.get("/media/not-a-ref/w480.jpg").status_code == 404
    ready_project(service)
    assert client.get("/preview/stars/other").status_code == 404
    blocked = client.post(
        "/api/projects/stars/images",
        files={"file": ("x.jpg", b"not an image", "image/jpeg")},
        data={"revision": str(service.get("stars")["revision"])},
        headers=CHANGE,
    )
    assert blocked.status_code == 422 and blocked.json()["code"] == "IMAGE_REJECTED"
    missing = client.post("/api/projects/stars/images", data={"revision": "x"}, headers=CHANGE)
    assert missing.status_code == 422


def test_renderer_assets_are_served_only_with_a_matching_hash(client: TestClient) -> None:
    import hashlib

    digest = hashlib.sha256(b"body{}").hexdigest()[:10]
    assert client.get(f"/assets/site.{digest}.css").status_code == 200
    assert client.get("/assets/site.0000000000.css").status_code == 404
    assert client.get("/assets/other.0000000000.css").status_code == 404
    assert client.get("/assets/evil.txt").status_code == 404


def test_missing_ui_explains_how_to_build_it(
    service: StudioService, builder: SiteBuilder, tmp_path: Path
) -> None:
    config = ServerConfig(
        port=1,
        ui_dir=tmp_path / "nothing",
        static_dir=tmp_path,
        site_output=tmp_path / "out",
        extra_hosts=("testserver",),
    )
    page = TestClient(create_app(service, builder, config)).get("/")
    assert "not built" in page.text
