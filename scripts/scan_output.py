"""Public-output allow-list scan (BR3.2, BR3.3, NFR2.1; AC0.9).

Given a release folder and the C2 PublicSiteSnapshot it was rendered from, fail on anything
in the folder that does not come from the snapshot's C2 fields, the renderer's fixed
template vocabulary, the authorized image derivatives or the static assets. Every file is
checked: file names, HTML text, HTML attribute values, JSON keys and values, and the bytes
of every binary file.

Binary files (``media/`` images and ``files/`` downloads) must equal an authorized
derivative byte for byte: their SHA-256 must match the entry for their exact release key in
the trusted digest manifest given with ``--media-digests`` (Codex review R3). A file without
an entry, or with any changed byte (pixels, metadata segments, trailing data), is a finding.
The image type and EXIF checks still run as a second line of defence.

The snapshot itself is checked first: any key outside the C2 allow-list, and any link that
points at a repository host, is a finding.

Usage::

    python scripts/scan_output.py --release <dir> --snapshot <snapshot.json> \
        --vocabulary <template-strings.json> --static-dir <renderer assets dir> \
        --media-digests <derivatives.sha256.json>

The digest manifest is JSON: ``{"version": 1, "algorithm": "sha256", "derivatives":
{"media/<assetRef>/<variant>.<format>": "<64 lowercase hex>", ...}}``.

Exit codes: 0 clean, 1 findings (or nothing scanned), 2 usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

# The C2 PublicSiteSnapshot 1.0 allow-list: every key the schema permits, per object type.
C2_KEYS: dict[str, frozenset[str]] = {
    "root": frozenset(
        {"schemaVersion", "generation", "site", "exhibits", "featuredOrder", "categories"}
    ),
    "site": frozenset({"ownerName", "githubProfileUrl", "contactEmail"}),
    "exhibit": frozenset(
        {
            "slug",
            "title",
            "summary",
            "sections",
            "leadImage",
            "images",
            "attachments",
            "links",
            "liveUrl",
            "badges",
            "publicRepositories",
            "primaryCategory",
            "featured",
            "publishedAt",
        }
    ),
    "sections": frozenset(
        {
            "inspiration",
            "designChallenges",
            "architecturalDecisions",
            "implementation",
            "outcomes",
            "lessonsLearned",
        }
    ),
    "image": frozenset({"assetRef", "altText", "caption", "width", "height"}),
    "attachment": frozenset({"assetRef", "label", "fileType", "byteSize"}),
    "link": frozenset({"kind", "label", "url"}),
    "badge": frozenset({"kind", "spdx"}),
    "publicRepository": frozenset({"name", "url", "licence"}),
    "category": frozenset({"slug", "name", "position"}),
    "categoryWithCount": frozenset({"slug", "name", "position", "count"}),
}
REPOSITORY_HOST = re.compile(
    r"https?://([A-Za-z0-9-]+\.)*(github\.com|githubusercontent\.com|gitlab\.com|bitbucket\.org)"
    r"(:[0-9]+)?(/|$)",
    re.IGNORECASE,
)
VARIANT_WIDTHS: tuple[tuple[str, int], ...] = (("w480", 480), ("w960", 960), ("w1600", 1600))
IMAGE_FORMATS: tuple[str, ...] = ("webp", "jpg")
FILE_EXTENSIONS: dict[str, str] = {
    "PDF": "pdf",
    "SKP": "skp",
    "FCStd": "fcstd",
    "DXF": "dxf",
    "STL": "stl",
    "ZIP": "zip",
    "VSDX": "vsdx",
}
STATIC_ASSET_NAME = re.compile(
    r"^(?P<stem>[a-z0-9-]+)\.(?P<hash>[0-9a-f]{8,64})\.(?P<ext>css|js|woff2)$"
)
URL_ATTRIBUTES = frozenset({"href", "src"})
NUMBER_ATTRIBUTES = frozenset({"width", "height"})
EXIF_MARKER = b"Exif\x00\x00"
BINARY_PREFIXES: tuple[str, ...] = ("media/", "files/")
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
FRAGMENT = re.compile(r"^#[a-z][a-z0-9-]*$")


class DigestManifestError(ValueError):
    """The trusted digest manifest cannot be read or is invalid."""


def load_media_digests(path: Path) -> dict[str, str]:
    """Read the trusted digest manifest: release key -> SHA-256 of the authorized bytes."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DigestManifestError(f"cannot read {path}: {error}") from error
    if (
        not isinstance(document, dict)
        or document.get("version") != 1
        or document.get("algorithm") != "sha256"
        or not isinstance(document.get("derivatives"), dict)
    ):
        raise DigestManifestError(
            f"{path} is not a version 1 sha256 manifest with a 'derivatives' object"
        )
    digests: dict[str, str] = {}
    for key, value in document["derivatives"].items():
        if not isinstance(key, str) or not key.startswith(BINARY_PREFIXES):
            raise DigestManifestError(f"{path}: key {key!r} is not a media/ or files/ path")
        if not isinstance(value, str) or not SHA256_HEX.match(value):
            raise DigestManifestError(f"{path}: {key} has no 64-hex SHA-256 digest")
        digests[key] = value
    return digests


@dataclass(frozen=True)
class Finding:
    """One allow-list violation."""

    location: str
    reason: str


@dataclass
class Allowed:
    """Everything the release may contain."""

    strings: set[str] = field(default_factory=set)
    urls: set[str] = field(default_factory=set)
    numbers: set[str] = field(default_factory=set)
    files: set[str] = field(default_factory=set)
    # Same-page links ("#main"): only fragments the template vocabulary itself spells.
    fragments: set[str] = field(default_factory=set)


# --- snapshot checks -------------------------------------------------------------------


def _check_keys(value: object, kind: str, where: str, findings: list[Finding]) -> None:
    if not isinstance(value, dict):
        return
    for key in value:
        if key not in C2_KEYS[kind]:
            findings.append(Finding(f"snapshot:{where}.{key}", "field not in the C2 allow-list"))


def check_snapshot(snapshot: dict[str, Any]) -> list[Finding]:
    """Return findings for keys outside C2 and for repository-host links."""
    findings: list[Finding] = []
    _check_keys(snapshot, "root", "$", findings)
    _check_keys(snapshot.get("site"), "site", "$.site", findings)
    for c_index, category in enumerate(snapshot.get("categories") or []):
        _check_keys(category, "categoryWithCount", f"$.categories[{c_index}]", findings)
    for e_index, exhibit in enumerate(snapshot.get("exhibits") or []):
        _check_exhibit(exhibit, f"$.exhibits[{e_index}]", findings)
    return findings


def _check_exhibit(exhibit: object, where: str, findings: list[Finding]) -> None:
    if not isinstance(exhibit, dict):
        findings.append(Finding(f"snapshot:{where}", "exhibit is not an object"))
        return
    _check_keys(exhibit, "exhibit", where, findings)
    _check_keys(exhibit.get("sections"), "sections", f"{where}.sections", findings)
    _check_keys(exhibit.get("leadImage"), "image", f"{where}.leadImage", findings)
    _check_keys(exhibit.get("primaryCategory"), "category", f"{where}.primaryCategory", findings)
    nested = (
        ("images", "image"),
        ("attachments", "attachment"),
        ("links", "link"),
        ("badges", "badge"),
        ("publicRepositories", "publicRepository"),
    )
    for list_key, kind in nested:
        for index, item in enumerate(exhibit.get(list_key) or []):
            _check_keys(item, kind, f"{where}.{list_key}[{index}]", findings)
    for index, link in enumerate(exhibit.get("links") or []):
        url = link.get("url") if isinstance(link, dict) else None
        if isinstance(url, str) and REPOSITORY_HOST.match(url):
            findings.append(Finding(f"snapshot:{where}.links[{index}].url", "repository host"))
    live_url = exhibit.get("liveUrl")
    if isinstance(live_url, str) and REPOSITORY_HOST.match(live_url):
        findings.append(Finding(f"snapshot:{where}.liveUrl", "repository host"))


# --- allow-list construction --------------------------------------------------------------


def _string_leaves(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _string_leaves(item)
    elif isinstance(value, list):
        for item in value:
            yield from _string_leaves(item)


def image_variants(width: int) -> list[str]:
    """Return the C8 variant names for an image of pixel width ``width``."""
    variants = [name for name, limit in VARIANT_WIDTHS if limit <= width]
    return variants or ["w480"]


def _variant_width(variant: str, image_width: int) -> int:
    limit = dict(VARIANT_WIDTHS)[variant]
    return min(limit, image_width)


def download_name(label: str, file_type: str) -> str:
    """Return the C9 download name for an attachment."""
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:60].strip("-")
    return f"{slug or 'download'}.{FILE_EXTENSIONS.get(file_type, 'bin')}"


def _add_image(allowed: Allowed, image: dict[str, Any]) -> None:
    ref = image.get("assetRef")
    width = image.get("width")
    height = image.get("height")
    if not isinstance(ref, str) or not isinstance(width, int) or not isinstance(height, int):
        return
    allowed.numbers.update({str(width), str(height)})
    for variant in image_variants(width):
        variant_width = _variant_width(variant, width)
        allowed.numbers.update({str(variant_width), f"{variant_width}w"})
        for image_format in IMAGE_FORMATS:
            key = f"media/{ref}/{variant}.{image_format}"
            allowed.files.add(key)
            allowed.urls.add(f"/{key}")


def _add_exhibit(allowed: Allowed, exhibit: dict[str, Any]) -> None:
    slug = exhibit.get("slug")
    if isinstance(slug, str):
        allowed.urls.update({f"/work/{slug}", f"/work/{slug}/"})
        allowed.files.add(f"work/{slug}/index.html")
    published_at = exhibit.get("publishedAt")
    if isinstance(published_at, str):
        allowed.strings.add(published_at[:10])
    images = [exhibit.get("leadImage"), *(exhibit.get("images") or [])]
    for image in images:
        if isinstance(image, dict):
            _add_image(allowed, image)
    for attachment in exhibit.get("attachments") or []:
        if isinstance(attachment, dict):
            name = download_name(str(attachment.get("label", "")), str(attachment.get("fileType")))
            key = f"files/{attachment.get('assetRef')}/{name}"
            allowed.files.add(key)
            allowed.urls.add(f"/{key}")
    for link in exhibit.get("links") or []:
        if isinstance(link, dict) and isinstance(link.get("url"), str):
            allowed.urls.add(link["url"])
    for repository in exhibit.get("publicRepositories") or []:
        if isinstance(repository, dict) and isinstance(repository.get("url"), str):
            allowed.urls.add(repository["url"])
    if isinstance(exhibit.get("liveUrl"), str):
        allowed.urls.add(exhibit["liveUrl"])


def _count_strings(snapshot: dict[str, Any]) -> set[str]:
    """Decimal counts the pages show: published exhibits in all and per category (C2 count)."""
    exhibits = snapshot.get("exhibits")
    counts = {str(len(exhibits))} if isinstance(exhibits, list) else set()
    for category in snapshot.get("categories") or []:
        count = category.get("count") if isinstance(category, dict) else None
        if isinstance(count, int) and not isinstance(count, bool):
            counts.add(str(count))
    return counts


def build_allowed(snapshot: dict[str, Any], vocabulary: Sequence[object]) -> Allowed:
    """Build the allow-list from the snapshot and the template vocabulary."""
    allowed = Allowed()
    snapshot_strings = set(_string_leaves(snapshot))
    # HTML text is compared after whitespace normalization, so a multi-line narrative section
    # is allowed in its normalized form too (the same characters, whitespace collapsed).
    allowed.strings.update(snapshot_strings, {_normalize(text) for text in snapshot_strings})
    allowed.strings.update(_count_strings(snapshot))
    for document in vocabulary:
        vocabulary_strings = set(_string_leaves(document))
        allowed.strings.update(vocabulary_strings)
        allowed.fragments.update(v for v in vocabulary_strings if FRAGMENT.match(v))
    allowed.urls.update({"/", "/work/"})
    allowed.files.update({"index.html", "work/index.html", "404.html", "category-404.html"})
    site = snapshot.get("site") or {}
    if isinstance(site.get("githubProfileUrl"), str):
        allowed.urls.add(site["githubProfileUrl"])
    if isinstance(site.get("contactEmail"), str):
        allowed.urls.add(f"mailto:{site['contactEmail']}")
    for category in snapshot.get("categories") or []:
        if isinstance(category, dict) and isinstance(category.get("slug"), str):
            allowed.urls.add(f"/category/{category['slug']}")
            allowed.files.add(f"category/{category['slug']}/index.html")
    for exhibit in snapshot.get("exhibits") or []:
        if isinstance(exhibit, dict):
            _add_exhibit(allowed, exhibit)
    return allowed


# --- release checks ----------------------------------------------------------------------


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _value_reason(value: str) -> str:
    if REPOSITORY_HOST.search(value):
        return "repository host not derived from the snapshot"
    return "not derived from the snapshot, the vocabulary or the static assets"


class _HtmlScanner(HTMLParser):
    def __init__(self, location: str, allowed: Allowed) -> None:
        super().__init__(convert_charrefs=True)
        self.location = location
        self.allowed = allowed
        self.findings: list[Finding] = []
        self._open_script = False

    def _flag(self, what: str, reason: str) -> None:
        self.findings.append(Finding(f"{self.location} [{what}]", reason))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "style":
            self._flag("<style>", "inline style element")
        if tag == "script":
            self._open_script = True
            sources = [value for name, value in attrs if name == "src"]
            if not sources:
                self._flag("<script>", "inline script")
        for name, value in attrs:
            self._check_attribute(tag, name, value)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._open_script = False

    def _check_attribute(self, tag: str, name: str, value: str | None) -> None:
        where = f"<{tag} {name}>"
        if name == "style" or name.startswith("on"):
            self._flag(where, "inline style or event handler attribute")
            return
        if value is None or value == "":
            return
        if name in URL_ATTRIBUTES:
            if value not in self.allowed.urls and value not in self.allowed.fragments:
                self._flag(f"{where}={value!r}", _value_reason(value))
        elif name == "srcset":
            self._check_srcset(where, value)
        elif name in NUMBER_ATTRIBUTES:
            if value not in self.allowed.numbers:
                self._flag(f"{where}={value!r}", "dimension not derived from the snapshot")
        elif value not in self.allowed.strings:
            self._flag(f"{where}={value!r}", _value_reason(value))

    def _check_srcset(self, where: str, value: str) -> None:
        for candidate in value.split(","):
            parts = candidate.split()
            if not parts:
                continue
            url, descriptors = parts[0], parts[1:]
            if url not in self.allowed.urls:
                self._flag(f"{where}={url!r}", _value_reason(url))
            for descriptor in descriptors:
                if descriptor not in self.allowed.numbers:
                    self._flag(
                        f"{where}={descriptor!r}", "descriptor not derived from the snapshot"
                    )

    def handle_data(self, data: str) -> None:
        text = _normalize(data)
        if not text:
            return
        if self._open_script:
            self._flag("<script>", "inline script content")
            return
        if text not in self.allowed.strings:
            self._flag(f"text {text[:80]!r}", _value_reason(text))

    def handle_comment(self, data: str) -> None:
        self._flag("<!-- -->", "HTML comment")

    def handle_decl(self, decl: str) -> None:
        if decl.strip().lower() != "doctype html":
            self._flag(f"<!{decl}>", "unexpected declaration")

    def handle_pi(self, data: str) -> None:
        self._flag("<?>", "processing instruction")

    def unknown_decl(self, data: str) -> None:
        # CDATA sections and conditional or marked sections: their text is not scanned as
        # text, so they are refused outright.
        self._flag(f"<![{data[:40]}", "CDATA or unknown declaration")


def scan_html(location: str, text: str, allowed: Allowed) -> list[Finding]:
    """Check every text node and attribute value of one HTML document."""
    scanner = _HtmlScanner(location, allowed)
    scanner.feed(text)
    scanner.close()
    return scanner.findings


def scan_json(location: str, document: object, allowed: Allowed) -> list[Finding]:
    """Check every key and string value of one JSON document."""
    findings: list[Finding] = []
    stack: list[object] = [document]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for key, value in item.items():
                if key not in allowed.strings:
                    findings.append(Finding(f"{location} [key {key!r}]", _value_reason(key)))
                stack.append(value)
        elif isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, str) and item not in allowed.strings | allowed.urls:
            findings.append(Finding(f"{location} [value {item[:80]!r}]", _value_reason(item)))
    return findings


def _image_type_ok(extension: str, data: bytes) -> bool:
    if extension == "jpg":
        return data.startswith(b"\xff\xd8\xff")
    if extension == "webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False


def _check_static_asset(location: str, name: str, data: bytes, static_dir: Path) -> list[Finding]:
    """Every asset must be byte-identical to its source and carry that source's hash."""
    match = STATIC_ASSET_NAME.match(name)
    if not match:
        return [Finding(location, "static asset name is not '<name>.<hash>.<ext>'")]
    source = static_dir / f"{match['stem']}.{match['ext']}"
    if not source.is_file():
        return [Finding(location, f"no static asset source {source.name} in {static_dir}")]
    if source.read_bytes() != data:
        return [Finding(location, "static asset differs from its source")]
    if not hashlib.sha256(data).hexdigest().startswith(match["hash"]):
        return [Finding(location, "static asset hash does not match its content")]
    return []


def _check_authorized_bytes(
    location: str, key: str, data: bytes, digests: Mapping[str, str]
) -> list[Finding]:
    """R3: a published binary must be exactly the authorized derivative for its key."""
    expected = digests.get(key)
    if expected is None:
        return [Finding(location, "no authorized derivative digest for this file")]
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        return [
            Finding(
                location,
                f"bytes differ from the authorized derivative (sha256 {actual[:12]}..., "
                f"authorized {expected[:12]}...)",
            )
        ]
    return []


def scan_file(
    release: Path,
    path: Path,
    allowed: Allowed,
    static_dir: Path,
    digests: Mapping[str, str] | None = None,
) -> list[Finding]:
    """Check one file of the release: its name, then its content by type.

    ``digests`` maps release keys to the SHA-256 of the authorized bytes; without it no
    binary file is authorized (fail closed).
    """
    key = path.relative_to(release).as_posix()
    location = key
    data = path.read_bytes()
    if key.startswith("assets/") and key.count("/") == 1:
        return _check_static_asset(location, key.split("/", 1)[1], data, static_dir)
    findings: list[Finding] = []
    if key not in allowed.files:
        findings.append(Finding(location, "file name not derived from the snapshot"))
    extension = path.suffix.lower().lstrip(".")
    if key.startswith(BINARY_PREFIXES):
        findings.extend(_check_authorized_bytes(location, key, data, digests or {}))
    if extension == "html":
        findings.extend(scan_html(location, data.decode("utf-8", errors="replace"), allowed))
    elif extension == "json":
        try:
            findings.extend(scan_json(location, json.loads(data), allowed))
        except json.JSONDecodeError:
            findings.append(Finding(location, "invalid JSON"))
    elif extension in IMAGE_FORMATS:
        if not _image_type_ok(extension, data):
            findings.append(Finding(location, f"content is not a {extension} image"))
        if EXIF_MARKER in data:
            findings.append(Finding(location, "image carries EXIF metadata"))
    elif not key.startswith("files/"):
        findings.append(Finding(location, f"unexpected file type '.{extension}'"))
    return findings


def scan_release(
    release: Path,
    snapshot: dict[str, Any],
    vocabulary: Sequence[object],
    static_dir: Path,
    digests: Mapping[str, str] | None = None,
) -> tuple[int, list[Finding]]:
    """Scan a release folder; return (files scanned, findings)."""
    findings = check_snapshot(snapshot)
    allowed = build_allowed(snapshot, vocabulary)
    files = sorted(p for p in release.rglob("*") if p.is_file())
    # Pages may reference the release's own static assets; each asset file is itself checked
    # against its name pattern and against its source in the static directory.
    assets_dir = release / "assets"
    if assets_dir.is_dir():
        allowed.urls.update(f"/assets/{p.name}" for p in assets_dir.iterdir() if p.is_file())
    for path in files:
        findings.extend(scan_file(release, path, allowed, static_dir, digests))
    return len(files), findings


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Public-output allow-list scan (AC0.9).")
    parser.add_argument("--release", required=True, help="the release folder to scan")
    parser.add_argument(
        "--snapshot", required=True, help="the C2 snapshot JSON it was rendered from"
    )
    parser.add_argument(
        "--vocabulary",
        action="append",
        default=[],
        help="JSON file of the renderer's fixed template strings (repeatable)",
    )
    parser.add_argument(
        "--static-dir",
        required=True,
        help="directory holding the static asset sources; every assets/ file is compared to it",
    )
    parser.add_argument(
        "--media-digests",
        required=True,
        help="trusted SHA-256 manifest of the authorized media and file derivatives",
    )
    args = parser.parse_args(argv)
    release = Path(args.release)
    if not release.is_dir():
        print(f"scan_output: release folder {release} not found", file=sys.stderr)
        return 2
    try:
        snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
        vocabulary = [json.loads(Path(v).read_text(encoding="utf-8")) for v in args.vocabulary]
    except (OSError, json.JSONDecodeError) as error:
        print(f"scan_output: cannot read input ({error})", file=sys.stderr)
        return 2
    if not isinstance(snapshot, dict):
        print("scan_output: the snapshot is not a JSON object", file=sys.stderr)
        return 2
    static_dir = Path(args.static_dir)
    if not static_dir.is_dir():
        print(f"scan_output: static directory {static_dir} not found", file=sys.stderr)
        return 2
    try:
        digests = load_media_digests(Path(args.media_digests))
    except DigestManifestError as error:
        print(f"scan_output: {error}", file=sys.stderr)
        return 2
    scanned, findings = scan_release(release, snapshot, vocabulary, static_dir, digests)
    if scanned == 0:
        print("scan_output: FAIL - the release folder is empty", file=sys.stderr)
        return 1
    if findings:
        print(f"scan_output: FAIL - {len(findings)} finding(s):", file=sys.stderr)
        for finding in findings:
            print(f"  {finding.location}: {finding.reason}", file=sys.stderr)
        return 1
    print(f"scan_output: OK - {scanned} file(s) scanned; only allow-listed content found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
