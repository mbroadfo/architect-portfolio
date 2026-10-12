"""API tests (Step 18; AC0.1, AC0.3 to AC0.9; BR1.1, BR2.1, BR2.2, BR3.1, BR3.3, BR3.4, BR4.1).

Every test runs against the real app with in-memory repositories, a fixed renderer and a
temporary site folder (fakes per the unit-test instructions).
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi.routing import iter_route_contexts
from portfolio_api.auth import require_owner
from portfolio_api.settings import ConfigurationError, load_settings
from portfolio_api.slice.app import create_app
from portfolio_api.slice.site_store import EMPTY_RELEASE, SiteStore

from tests.unit.slice import tokens
from tests.unit.slice.conftest import Harness

# --- AC0.1: owner-only routes, no handler runs on a rejected call ---------------------------


def _dependency_calls(dependant: Any) -> set[Any]:
    calls = set()
    for dependency in dependant.dependencies:
        calls.add(dependency.call)
        calls |= _dependency_calls(dependency)
    return calls


def test_ac0_1_only_health_is_unauthenticated(harness: Harness) -> None:
    """AC0.1: every served route except /health depends on require_owner."""
    unprotected = []
    for context in iter_route_contexts(harness.app.routes):
        dependant = getattr(context, "dependant", None)
        calls = _dependency_calls(dependant) if dependant is not None else set()
        if require_owner not in calls:
            unprotected.append(context.path)
    assert unprotected == ["/health"]
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert harness.client.get(path).status_code == 404


@pytest.fixture
def spies(harness: Harness, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace every service entry point with a spy that records a call."""
    calls: list[str] = []
    services = harness.app.state.services
    for name, target, method in [
        ("list", services.projects, "list"),
        ("create", services.projects, "create"),
        ("get", services.projects, "get"),
        ("save", services.projects, "save"),
        ("preview", services.preview, "candidate"),
        ("publish", services.publish, "publish"),
    ]:
        monkeypatch.setattr(target, method, lambda *a, _n=name, **k: calls.append(_n))
    return calls


REQUESTS: list[tuple[str, str, dict[str, Any] | None]] = [
    ("GET", "/slice/projects", None),
    ("POST", "/slice/projects", {"title": "x"}),
    ("GET", "/slice/projects/p1", None),
    ("PATCH", "/slice/projects/p1", {"title": "x"}),
    ("GET", "/slice/projects/p1/preview", None),
    ("POST", "/slice/projects/p1/publish", {"revision": 1}),
]


def _bad_tokens(harness: Harness) -> list[tuple[dict[str, str], int]]:
    forger = tokens.ec_key(kid=harness.signing_key.kid)
    return [
        ({}, 401),
        ({"Authorization": "Basic abc"}, 401),
        ({"Authorization": f"Bearer {tokens.unsigned(harness.signing_key.kid)}"}, 401),
        ({"Authorization": f"Bearer {tokens.hs256(harness.signing_key.kid)}"}, 401),
        ({"Authorization": f"Bearer {tokens.sign(forger)}"}, 401),
        (
            {
                "Authorization": "Bearer "
                + tokens.sign(harness.signing_key, tokens.claims(aud="another-api"))
            },
            401,
        ),
        (
            {
                "Authorization": "Bearer "
                + tokens.sign(harness.signing_key, tokens.claims(iss="https://other.test.example"))
            },
            401,
        ),
        (
            {
                "Authorization": "Bearer "
                + tokens.sign(harness.signing_key, tokens.claims(exp=1000))
            },
            401,
        ),
        (harness.headers(subject="someone-else"), 403),
    ]


@pytest.mark.parametrize(("method", "path", "body"), REQUESTS)
def test_ac0_1_refused_callers_never_reach_a_handler(
    harness: Harness, spies: list[str], method: str, path: str, body: dict[str, Any] | None
) -> None:
    """AC0.1: 401 (or 403 for another subject) and no handler or service call."""
    for headers, expected in _bad_tokens(harness):
        response = harness.client.request(method, path, json=body, headers=headers)
        assert response.status_code == expected, (headers, response.text)
        error = response.json()
        assert error["code"] == ("NOT_OWNER" if expected == 403 else "UNAUTHENTICATED")
        assert error["requestId"]
    assert spies == []


def test_ac0_1_invalid_body_from_a_stranger_is_still_401(
    harness: Harness, spies: list[str]
) -> None:
    """Authentication runs before body validation, so nothing is learned without a token."""
    response = harness.client.post("/slice/projects", json={"unknown": 1})
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert spies == []


def test_health_is_open_and_fixed(harness: Harness) -> None:
    """NFR11.2 / C10."""
    response = harness.client.get("/health")
    assert (response.status_code, response.json()) == (200, {"status": "ok"})


def test_ac0_1a_create_app_refuses_a_local_issuer_outside_local_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC0.1a: start-up fails before any route is served."""
    monkeypatch.setenv("AUTH_ISSUER", "http://fake-idp.invalid")
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(ConfigurationError):
        create_app()
    with pytest.raises(ConfigurationError):
        load_settings()


# --- W1 create, W2 save (AC0.3, AC0.4) --------------------------------------------------------


def test_create_stores_a_draft_at_revision_1(harness: Harness) -> None:
    created = harness.client.post(
        "/slice/projects", json={"title": "Hello, World!"}, headers=harness.headers()
    )
    assert created.status_code == 201
    body = created.json()
    assert (body["revision"], body["status"], body["slug"]) == (1, "Draft", "hello-world")
    assert body["publishedRevision"] is None
    assert created.headers["ETag"] == '"1"'
    duplicate = harness.create("Hello world")
    assert duplicate["slug"] == "hello-world-2"


def test_list_and_get_projects(harness: Harness) -> None:
    created = harness.create("First")
    listing = harness.client.get("/slice/projects", headers=harness.headers()).json()["projects"]
    assert [p["projectId"] for p in listing] == [created["projectId"]]
    fetched = harness.client.get(
        f"/slice/projects/{created['projectId']}", headers=harness.headers()
    )
    assert fetched.json()["title"] == "First"
    missing = harness.client.get("/slice/projects/nope", headers=harness.headers())
    assert (missing.status_code, missing.json()["code"]) == (404, "NOT_FOUND")


def test_save_increments_the_revision(harness: Harness) -> None:
    created = harness.create()
    saved = harness.save(created["projectId"], 1, summary="New summary")
    assert saved.status_code == 200
    assert (saved.json()["revision"], saved.json()["summary"]) == (2, "New summary")
    assert saved.headers["ETag"] == '"2"'


def test_ac0_3_stale_save_is_refused_and_nothing_changes(harness: Harness) -> None:
    """AC0.3: a save based on N-1 gets 409 STALE_REVISION; the project is unchanged."""
    created = harness.create()
    harness.save(created["projectId"], 1, title="Revision two")
    stale = harness.save(created["projectId"], 1, title="Lost update")
    assert (stale.status_code, stale.json()["code"]) == (409, "STALE_REVISION")
    stored = harness.projects.get(str(created["projectId"]))
    assert stored is not None
    assert (stored.title, stored.revision) == ("Revision two", 2)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"title": ""}, "title"),
        ({"title": "x" * 121}, "title"),
        ({"summary": "s" * 1201}, "summary"),
        ({"slug": "Not A Slug"}, "slug"),
        ({}, "nothing to save"),
        ({"privateNotes": "x"}, "privateNotes"),
    ],
)
def test_ac0_4_invalid_saves_are_refused_with_the_reason(
    harness: Harness, changes: dict[str, str], reason: str
) -> None:
    """AC0.4: 422 VALIDATION_FAILED, naming what is wrong."""
    created = harness.create()
    response = harness.save(created["projectId"], 1, **changes)
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_FAILED"
    assert reason in response.json()["message"]


def test_ac0_4_create_validation(harness: Harness) -> None:
    response = harness.client.post(
        "/slice/projects", json={"title": " "}, headers=harness.headers()
    )
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_FAILED")


def test_ac0_4_slug_in_use_is_refused(harness: Harness) -> None:
    first = harness.create("Alpha")
    second = harness.create("Beta")
    response = harness.save(second["projectId"], 1, slug=str(first["slug"]))
    assert (response.status_code, response.json()["code"]) == (409, "SLUG_TAKEN")


def test_ac0_4_slug_is_fixed_after_the_first_publish(harness: Harness) -> None:
    created = harness.create("Alpha")
    assert harness.publish_revision(created["projectId"], 1).status_code == 200
    response = harness.save(created["projectId"], 1, slug="renamed")
    assert response.status_code == 422
    assert "fixed after the first publish" in response.json()["message"]


@pytest.mark.parametrize(("header", "status"), [(None, 428), ("abc", 422), ('W/"1"', 200)])
def test_if_match_is_required_and_parsed(harness: Harness, header: str | None, status: int) -> None:
    created = harness.create()
    headers = harness.headers() if header is None else harness.headers(**{"If-Match": header})
    response = harness.client.patch(
        f"/slice/projects/{created['projectId']}", json={"summary": "x"}, headers=headers
    )
    assert response.status_code == status
    if status == 428:
        assert response.json()["code"] == "REVISION_REQUIRED"


# --- W3 preview (AC0.5) -----------------------------------------------------------------------


def _site_files(site: SiteStore) -> list[str]:
    return sorted(p.relative_to(site.root).as_posix() for p in site.root.rglob("*"))


def test_ac0_5_preview_returns_the_candidate_and_writes_nothing(harness: Harness) -> None:
    """AC0.5: the candidate snapshot of the current revision; the output folder is untouched."""
    created = harness.create("Draft <b>title</b>", "A summary")
    before = _site_files(harness.site)
    response = harness.client.get(
        f"/slice/projects/{created['projectId']}/preview", headers=harness.headers()
    )
    assert response.status_code == 200
    body = response.json()
    assert body["revision"] == 1
    exhibit = body["snapshot"]["exhibits"][0]
    assert (exhibit["title"], exhibit["summary"], exhibit["slug"]) == (
        "Draft <b>title</b>",
        "A summary",
        "draft-b-title-b",
    )
    assert sorted(body["imageAddresses"]) == [
        "ast_PlaceholderAsset0001/w480.jpg",
        "ast_PlaceholderAsset0001/w480.webp",
    ]
    assert body["imageAddresses"]["ast_PlaceholderAsset0001/w480.jpg"].startswith(
        "data:image/jpeg;base64,"
    )
    assert _site_files(harness.site) == before
    assert harness.renderer.calls == []
    assert harness.site.current_release() == EMPTY_RELEASE


# --- W4 publish (AC0.6, AC0.7, AC0.8) ------------------------------------------------------------


def _public_file(harness: Harness, relative: str) -> str:
    release = harness.site.current_release()
    assert release is not None
    return (harness.site.releases / release / relative).read_text(encoding="utf-8")


def test_ac0_6_publish_freezes_a_c2_snapshot_and_serves_it(harness: Harness) -> None:
    """AC0.6: confirm Publish for current revision N; a C2 snapshot is frozen and served."""
    created = harness.create("Published title", "Published summary")
    response = harness.publish_revision(created["projectId"], 1)
    assert response.status_code == 200
    body = response.json()
    assert (body["sourceRevision"], body["status"]) == (1, "Published")
    version = harness.publications.get_version(body["versionId"])
    assert version is not None
    snapshot = version.snapshot
    assert snapshot["schemaVersion"] == "1.0"
    assert snapshot["exhibits"][0]["title"] == "Published title"
    assert snapshot["exhibits"][0]["publishedAt"] == body["publishedAt"]
    assert harness.site.current_release() == body["versionId"]
    assert "Published title" in _public_file(harness, "work/published-title/index.html")
    media = harness.site.releases / body["versionId"] / "media" / "ast_PlaceholderAsset0001"
    assert (media / "w480.jpg").is_file()
    assert harness.renderer.calls[-1][1] == "public"


def test_ac0_7_publish_of_a_revision_no_longer_current_is_refused(harness: Harness) -> None:
    """AC0.7: 409 and nothing is written."""
    created = harness.create()
    harness.save(created["projectId"], 1, summary="newer")
    before = _site_files(harness.site)
    response = harness.publish_revision(created["projectId"], 1)
    assert (response.status_code, response.json()["code"]) == (409, "STALE_REVISION")
    assert _site_files(harness.site) == before
    assert harness.renderer.calls == []
    assert harness.publications.versions == {}


def test_publish_unknown_project_and_closed_body(harness: Harness) -> None:
    missing = harness.publish_revision("nope", 1)
    assert missing.status_code == 404
    created = harness.create()
    response = harness.client.post(
        f"/slice/projects/{created['projectId']}/publish",
        json={"revision": 1, "force": True},
        headers=harness.headers(),
    )
    assert response.status_code == 422


def test_ac0_8_status_derivation_and_public_page_unchanged_until_publish(harness: Harness) -> None:
    """AC0.8 / BR3.4: Draft -> Published -> Changes since last publish -> Published."""
    created = harness.create("Version one")
    project_id = created["projectId"]

    def status() -> str:
        response = harness.client.get(f"/slice/projects/{project_id}", headers=harness.headers())
        return str(response.json()["status"])

    assert status() == "Draft"
    assert harness.save(project_id, 1, summary="still a draft").status_code == 200
    assert status() == "Draft"
    assert harness.publish_revision(project_id, 2).status_code == 200
    assert status() == "Published"
    page_before = _public_file(harness, "work/version-one/index.html")
    harness.save(project_id, 2, title="Version two")
    assert status() == "Changes since last publish"
    assert _public_file(harness, "work/version-one/index.html") == page_before
    harness.save(project_id, 3, summary="more")
    assert status() == "Changes since last publish"
    assert harness.publish_revision(project_id, 4).status_code == 200
    assert status() == "Published"
    assert "Version two" in _public_file(harness, "work/version-one/index.html")


def test_site_snapshot_holds_every_published_exhibit(harness: Harness) -> None:
    first = harness.create("First project")
    second = harness.create("Second project")
    harness.publish_revision(first["projectId"], 1)
    body = harness.publish_revision(second["projectId"], 1).json()
    version = harness.publications.get_version(body["versionId"])
    assert version is not None
    assert [e["title"] for e in version.snapshot["exhibits"]] == ["Second project", "First project"]
    assert version.snapshot["generation"] == 2


def test_r09_publishes_in_the_same_second_never_tie(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R-09: with a fixed clock, the later Publish is the site version, and reconciliation
    keeps public on it."""
    from datetime import UTC, datetime

    moment = datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(harness.publish, "_clock", lambda: moment)
    first = harness.create("First project")
    second = harness.create("Second project")
    first_body = harness.publish_revision(first["projectId"], 1).json()
    second_body = harness.publish_revision(second["projectId"], 1).json()
    assert first_body["publishedAt"] == second_body["publishedAt"]
    site = harness.publish.site_version()
    assert site is not None and site.version_id == second_body["versionId"]
    assert site.snapshot["generation"] == 2
    assert [e["title"] for e in site.snapshot["exhibits"]] == ["Second project", "First project"]
    assert harness.publish.reconcile() == second_body["versionId"]
    assert harness.site.current_release() == second_body["versionId"]
    first_version = harness.publications.get_version(first_body["versionId"])
    assert first_version is not None and first_version.sequence < site.sequence


def test_old_releases_are_pruned_to_the_last_three(harness: Harness) -> None:
    created = harness.create("Prune")
    revision = 1
    for _ in range(5):
        assert harness.publish_revision(created["projectId"], revision).status_code == 200
        saved = harness.save(created["projectId"], revision, summary=f"r{revision}")
        revision = saved.json()["revision"]
    releases = [p.name for p in harness.site.releases.iterdir() if p.name != EMPTY_RELEASE]
    assert len(releases) == 3
    assert harness.site.current_release() in releases


# --- AC0.9: failures partway leave the previous output and current version -------------------


def _state(harness: Harness, project_id: object) -> tuple[str | None, str | None, list[str]]:
    project = harness.projects.get(str(project_id))
    assert project is not None
    releases = sorted(p.name for p in harness.site.releases.iterdir())
    return project.current_version_id, harness.site.current_release(), releases


@pytest.fixture
def published(harness: Harness) -> dict[str, Any]:
    """A project published once at revision 1, then saved to revision 2."""
    created = harness.create("Stable title")
    harness.publish_revision(created["projectId"], 1)
    harness.save(created["projectId"], 1, title="Unpublished change")
    return created


def test_ac0_9_render_failure_changes_nothing(harness: Harness, published: dict[str, Any]) -> None:
    from portfolio_api.slice.renderer import RenderFailedError

    before = _state(harness, published["projectId"])
    harness.renderer.fail = RenderFailedError("the renderer refused the snapshot")
    response = harness.publish_revision(published["projectId"], 2)
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL"
    assert _state(harness, published["projectId"]) == before


def test_ac0_9_transaction_failure_removes_the_new_release(
    harness: Harness, published: dict[str, Any]
) -> None:
    from portfolio_api.slice.mongo import DatabaseUnavailableError

    before = _state(harness, published["projectId"])
    harness.publications.fail_commit = DatabaseUnavailableError("transaction aborted")
    response = harness.publish_revision(published["projectId"], 2)
    assert response.status_code == 500
    assert _state(harness, published["projectId"]) == before


def test_ac0_9_swap_failure_is_compensated(
    harness: Harness, published: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The version record is removed and the previous current version restored."""
    before = _state(harness, published["projectId"])

    def failing_swap(name: str) -> None:
        raise OSError("rename failed")

    monkeypatch.setattr(harness.site, "swap_public", failing_swap)
    response = harness.publish_revision(published["projectId"], 2)
    assert response.status_code == 500
    assert "previous version is kept" in response.json()["message"]
    monkeypatch.undo()
    assert _state(harness, published["projectId"]) == before
    assert len(harness.publications.versions) == 1


class _Records(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def test_failed_compensation_is_repaired_by_reconciliation(
    harness: Harness, published: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """If compensation itself fails, it is logged and reconciliation converges on the database."""
    records = _Records()
    logging.getLogger("portfolio_api.slice.publish").addHandler(records)
    harness.publications.fail_compensate = RuntimeError("database gone")

    def failing_swap(name: str) -> None:
        raise OSError("rename failed")

    monkeypatch.setattr(harness.site, "swap_public", failing_swap)
    assert harness.publish_revision(published["projectId"], 2).status_code == 500
    logging.getLogger("portfolio_api.slice.publish").removeHandler(records)
    assert any("compensation failed" in message for message in records.messages)
    monkeypatch.undo()
    harness.publications.fail_compensate = None
    project = harness.projects.get(str(published["projectId"]))
    assert project is not None
    assert harness.site.current_release() != project.current_version_id
    assert harness.publish.reconcile() == project.current_version_id
    assert harness.site.current_release() == project.current_version_id


def test_reconciliation_after_a_crash_rerenders_a_missing_release(
    harness: Harness, published: dict[str, Any]
) -> None:
    """A crash after the commit but before the swap converges on the database state."""
    project = harness.projects.get(str(published["projectId"]))
    assert project is not None and project.current_version_id is not None
    current = project.current_version_id
    harness.site.swap_public(EMPTY_RELEASE)
    harness.site.delete_release(current)
    calls_before = len(harness.renderer.calls)
    assert harness.publish.reconcile() == current
    assert harness.site.current_release() == current
    assert harness.site.has_release(current)
    assert len(harness.renderer.calls) == calls_before + 1


def test_empty_database_with_leftover_releases_reconciles_and_publishes(harness: Harness) -> None:
    """The verification stack keeps its site volume while MongoDB (tmpfs) starts empty:
    public must go back to the placeholder, and a new Publish must serve only the new release."""
    leftover = harness.site.releases / "a1b2c3d4leftover"
    (leftover / "work" / "old-project").mkdir(parents=True)
    (leftover / "work" / "old-project" / "index.html").write_text("<html>old</html>")
    harness.site.swap_public("a1b2c3d4leftover")
    assert harness.publish.reconcile() == EMPTY_RELEASE
    assert harness.site.current_release() == EMPTY_RELEASE
    created = harness.create("Fresh project")
    body = harness.publish_revision(created["projectId"], 1).json()
    assert harness.site.current_release() == body["versionId"]
    served = harness.site.releases / body["versionId"]
    assert (served / "work" / "fresh-project" / "index.html").is_file()
    assert not (served / "work" / "old-project").exists()
    version = harness.publications.get_version(body["versionId"])
    assert version is not None and version.snapshot["generation"] == 1


def test_reconciliation_is_a_no_op_when_consistent(
    harness: Harness, published: dict[str, Any]
) -> None:
    calls_before = len(harness.renderer.calls)
    current = harness.site.current_release()
    assert harness.publish.reconcile() == current
    assert len(harness.renderer.calls) == calls_before


# --- errors, CORS, request ids --------------------------------------------------------------------


def test_unexpected_errors_answer_500_with_a_request_id(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_: Any, **__: Any) -> Any:
        raise RuntimeError("secret detail")

    monkeypatch.setattr(harness.app.state.services.projects, "list", boom)
    from fastapi.testclient import TestClient

    client = TestClient(harness.app, raise_server_exceptions=False)
    response = client.get("/slice/projects", headers=harness.headers(**{"X-Request-Id": "req-123"}))
    assert response.status_code == 500
    assert response.json() == {
        "code": "INTERNAL",
        "message": "Something went wrong; nothing was published.",
        "requestId": "req-123",
    }


def test_request_id_is_echoed_or_generated(harness: Harness) -> None:
    echoed = harness.client.get("/health", headers={"X-Request-Id": "abc-123"})
    assert echoed.headers["X-Request-Id"] == "abc-123"
    generated = harness.client.get("/health", headers={"X-Request-Id": "bad id with spaces"})
    assert generated.headers["X-Request-Id"] != "bad id with spaces"
    assert len(generated.headers["X-Request-Id"]) == 32


def test_cors_allows_only_the_studio_origin(harness: Harness) -> None:
    preflight = harness.client.options(
        "/slice/projects",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,if-match,content-type",
        },
    )
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-credentials" not in preflight.headers
    other = harness.client.get("/health", headers={"Origin": "http://evil.test.example"})
    assert "access-control-allow-origin" not in other.headers
