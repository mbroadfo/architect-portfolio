"""serve-site: C9 address mapping, 404 pages and the public security headers."""

from __future__ import annotations

import http.client
from pathlib import Path

import pytest
from portfolio_studio.server import BindError
from portfolio_studio.site_server import create_site_server, resolve, start_in_background


@pytest.fixture
def site(tmp_path: Path) -> Path:
    root = tmp_path / "site"
    for relative, text in {
        "index.html": "home",
        "404.html": "not found",
        "category-404.html": "no category",
        "work/index.html": "all work",
        "work/stars/index.html": "stars",
        "category/astronomy/index.html": "astronomy",
        "assets/site.0123456789.css": "body{}",
        "media/ast_abcdefghijklmnop/w480.jpg": "jpg",
    }.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def test_resolve_maps_c9_addresses(site: Path) -> None:
    assert resolve(site, "/") == (site / "index.html", 200)
    assert resolve(site, "/work/") == (site / "work/index.html", 200)
    assert resolve(site, "/work/stars") == (site / "work/stars/index.html", 200)
    assert resolve(site, "/category/astronomy") == (site / "category/astronomy/index.html", 200)
    assert resolve(site, "/category/woodworking") == (site / "category-404.html", 404)
    assert resolve(site, "/work/risk") == (site / "404.html", 404)
    assert resolve(site, "/../secret") == (site / "404.html", 404)
    assert resolve(site, "/work/%2e%2e/x") == (site / "404.html", 404)


def test_serves_with_public_headers(site: Path) -> None:
    server = start_in_background(site, "127.0.0.1", 0)
    port = server.server_address[1]
    try:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request("GET", "/work/stars")
        response = connection.getresponse()
        assert response.status == 200 and response.read() == b"stars"
        assert response.getheader("Content-Security-Policy") == (
            "default-src 'self'; frame-ancestors 'none'"
        )
        assert response.getheader("X-Content-Type-Options") == "nosniff"
        assert response.getheader("Cache-Control") == "no-cache"
        connection.request("GET", "/assets/site.0123456789.css")
        asset = connection.getresponse()
        asset.read()
        assert "immutable" in asset.getheader("Cache-Control", "")
        connection.request("GET", "/work/missing")
        missing = connection.getresponse()
        assert missing.status == 404 and missing.read() == b"not found"
        connection.request("GET", "/", headers={"Host": "evil.example"})
        refused = connection.getresponse()
        refused.read()
        assert refused.status == 421
        connection.request("HEAD", "/")
        head = connection.getresponse()
        assert head.status == 200 and head.read() == b""
    finally:
        server.shutdown()
        server.server_close()


def test_site_server_binds_loopback_only(site: Path) -> None:
    with pytest.raises(BindError):
        create_site_server(site, "0.0.0.0", 0)  # noqa: S104 - the refused address
