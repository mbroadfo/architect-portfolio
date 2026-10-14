"""Renderer subprocess boundary tests (Step 18; C11 shape, BR3.2).

The real renderer is never started here: the subprocess is a small Python stand-in.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
from portfolio_api.slice.renderer import RenderFailedError, SubprocessRenderer, parse_output

VALID: dict[str, Any] = {
    "contractVersion": "1.0",
    "pages": [
        {"path": "/", "status": 200, "html": "<html></html>"},
        {"path": "/404.html", "status": 404, "html": "x"},
    ],
    "requiredImages": [
        {"assetRef": "ast_PlaceholderAsset0001", "variant": "w480", "format": "jpg"}
    ],
    "requiredDownloads": [],
    "staticAssets": ["/assets/site.0123456789.css"],
}


def test_parse_output_accepts_a_c11_render_output() -> None:
    output = parse_output(json.dumps(VALID))
    assert [p.path for p in output.pages] == ["/", "/404.html"]
    assert output.required_images[0].variant == "w480"
    assert output.static_assets == ("/assets/site.0123456789.css",)


@pytest.mark.parametrize(
    "mutation",
    [
        {"contractVersion": "2.0"},
        {"pages": [{"path": "/../etc/passwd", "status": 200, "html": "x"}]},
        {"pages": [{"path": "/", "status": 500, "html": "x"}]},
        {"pages": "not a list"},
        {"requiredImages": [{"assetRef": "a", "variant": "w9999", "format": "jpg"}]},
        {"staticAssets": ["/assets/evil.js"]},
        {"requiredDownloads": [{"assetRef": "a", "downloadName": "x.pdf"}]},
    ],
)
def test_parse_output_refuses_unexpected_shapes(mutation: dict[str, Any]) -> None:
    with pytest.raises(RenderFailedError):
        parse_output(json.dumps({**VALID, **mutation}))


def test_parse_output_refuses_non_json() -> None:
    with pytest.raises(RenderFailedError, match="not JSON"):
        parse_output("<html>")
    with pytest.raises(RenderFailedError):
        parse_output("[]")


def _script(tmp_path: Path, body: str) -> tuple[str, ...]:
    script = tmp_path / "stand_in.py"
    script.write_text(body, encoding="utf-8")
    return (sys.executable, str(script))


def test_subprocess_renderer_round_trip(tmp_path: Path) -> None:
    command = _script(
        tmp_path,
        "import json, sys\n"
        "snapshot = json.load(sys.stdin)\n"
        "assert sys.argv[1:] == ['--mode', 'public']\n"
        f"print(json.dumps({VALID!r}))\n",
    )
    output = SubprocessRenderer(command).render({"schemaVersion": "1.0"}, "public")
    assert len(output.pages) == 2


def test_subprocess_renderer_failure_exit(tmp_path: Path) -> None:
    command = _script(
        tmp_path, "import sys\nsys.stderr.write('RenderInputError: bad\\n')\nsys.exit(2)\n"
    )
    with pytest.raises(RenderFailedError, match="RenderInputError: bad"):
        SubprocessRenderer(command).render({}, "public")


def test_subprocess_renderer_missing_command_and_timeout(tmp_path: Path) -> None:
    with pytest.raises(RenderFailedError, match="could not run"):
        SubprocessRenderer((str(tmp_path / "missing-binary"),)).render({}, "public")
    slow = _script(tmp_path, "import time\ntime.sleep(5)\n")
    with pytest.raises(RenderFailedError, match="could not run"):
        SubprocessRenderer(slow, timeout=0.5).render({}, "public")
