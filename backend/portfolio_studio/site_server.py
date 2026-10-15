"""Serve the generated public site on a loopback port, with the public headers (C9, NFR15).

This is how Michael views the "public" site locally before any hosting exists. It serves the
build output read-only, maps the C9 addresses to files (``/work/<slug>`` to
``work/<slug>/index.html``), answers unknown addresses with the site's own 404 pages, and
sends the same security headers as the U0 public server: CSP ``default-src 'self'`` with
``frame-ancestors 'none'``, ``nosniff`` and a referrer policy; hashed assets and media are
cached as immutable, pages are revalidated.
"""

from __future__ import annotations

import re
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from portfolio_studio.server import LOOPBACK, check_bind_host

PUBLIC_CSP = "default-src 'self'; frame-ancestors 'none'"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".woff2": "font/woff2",
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
}
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
ROUTES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^/$"), "index.html"),
    (re.compile(r"^/work/?$"), "work/index.html"),
    (re.compile(rf"^/work/(?P<slug>{SLUG})/?$"), "work/{slug}/index.html"),
    (re.compile(r"^/category/(?P<slug>[a-z]+)/?$"), "category/{slug}/index.html"),
    (
        re.compile(r"^/assets/(?P<name>[a-z0-9-]+\.[0-9a-f]{8,64}\.(?:css|js|woff2))$"),
        "assets/{name}",
    ),
    (
        re.compile(
            r"^/media/(?P<ref>ast_[A-Za-z0-9]{16,32})/(?P<name>w(?:480|960|1600)\.(?:webp|jpg))$"
        ),
        "media/{ref}/{name}",
    ),
)


def resolve(root: Path, path: str) -> tuple[Path, int]:
    """Map a request path to a file under ``root`` and the status to answer with."""
    for pattern, template in ROUTES:
        match = pattern.match(path)
        if match:
            candidate = root / template.format(**match.groupdict())
            if candidate.is_file():
                return candidate, 200
            break
    fallback = "category-404.html" if path.startswith("/category/") else "404.html"
    return root / fallback, 404


def make_handler(root: Path) -> type[BaseHTTPRequestHandler]:
    class SiteHandler(BaseHTTPRequestHandler):
        server_version = "portfolio-site"
        sys_version = ""

        def do_GET(self) -> None:
            self._serve(include_body=True)

        def do_HEAD(self) -> None:
            self._serve(include_body=False)

        def _serve(self, include_body: bool) -> None:
            address = self.server.server_address
            port = address[1] if isinstance(address, tuple) else 0
            if self.headers.get("Host", "") not in {f"{LOOPBACK}:{port}", f"localhost:{port}"}:
                self._send(HTTPStatus.MISDIRECTED_REQUEST, b"", ".html", include_body)
                return
            path = self.path.split("?", 1)[0].split("#", 1)[0]
            file, status = resolve(root, path)
            data = file.read_bytes() if file.is_file() else b"Not found"
            self._send(status, data, file.suffix, include_body)

        def _send(self, status: int, data: bytes, suffix: str, include_body: bool) -> None:
            self.send_response(status)
            self.send_header("Content-Type", CONTENT_TYPES.get(suffix, "application/octet-stream"))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Security-Policy", PUBLIC_CSP)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            immutable = suffix in (".css", ".js", ".woff2", ".webp", ".jpg") and status == 200
            self.send_header(
                "Cache-Control", "public, max-age=31536000, immutable" if immutable else "no-cache"
            )
            self.end_headers()
            if include_body:
                self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:
            return  # request lines are not logged

    return SiteHandler


def create_site_server(root: Path, host: str, port: int) -> ThreadingHTTPServer:
    check_bind_host(host)
    server = ThreadingHTTPServer((host, port), make_handler(root))
    server.daemon_threads = True
    return server


def start_in_background(root: Path, host: str, port: int) -> ThreadingHTTPServer:
    """Serve the site on a daemon thread (used by ``serve`` next to the Studio)."""
    server = create_site_server(root, host, port)
    threading.Thread(target=server.serve_forever, name="site-server", daemon=True).start()
    return server
