"""The renderer subprocess boundary: arguments, refusal and output shape (ADR-008)."""

from __future__ import annotations

import sys

import pytest
from portfolio_studio.renderer import CliRenderer, RenderFailedError

ECHO = (
    "import json, sys\n"
    "args = sys.argv[1:]\n"
    "snapshot = json.load(sys.stdin)\n"
    "print(json.dumps({'contractVersion': '1.0', 'pages': [{'path': '/', 'status': 200,"
    " 'html': ' '.join(args) + ' ' + snapshot['marker']}], 'requiredImages': [],"
    " 'requiredDownloads': [], 'staticAssets': []}))\n"
)


def test_preview_slug_is_passed_and_output_parsed() -> None:
    renderer = CliRenderer((sys.executable, "-c", ECHO))
    output = renderer.render({"marker": "ok"}, "preview", preview_slug="stars")
    assert output.pages[0].html == "--mode preview --preview-slug stars ok"
    public = renderer.render({"marker": "ok"}, "public")
    assert public.pages[0].html == "--mode public ok"


def test_refusal_and_bad_output_raise() -> None:
    refusing = CliRenderer((sys.executable, "-c", "import sys; sys.exit(2)"))
    with pytest.raises(RenderFailedError, match="refused"):
        refusing.render({}, "public")
    garbage = CliRenderer((sys.executable, "-c", "print('not json')"))
    with pytest.raises(RenderFailedError):
        garbage.render({}, "public")
    missing = CliRenderer(("definitely-not-a-command-xyz",))
    with pytest.raises(RenderFailedError, match="could not run"):
        missing.render({}, "public")
