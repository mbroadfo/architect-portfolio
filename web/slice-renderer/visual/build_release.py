"""Build a local release folder from the visual-check fixture, then scan it (not part of CI).

The fixture (fixture-snapshot.json) carries the STARS and Baduk text of the owner-approved
Refined Mockups prototype (prototype/export/publication.js); its images are the prototype's
live captures (prototype/assets/live/), mapped by fixture-images.json. This script:

1. renders the fixture with the built renderer CLI (dist/cli.cjs, ``npm run build`` first);
2. writes the pages at their C9 keys and copies the static assets;
3. encodes every required image variant (C8) with Pillow, without metadata;
4. writes the SHA-256 digest manifest and runs scripts/scan_output.py over the folder.

Usage (from web/slice-renderer, with the repository's Python virtual environment)::

    python visual/build_release.py --images <prototype>/assets/live --out <folder>

Exit code: the scan's (0 clean, 1 findings), or 2 for a usage or build error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
RENDERER = HERE.parent
ROOT = RENDERER.parent.parent
WIDTHS = {"w480": 480, "w960": 960, "w1600": 1600}


def page_key(path: str) -> str:
    """Map a C9 page path to its file in the release folder."""
    if path.endswith(".html"):
        return path.lstrip("/")
    return f"{path.strip('/')}/index.html".lstrip("/")


def encode(source: Path, variant: str, image_format: str, target: Path) -> None:
    """Write one variant: never upscaled, RGB, no EXIF or other metadata."""
    with Image.open(source) as image:
        rgb = image.convert("RGB")
        width = min(WIDTHS[variant], rgb.width)
        height = round(rgb.height * width / rgb.width)
        resized = rgb.resize((width, height), Image.Resampling.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        if image_format == "webp":
            resized.save(target, "WEBP", quality=82)
        else:
            resized.save(target, "JPEG", quality=84, optimize=True, progressive=True)


def build(images: Path, out: Path) -> Path:
    """Render and write the release; return the digest manifest path."""
    snapshot_file = HERE / "fixture-snapshot.json"
    node = shutil.which("node")
    if node is None:
        raise OSError("node is not on PATH")
    # Fixed argument list, no shell: the renderer CLI built from this repository.
    result = subprocess.run(  # noqa: S603
        [node, str(RENDERER / "dist" / "cli.cjs"), "--mode", "public"],
        input=snapshot_file.read_bytes(),
        capture_output=True,
        check=True,
    )
    output = json.loads(result.stdout)
    sources = json.loads((HERE / "fixture-images.json").read_text(encoding="utf-8"))
    if out.exists():
        shutil.rmtree(out)
    release = out / "release"
    for page in output["pages"]:
        target = release / page_key(page["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page["html"], encoding="utf-8", newline="\n")
    for asset in output["staticAssets"]:
        name = asset.rsplit("/", 1)[1]
        stem, _hash, ext = name.rsplit(".", 2)
        target = release / "assets" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RENDERER / "assets" / f"{stem}.{ext}", target)
    digests: dict[str, str] = {}
    for required in output["requiredImages"]:
        key = f"media/{required['assetRef']}/{required['variant']}.{required['format']}"
        encode(
            images / sources[required["assetRef"]],
            required["variant"],
            required["format"],
            release / key,
        )
        digests[key] = hashlib.sha256((release / key).read_bytes()).hexdigest()
    manifest = out / "derivatives.sha256.json"
    manifest.write_text(
        json.dumps({"version": 1, "algorithm": "sha256", "derivatives": digests}, indent=2),
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    """Build the release, then run the public-output scan over it."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--images", required=True, type=Path, help="prototype/assets/live")
    parser.add_argument("--out", required=True, type=Path, help="output folder (replaced)")
    args = parser.parse_args()
    try:
        manifest = build(args.images, args.out)
    except (OSError, subprocess.CalledProcessError, KeyError, ValueError) as error:
        print(f"build_release: {error}", file=sys.stderr)
        return 2
    scan = [
        sys.executable,
        str(ROOT / "scripts" / "scan_output.py"),
        "--release",
        str(args.out / "release"),
        "--snapshot",
        str(HERE / "fixture-snapshot.json"),
        "--vocabulary",
        str(RENDERER / "src" / "template-strings.json"),
        "--static-dir",
        str(RENDERER / "assets"),
        "--media-digests",
        str(manifest),
    ]
    # Fixed argument list, no shell: this interpreter running the repository's scan script.
    return subprocess.run(scan, check=False).returncode  # noqa: S603


if __name__ == "__main__":
    sys.exit(main())
