"""Generate the walking slice's one fixture image (LOCAL-ONLY test data; C8 variant rule).

The image is an abstract placeholder drawn from code, so the project owns it outright and it
carries no camera or location metadata. Its width is 400 pixels, below 480, so the C8 variant
rule gives one variant, ``w480``, encoded at the image's own width, in webp and jpg.

The committed files were produced once with:

    python -m pip install pillow
    python local/fixtures/make_fixture.py

Pillow is needed only to regenerate the fixture; nothing at runtime depends on it.

It also writes ``derivatives.sha256.json``, the trusted digests of the authorized derivatives
that the public-output scan compares every published image against (Codex review R3). The
digest file was added after the images; it was computed from the committed images, in the
format ``write_digests`` produces.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw  # type: ignore[import-not-found]

ASSET_REF = "ast_SliceFixtureImage0001"
WIDTH, HEIGHT = 400, 300
ALT_TEXT = "Abstract placeholder illustration of overlapping blue and amber shapes"
HERE = Path(__file__).resolve().parent


def draw() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = image.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            pixels[x, y] = (30 + x * 60 // WIDTH, 60 + y * 80 // HEIGHT, 120 + x * 80 // WIDTH)
    canvas = ImageDraw.Draw(image)
    canvas.ellipse((40, 50, 220, 230), fill=(233, 168, 60))
    canvas.rectangle((180, 90, 360, 250), fill=(43, 93, 138))
    canvas.polygon([(260, 30), (380, 140), (200, 160)], fill=(240, 236, 228))
    return image


DIGESTS_DESCRIPTION = (
    "LOCAL-ONLY trusted digests of the authorized walking-slice fixture derivatives (Codex "
    "review R3). scripts/scan_output.py --media-digests fails any published media file whose "
    "bytes differ, or that has no entry here. Regenerated together with the images by "
    "local/fixtures/make_fixture.py."
)


def write_digests(folder: Path) -> None:
    """Write derivatives.sha256.json for every derivative in ``folder``."""
    derivatives = {
        f"media/{ASSET_REF}/{path.name}": hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(folder.iterdir())
        if path.suffix in (".jpg", ".webp")
    }
    document = {
        "description": DIGESTS_DESCRIPTION,
        "version": 1,
        "algorithm": "sha256",
        "derivatives": derivatives,
    }
    text = json.dumps(document, indent=2) + "\n"
    (HERE / "derivatives.sha256.json").write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    folder = HERE / ASSET_REF
    folder.mkdir(exist_ok=True)
    image = draw()
    # No exif/icc arguments: the derivatives carry no metadata.
    image.save(folder / "w480.jpg", "JPEG", quality=85, optimize=True)
    image.save(folder / "w480.webp", "WEBP", quality=80, method=6)
    manifest = {"assetRef": ASSET_REF, "altText": ALT_TEXT, "width": WIDTH, "height": HEIGHT}
    text = json.dumps(manifest, indent=2) + "\n"
    (HERE / "fixture.json").write_text(text, encoding="utf-8", newline="\n")
    write_digests(folder)


if __name__ == "__main__":
    main()
