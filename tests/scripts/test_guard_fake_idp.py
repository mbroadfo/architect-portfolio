"""Tests for scripts/guard_fake_idp.py (AC0.2, BR1.2, NFR1.3)."""

from __future__ import annotations

import io
import shutil
import tarfile
import zipfile
from pathlib import Path

import guard_fake_idp as guard
import pytest
from conftest import GUARD_FIXTURES, REPO_ROOT

# Built at run time so no file in the repository holds a private-key header.
PEM_HEADER = "-----BEGIN " + "EC PRIVATE KEY-----"
FAKE_ISSUER = "http://fake-idp.invalid"


def _write(root: Path, relative: str, content: str | bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode("utf-8") if isinstance(content, str) else content
    path.write_bytes(data)
    return path


def _root_with_dist(tmp_path: Path, content: str) -> Path:
    _write(tmp_path, "backend/dist/portfolio_api-0.0.1.txt", content)
    return tmp_path


def test_ac0_2_contaminated_fixture_fails(capsys: pytest.CaptureFixture[str]) -> None:
    """AC0.2: the shipped negative fixture (marker text, no key) fails the guard."""
    exit_code = guard.main(["--root", str(REPO_ROOT), str(GUARD_FIXTURES / "contaminated")])
    assert exit_code == 1
    assert "fake identity provider marker" in capsys.readouterr().err


def test_ac0_2_clean_fixture_passes(capsys: pytest.CaptureFixture[str]) -> None:
    """AC0.2: a clean artifact passes."""
    exit_code = guard.main(["--root", str(REPO_ROOT), str(GUARD_FIXTURES / "clean")])
    assert exit_code == 0
    assert "2 file(s) scanned" in capsys.readouterr().out


def test_zero_files_scanned_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A missing build output must not pass silently."""
    assert guard.main(["--root", str(tmp_path)]) == 1
    assert "zero files scanned" in capsys.readouterr().err


def test_scripts_and_local_are_never_scanned(tmp_path: Path) -> None:
    """The guard skips scripts/ and local/, even when they carry the marker."""
    _root_with_dist(tmp_path, "clean output")
    _write(tmp_path, "local/fake-idp/app.py", "AIDLC_LOCAL_ONLY_FAKE_IDP fake_idp")
    _write(tmp_path, "scripts/guard.py", "AIDLC_LOCAL_ONLY_FAKE_IDP")
    result = guard.run_scan(tmp_path)
    assert result.files_scanned == 1
    assert result.findings == []
    assert guard.main(["--root", str(tmp_path), "local", "scripts"]) == 1


def test_default_targets_cover_backend_and_web_dist(tmp_path: Path) -> None:
    """Default targets are backend/dist/* and every file under web/*/dist/**."""
    _write(tmp_path, "backend/dist/a.txt", "ok")
    _write(tmp_path, "web/site/dist/assets/deep/b.js", "uses fake_idp here")
    _write(tmp_path, "web/site/src/c.ts", "AIDLC_LOCAL_ONLY_FAKE_IDP")
    result = guard.run_scan(tmp_path)
    assert result.files_scanned == 2
    assert [f.reason for f in result.findings] == ["fake identity provider package name"]


def test_fake_issuer_url_is_read_from_compose_env(tmp_path: Path) -> None:
    """The issuer URL comes from local/compose.env at scan time."""
    env = f"# local only\nAPP_ENV=local\nAUTH_ISSUER={FAKE_ISSUER}\n"
    _write(tmp_path, "local/compose.env", env)
    _root_with_dist(tmp_path, f'const issuer = "{FAKE_ISSUER}/";')
    reasons = [f.reason for f in guard.run_scan(tmp_path).findings]
    assert reasons == ["fake issuer URL"]


def test_issuer_check_is_skipped_without_compose_env(tmp_path: Path) -> None:
    """Without local/compose.env there is no issuer URL to look for."""
    _root_with_dist(tmp_path, f'const issuer = "{FAKE_ISSUER}";')
    assert guard.run_scan(tmp_path).findings == []
    assert guard.read_fake_issuer(tmp_path) is None


def test_compose_env_without_issuer_key(tmp_path: Path) -> None:
    _write(tmp_path, "local/compose.env", "APP_ENV=local\nnot a pair\nAUTH_ISSUER=\n")
    assert guard.read_fake_issuer(tmp_path) is None


def test_pem_private_key_is_detected(tmp_path: Path) -> None:
    _root_with_dist(tmp_path, f"{PEM_HEADER}\nnot-a-real-key\n")
    assert [f.reason for f in guard.run_scan(tmp_path).findings] == ["PEM private key"]


def test_jwk_private_key_is_detected_and_public_jwk_passes(tmp_path: Path) -> None:
    private_jwk = '{"kty": "EC", "crv": "P-256", "x": "abc", "y": "def", "d": "' + "A" * 43 + '"}'
    _write(tmp_path, "web/site/dist/key.json", private_jwk)
    _write(tmp_path, "web/site/dist/public.json", '{"kty": "EC", "crv": "P-256", "x": "abc"}')
    findings = guard.run_scan(tmp_path).findings
    assert [(Path(f.location).name, f.reason) for f in findings] == [
        ("key.json", "JWK private key")
    ]


def test_wheel_members_are_scanned(tmp_path: Path) -> None:
    """Archives are opened: a wheel that packages fake_idp fails."""
    wheel = tmp_path / "backend" / "dist" / "portfolio_api-0.0.1-py3-none-any.whl"
    wheel.parent.mkdir(parents=True)
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("portfolio_api/__init__.py", "x = 1\n")
        archive.writestr("fake_idp/__init__.py", "")
    result = guard.run_scan(tmp_path)
    assert result.files_scanned == 3
    assert any(f.reason == "fake identity provider package name" for f in result.findings)


def test_tarball_members_are_scanned(tmp_path: Path) -> None:
    sdist = tmp_path / "backend" / "dist" / "portfolio_api-0.0.1.tar.gz"
    sdist.parent.mkdir(parents=True)
    payload = b"AIDLC_LOCAL_ONLY_FAKE_IDP"
    with tarfile.open(sdist, "w:gz") as archive:
        info = tarfile.TarInfo("portfolio_api-0.0.1/leak.txt")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    findings = guard.run_scan(tmp_path).findings
    assert [f.reason for f in findings] == ["fake identity provider marker"]


def test_nested_zip_in_wheel_is_scanned(tmp_path: Path) -> None:
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as archive:
        archive.writestr("inner.txt", "AIDLC_LOCAL_ONLY_FAKE_IDP")
    wheel = tmp_path / "backend" / "dist" / "outer.zip"
    wheel.parent.mkdir(parents=True)
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("bundle.zip", inner.getvalue())
    reasons = [f.reason for f in guard.run_scan(tmp_path).findings]
    assert "fake identity provider marker" in reasons


def test_unreadable_archive_is_a_finding(tmp_path: Path) -> None:
    _write(tmp_path, "backend/dist/broken.whl", b"not a zip file")
    findings = guard.run_scan(tmp_path).findings
    assert len(findings) == 1
    assert findings[0].reason.startswith("unreadable build output")


def test_explicit_file_target_and_missing_root(tmp_path: Path) -> None:
    target = shutil.copy(GUARD_FIXTURES / "clean" / "index.html", tmp_path / "index.html")
    assert guard.main(["--root", str(tmp_path), str(target)]) == 0
    assert guard.main(["--root", str(tmp_path / "missing")]) == 2
