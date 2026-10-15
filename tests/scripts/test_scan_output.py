"""Tests for scripts/scan_output.py (AC0.9, BR3.2, BR3.3, NFR2.1; Codex review R3)."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import scan_output as scan

REF = "ast_PlaceholderAsset0001"
CSS = b"body{margin:0}\n"
CSS_HASH = hashlib.sha256(CSS).hexdigest()[:10]
VOCABULARY: dict[str, Any] = {
    "text": {"allWork": "All work", "notFound": "This exhibit isn't on display"},
    "attributes": ["en", "utf-8", "stylesheet", "image/webp", "exhibit"],
}
SNAPSHOT: dict[str, Any] = {
    "schemaVersion": "1.0",
    "generation": 1,
    "site": {
        "ownerName": "Placeholder Owner",
        "githubProfileUrl": "https://github.com/example",
        "contactEmail": None,
    },
    "exhibits": [
        {
            "slug": "placeholder-project",
            "title": "Placeholder <project> & co",
            "summary": "Placeholder summary text.",
            "sections": {},
            "leadImage": {
                "assetRef": REF,
                "altText": "Placeholder image",
                "width": 400,
                "height": 300,
            },
            "images": [],
            "attachments": [],
            "links": [],
            "badges": [],
            "publicRepositories": [],
            "featured": False,
            "publishedAt": "2026-10-11T12:00:00Z",
        }
    ],
    "featuredOrder": [],
    "categories": [],
}
EXHIBIT_HTML = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<title>Placeholder &lt;project&gt; &amp; co</title>
<link rel="stylesheet" href="/assets/site.{CSS_HASH}.css"/></head>
<body class="exhibit"><a href="/work/">All work</a><h1>Placeholder &lt;project&gt; &amp; co</h1>
<p>Placeholder summary text.</p><time datetime="2026-10-11T12:00:00Z">2026-10-11</time>
<picture><source type="image/webp" srcset="/media/{REF}/w480.webp 400w"/>
<img src="/media/{REF}/w480.jpg" alt="Placeholder image" width="400" height="300"/></picture>
<a href="https://github.com/example">Placeholder Owner</a></body></html>"""
# A structurally plausible JPEG: SOI, APP0 (JFIF), SOS, entropy-coded "pixels", EOI.
JPEG_HEAD = b"\xff\xd8"
JPEG_APP0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
JPEG_SOS = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
JPEG_PIXELS = bytes(range(16, 80))
JPEG_EOI = b"\xff\xd9"
JPEG = JPEG_HEAD + JPEG_APP0 + JPEG_SOS + JPEG_PIXELS + JPEG_EOI
WEBP = b"RIFF\x10\x00\x00\x00WEBPVP8 rest"
JPEG_KEY = f"media/{REF}/w480.jpg"
WEBP_KEY = f"media/{REF}/w480.webp"
DIGESTS = {
    JPEG_KEY: hashlib.sha256(JPEG).hexdigest(),
    WEBP_KEY: hashlib.sha256(WEBP).hexdigest(),
}


def _write(root: Path, relative: str, data: str | bytes) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)


def _manifest(path: Path, derivatives: object, **fields: object) -> Path:
    document = {"version": 1, "algorithm": "sha256", "derivatives": derivatives, **fields}
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


@pytest.fixture
def release(tmp_path: Path) -> Path:
    root = tmp_path / "release"
    _write(
        root,
        "index.html",
        '<!DOCTYPE html><html lang="en"><body><a href="/work/">All work</a></body></html>',
    )
    _write(root, "work/placeholder-project/index.html", EXHIBIT_HTML)
    _write(
        root,
        "404.html",
        "<!DOCTYPE html><html><body><p>This exhibit isn&#x27;t on display</p></body></html>",
    )
    _write(root, f"media/{REF}/w480.jpg", JPEG)
    _write(root, f"media/{REF}/w480.webp", WEBP)
    _write(root, f"assets/site.{CSS_HASH}.css", CSS)
    return root


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "static"
    _write(directory, "site.css", CSS)
    return directory


def _reasons(
    release: Path,
    snapshot: dict[str, Any] | None = None,
    static: Path | None = None,
    digests: dict[str, str] | None = None,
) -> list[str]:
    """Scan with the static sources next to the release (written by the static_dir fixture
    or created here), since --static-dir is required, and the authorized digests."""
    source_dir = static or release.parent / "static"
    if not (source_dir / "site.css").is_file():
        _write(source_dir, "site.css", CSS)
    _, findings = scan.scan_release(
        release,
        snapshot or SNAPSHOT,
        [VOCABULARY],
        source_dir,
        DIGESTS if digests is None else digests,
    )
    return [f"{f.location}: {f.reason}" for f in findings]


def test_ac0_9_clean_release_passes(release: Path, static_dir: Path) -> None:
    """AC0.9: a release rendered only from C2 fields, the vocabulary and assets passes."""
    assert _reasons(release, static=static_dir) == []


def test_ac0_9_extra_snapshot_field_fails(release: Path) -> None:
    """AC0.9: a field outside the C2 allow-list is refused even if it is not rendered."""
    snapshot = copy.deepcopy(SNAPSHOT)
    snapshot["exhibits"][0]["privateNotes"] = "internal"
    snapshot["site"]["ownerEmail"] = "owner@example.invalid"
    reasons = _reasons(release, snapshot)
    assert "snapshot:$.exhibits[0].privateNotes: field not in the C2 allow-list" in reasons
    assert "snapshot:$.site.ownerEmail: field not in the C2 allow-list" in reasons


def test_ac0_9_private_string_in_html_fails(release: Path) -> None:
    """AC0.9: text that no C2 field supplies is a leak."""
    _write(
        release, "index.html", "<!DOCTYPE html><html><body><p>Private draft note</p></body></html>"
    )
    reasons = _reasons(release)
    assert any("Private draft note" in r and "not derived from the snapshot" in r for r in reasons)


def test_ac0_9_repository_host_fails(release: Path) -> None:
    """AC0.9: a repository URL that the snapshot does not list publicly is refused."""
    html = '<!DOCTYPE html><html><body><a href="https://github.com/example/private-repo">x</a></body></html>'
    _write(release, "index.html", html)
    reasons = _reasons(release)
    assert any("repository host not derived from the snapshot" in r for r in reasons)


def test_repository_host_in_snapshot_links_fails(release: Path) -> None:
    snapshot = copy.deepcopy(SNAPSHOT)
    snapshot["exhibits"][0]["links"] = [
        {"kind": "demo", "label": "Code", "url": "https://gitlab.com/x/y"}
    ]
    snapshot["exhibits"][0]["liveUrl"] = "https://raw.githubusercontent.com/x/y/main/a"
    reasons = _reasons(release, snapshot)
    assert "snapshot:$.exhibits[0].links[0].url: repository host" in reasons
    assert "snapshot:$.exhibits[0].liveUrl: repository host" in reasons


def test_unexpected_file_names_fail(release: Path) -> None:
    _write(release, "work/secret-project/index.html", "<!DOCTYPE html><html></html>")
    _write(release, "notes.txt", "x")
    reasons = _reasons(release)
    assert "work/secret-project/index.html: file name not derived from the snapshot" in reasons
    assert "notes.txt: unexpected file type '.txt'" in reasons


def test_inline_script_style_and_comments_fail(release: Path) -> None:
    html = (
        "<!DOCTYPE html><html><body><!-- note --><script>alert(1)</script>"
        '<style>p{}</style><p style="color:red" onclick="x()">All work</p></body></html>'
    )
    _write(release, "index.html", html)
    reasons = " | ".join(_reasons(release))
    for expected in (
        "HTML comment",
        "inline script",
        "inline style element",
        "inline style or event",
    ):
        assert expected in reasons


def test_bad_dimensions_and_srcset_fail(release: Path) -> None:
    html = EXHIBIT_HTML.replace('width="400"', 'width="999"').replace("400w", "1600w")
    html = html.replace(f"/media/{REF}/w480.webp", "/media/ast_Other0000000000000/w480.webp")
    _write(release, "work/placeholder-project/index.html", html)
    reasons = " | ".join(_reasons(release))
    assert "dimension not derived" in reasons
    assert "descriptor not derived" in reasons
    assert "ast_Other" in reasons


def test_image_content_is_checked(release: Path) -> None:
    _write(release, f"media/{REF}/w480.jpg", b"\xff\xd8\xff\xe1\x00\x10Exif\x00\x00metadata")
    _write(release, f"media/{REF}/w480.webp", b"not an image")
    reasons = _reasons(release)
    assert f"media/{REF}/w480.jpg: image carries EXIF metadata" in reasons
    assert f"media/{REF}/w480.webp: content is not a webp image" in reasons


def test_static_assets_are_checked(release: Path, static_dir: Path) -> None:
    _write(release, "assets/site.0000000000.css", CSS)
    _write(release, "assets/other.1234567890.css", b"x")
    _write(release, "assets/Bad Name.css", b"x")
    reasons = _reasons(release, static=static_dir)
    assert "assets/site.0000000000.css: static asset hash does not match its content" in reasons
    assert any(r.startswith("assets/other.1234567890.css: no static asset source") for r in reasons)
    assert "assets/Bad Name.css: static asset name is not '<name>.<hash>.<ext>'" in reasons
    _write(static_dir, "site.css", b"changed")
    assert any("differs from its source" in r for r in _reasons(release, static=static_dir))


def test_json_files_are_scanned(release: Path) -> None:
    snapshot = copy.deepcopy(SNAPSHOT)
    _write(release, "work/index.html", "<!DOCTYPE html><html></html>")
    _write(release, "index.json", json.dumps({"title": "Placeholder summary text."}))
    _write(release, "work/broken.json", "{")
    reasons = _reasons(release, snapshot)
    assert any("key 'title'" in r for r in reasons)
    assert "work/broken.json: invalid JSON" in reasons


def test_unexpected_declaration_and_pi_fail(release: Path) -> None:
    _write(release, "index.html", '<!DOCTYPE svg><?xml version="1.0"?><html></html>')
    reasons = " | ".join(_reasons(release))
    assert "unexpected declaration" in reasons
    assert "processing instruction" in reasons


def test_attachments_and_categories_extend_the_allow_list() -> None:
    snapshot = copy.deepcopy(SNAPSHOT)
    snapshot["exhibits"][0]["attachments"] = [
        {"assetRef": REF, "label": "Plans & Drawings!", "fileType": "PDF", "byteSize": 10}
    ]
    snapshot["exhibits"][0]["publicRepositories"] = [
        {"name": "r", "url": "https://github.com/example/r"}
    ]
    snapshot["categories"] = [{"slug": "software", "name": "Software", "position": 0, "count": 1}]
    snapshot["site"]["contactEmail"] = "owner@example.invalid"
    allowed = scan.build_allowed(snapshot, [VOCABULARY])
    assert f"/files/{REF}/plans-drawings.pdf" in allowed.urls
    assert "https://github.com/example/r" in allowed.urls
    assert "/category/software" in allowed.urls
    assert "mailto:owner@example.invalid" in allowed.urls
    assert scan.download_name("!!!", "ZIP") == "download.zip"
    assert scan.image_variants(2000) == ["w480", "w960", "w1600"]


def test_main_exit_codes(release: Path, tmp_path: Path, static_dir: Path) -> None:
    snapshot_file = tmp_path / "snapshot.json"
    snapshot_file.write_text(json.dumps(SNAPSHOT), encoding="utf-8")
    vocabulary_file = tmp_path / "vocabulary.json"
    vocabulary_file.write_text(json.dumps(VOCABULARY), encoding="utf-8")
    manifest = _manifest(tmp_path / "digests.json", DIGESTS)
    static = ["--static-dir", str(static_dir), "--media-digests", str(manifest)]
    base = ["--snapshot", str(snapshot_file), "--vocabulary", str(vocabulary_file), *static]
    assert scan.main(["--release", str(release), *base]) == 0
    empty = tmp_path / "empty"
    empty.mkdir()
    assert scan.main(["--release", str(empty), *base]) == 1
    assert scan.main(["--release", str(tmp_path / "missing"), *base]) == 2
    _write(release, "index.html", "<p>leak</p>")
    assert scan.main(["--release", str(release), *base]) == 1
    (tmp_path / "list.json").write_text("[]", encoding="utf-8")
    listing = ["--snapshot", str(tmp_path / "list.json"), *static]
    assert scan.main(["--release", str(release), *listing]) == 2
    missing = ["--snapshot", str(tmp_path / "nope.json"), *static]
    assert scan.main(["--release", str(release), *missing]) == 2
    no_static = [
        "--snapshot",
        str(snapshot_file),
        "--static-dir",
        str(tmp_path / "nowhere"),
        "--media-digests",
        str(manifest),
    ]
    assert scan.main(["--release", str(release), *no_static]) == 2


def test_r05_static_dir_is_required(release: Path, tmp_path: Path) -> None:
    """R-05: without --static-dir no asset could be compared to its source, so it is refused."""
    snapshot_file = tmp_path / "snapshot.json"
    snapshot_file.write_text(json.dumps(SNAPSHOT), encoding="utf-8")
    with pytest.raises(SystemExit) as exit_info:
        scan.main(["--release", str(release), "--snapshot", str(snapshot_file)])
    assert exit_info.value.code == 2


def test_r05_a_script_posing_as_a_hashed_asset_fails(release: Path, static_dir: Path) -> None:
    """R-05: an assets/name.hash.js file with no matching source is a finding."""
    _write(release, "assets/site.0123456789abcdef.js", b"alert(document.cookie)")
    reasons = _reasons(release, static=static_dir)
    assert any(
        r.startswith("assets/site.0123456789abcdef.js: no static asset source") for r in reasons
    )


@pytest.mark.parametrize(
    "markup",
    [
        "<![CDATA[Private draft note]]>",
        "<![if !IE]>Private draft note<![endif]>",
    ],
)
def test_r05_cdata_and_unknown_declarations_fail(release: Path, markup: str) -> None:
    """R-05: text hidden in CDATA or a marked section is refused.

    Depending on the Python version, the parser reports a conditional marked section as an
    unknown declaration or as a bogus comment; both are findings.
    """
    _write(release, "index.html", f"<!DOCTYPE html><html><body>{markup}</body></html>")
    reasons = _reasons(release)
    assert any("CDATA or unknown declaration" in r or "HTML comment" in r for r in reasons)
    if markup.startswith("<![CDATA["):
        assert any("CDATA or unknown declaration" in r for r in reasons)


# --- R3: every published image must equal an authorized derivative ---------------------------


def _scan_one(release: Path, key: str, digests: dict[str, str] | None = DIGESTS) -> list[str]:
    """Codex's call: scan_file on one release path that the allow-list names."""
    allowed = scan.Allowed(files={key})
    findings = scan.scan_file(release, release / key, allowed, release.parent / "static", digests)
    return [f.reason for f in findings]


def _differs(reasons: list[str]) -> bool:
    return any(r.startswith("bytes differ from the authorized derivative") for r in reasons)


def test_r3_clean_authorized_derivatives_pass(release: Path) -> None:
    assert _scan_one(release, JPEG_KEY) == []
    assert _scan_one(release, WEBP_KEY) == []


def test_r3_appended_private_note_is_a_finding(release: Path) -> None:
    """R3 (Codex reproduction, synthetic JPEG): bytes appended to an allow-listed image."""
    _write(release, JPEG_KEY, JPEG + b"PRIVATE_DRAFT_NOTE=not-authorized-for-publication")
    reasons = _scan_one(release, JPEG_KEY)
    assert _differs(reasons)
    assert "image carries EXIF metadata" not in reasons, "the old checks alone saw nothing"


def test_r3_changed_pixels_are_a_finding(release: Path) -> None:
    pixels = bytearray(JPEG_PIXELS)
    pixels[10] ^= 0x01
    _write(release, JPEG_KEY, JPEG_HEAD + JPEG_APP0 + JPEG_SOS + bytes(pixels) + JPEG_EOI)
    assert _differs(_scan_one(release, JPEG_KEY))


def test_r3_non_exif_metadata_is_a_finding(release: Path) -> None:
    """A JPEG COM segment (not EXIF) carrying text is refused."""
    comment = b"private draft"
    segment = b"\xff\xfe" + (len(comment) + 2).to_bytes(2, "big") + comment
    _write(release, JPEG_KEY, JPEG_HEAD + segment + JPEG_APP0 + JPEG_SOS + JPEG_PIXELS + JPEG_EOI)
    assert _differs(_scan_one(release, JPEG_KEY))


def test_r3_trailing_data_after_the_end_marker_is_a_finding(release: Path) -> None:
    _write(release, WEBP_KEY, WEBP + b"\x00trailing")
    assert _differs(_scan_one(release, WEBP_KEY))


def test_r3_a_media_file_without_a_digest_entry_is_a_finding(release: Path) -> None:
    only_webp = {WEBP_KEY: DIGESTS[WEBP_KEY]}
    assert _scan_one(release, JPEG_KEY, only_webp) == [
        "no authorized derivative digest for this file"
    ]
    reasons = _reasons(release, digests=only_webp)
    assert f"{JPEG_KEY}: no authorized derivative digest for this file" in reasons


def test_r3_without_a_manifest_no_media_is_authorized(release: Path) -> None:
    """Fail closed: scan_file called without digests (as in Codex's call) authorizes nothing."""
    assert _scan_one(release, JPEG_KEY, None) == ["no authorized derivative digest for this file"]


def test_r3_a_digest_for_another_key_does_not_authorize_the_file(release: Path) -> None:
    """The digest must be for the file's exact key: a copy under another name is refused."""
    _write(release, f"media/{REF}/w960.jpg", JPEG)
    assert _scan_one(release, f"media/{REF}/w960.jpg") == [
        "no authorized derivative digest for this file"
    ]


def test_r3_downloads_need_an_authorized_digest_too(release: Path) -> None:
    key = f"files/{REF}/plans.pdf"
    _write(release, key, b"%PDF-1.7 placeholder")
    assert _scan_one(release, key) == ["no authorized derivative digest for this file"]
    digest = hashlib.sha256(b"%PDF-1.7 placeholder").hexdigest()
    assert _scan_one(release, key, {key: digest}) == []


def test_r3_the_manifest_is_validated(tmp_path: Path) -> None:
    good = _manifest(tmp_path / "good.json", DIGESTS)
    assert scan.load_media_digests(good) == DIGESTS
    bad_documents = [
        _manifest(tmp_path / "version.json", DIGESTS, version=2),
        _manifest(tmp_path / "algorithm.json", DIGESTS, algorithm="md5"),
        _manifest(tmp_path / "list.json", []),
        _manifest(tmp_path / "key.json", {"index.html": "a" * 64}),
        _manifest(tmp_path / "value.json", {JPEG_KEY: "A" * 64}),
        _manifest(tmp_path / "short.json", {JPEG_KEY: "abc"}),
    ]
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    for path in [*bad_documents, tmp_path / "broken.json", tmp_path / "missing.json"]:
        with pytest.raises(scan.DigestManifestError):
            scan.load_media_digests(path)


def test_r3_main_requires_and_checks_the_manifest(
    release: Path, tmp_path: Path, static_dir: Path
) -> None:
    snapshot_file = tmp_path / "snapshot.json"
    snapshot_file.write_text(json.dumps(SNAPSHOT), encoding="utf-8")
    vocabulary_file = tmp_path / "vocabulary.json"
    vocabulary_file.write_text(json.dumps(VOCABULARY), encoding="utf-8")
    base = [
        "--release",
        str(release),
        "--snapshot",
        str(snapshot_file),
        "--vocabulary",
        str(vocabulary_file),
        "--static-dir",
        str(static_dir),
    ]
    with pytest.raises(SystemExit) as exit_info:
        scan.main(base)
    assert exit_info.value.code == 2
    broken = tmp_path / "broken.json"
    broken.write_text("[]", encoding="utf-8")
    assert scan.main([*base, "--media-digests", str(broken)]) == 2
    good = _manifest(tmp_path / "digests.json", DIGESTS)
    assert scan.main([*base, "--media-digests", str(good)]) == 0
    _write(release, JPEG_KEY, JPEG + b"x")
    assert scan.main([*base, "--media-digests", str(good)]) == 1


# --- L1 public design: same-page links, counts and multi-line narrative -------------------


def _page(body: str) -> str:
    return f'<!DOCTYPE html><html lang="en"><body>{body}</body></html>'


def _allowed(snapshot: dict[str, Any] | None = None) -> scan.Allowed:
    vocabulary = {**VOCABULARY, "fragments": ["#main", "#story"]}
    return scan.build_allowed(snapshot or SNAPSHOT, [vocabulary])


def test_l1_vocabulary_fragments_are_allowed_links() -> None:
    """The skip link and in-page navigation may target fragments the vocabulary spells."""
    html = _page('<a href="#main">All work</a><a href="#story">All work</a>')
    assert scan.scan_html("page", html, _allowed()) == []


def test_l1_other_fragments_and_snapshot_strings_are_not_links() -> None:
    """A fragment the vocabulary does not spell is refused, even if the snapshot has it."""
    snapshot = copy.deepcopy(SNAPSHOT)
    snapshot["exhibits"][0]["summary"] = "#evil"
    html = _page('<a href="#evil">All work</a><a href="#Main">All work</a>')
    reasons = [f.location for f in scan.scan_html("page", html, _allowed(snapshot))]
    assert reasons == ["page [<a href>='#evil']", "page [<a href>='#Main']"]


def test_l1_counts_derived_from_the_snapshot_are_allowed() -> None:
    """The exhibit total and each C2 category count may appear as text; other numbers not."""
    snapshot = copy.deepcopy(SNAPSHOT)
    snapshot["categories"] = [{"slug": "games", "name": "Games", "position": 0, "count": 7}]
    allowed = _allowed(snapshot)
    assert scan.scan_html("page", _page("<span>1</span><span>7</span>"), allowed) == []
    findings = scan.scan_html("page", _page("<span>42</span>"), allowed)
    assert [f.location for f in findings] == ["page [text '42']"]


def test_l1_multi_line_snapshot_text_is_allowed_in_normalized_form() -> None:
    """A narrative with paragraphs is compared after whitespace normalization."""
    snapshot = copy.deepcopy(SNAPSHOT)
    snapshot["exhibits"][0]["sections"] = {"outcomes": "First line.\n\nSecond  line."}
    allowed = _allowed(snapshot)
    html = _page("<p>First line.\n\nSecond  line.</p>")
    assert scan.scan_html("page", html, allowed) == []
    assert scan.scan_html("page", _page("<p>First line. Third line.</p>"), allowed) != []
