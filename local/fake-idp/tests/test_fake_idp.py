"""LOCAL-ONLY FAKE identity provider tests (Step 14; NFR1.3, BR1.2).

The key is never written to disk; tokens verify against the published JWKS.
"""

from __future__ import annotations

import builtins
import os
from pathlib import Path
from typing import Any

import jwt
import pytest
from fake_idp import MARKER
from fake_idp.app import FakeIdpConfigurationError, create_app
from fastapi.testclient import TestClient

ENV = {
    "AUTH_ISSUER": "http://fake-idp.invalid",
    "AUTH_AUDIENCE": "portfolio-studio-api",
    "OWNER_SUBJECT": "local-owner",
    "FAKE_IDP_TEST_SUBJECTS": "local-other, ",
}
SOURCE = Path(__file__).resolve().parents[1] / "fake_idp"
# The issuer answers only allow-listed Host names (SL-3); TestClient's default is "testserver".
BASE = "http://localhost"


def test_marker_is_in_every_source_file() -> None:
    """NFR1.3: the fake carries the marker the S0 guard looks for."""
    assert MARKER == "AIDLC_LOCAL_ONLY_FAKE_IDP"
    for path in SOURCE.glob("*.py"):
        assert MARKER in path.read_text(encoding="utf-8"), path.name


def test_jwks_publishes_only_the_public_key() -> None:
    keys = TestClient(create_app(ENV), base_url=BASE).get("/.well-known/jwks.json").json()["keys"]
    assert len(keys) == 1
    assert keys[0]["kty"] == "EC"
    assert keys[0]["alg"] == "ES256"
    assert "d" not in keys[0]


def test_owner_token_verifies_against_the_jwks() -> None:
    client = TestClient(create_app(ENV), base_url=BASE)
    body = client.get("/token", params={"sub": "local-owner"}).json()
    key_set = jwt.PyJWKSet.from_dict(client.get("/.well-known/jwks.json").json())
    kid = jwt.get_unverified_header(body["access_token"])["kid"]
    claims = jwt.decode(
        body["access_token"],
        key=key_set[kid].key,
        algorithms=["ES256"],
        audience=ENV["AUTH_AUDIENCE"],
        issuer=ENV["AUTH_ISSUER"],
    )
    assert claims["sub"] == "local-owner"
    assert claims["exp"] - claims["iat"] == 600
    assert body["token_type"] == "Bearer"


def test_test_subjects_are_served_and_unknown_subjects_refused() -> None:
    client = TestClient(create_app(ENV), base_url=BASE)
    assert client.get("/token", params={"sub": "local-other"}).status_code == 200
    assert client.get("/token", params={"sub": "intruder"}).status_code == 400
    assert client.get("/token").status_code == 422


def test_each_start_generates_a_new_key() -> None:
    first = (
        TestClient(create_app(ENV), base_url=BASE).get("/.well-known/jwks.json").json()["keys"][0]
    )
    second = (
        TestClient(create_app(ENV), base_url=BASE).get("/.well-known/jwks.json").json()["keys"][0]
    )
    assert first["kid"] != second["kid"]


def test_the_key_is_never_written_to_disk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """NFR1.3: start-up and token issuance open no file for writing."""
    monkeypatch.chdir(tmp_path)
    real_open = builtins.open
    real_os_open = os.open
    writes: list[str] = []

    def guarded_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if any(flag in mode for flag in "wax+"):
            writes.append(str(file))
        return real_open(file, mode, *args, **kwargs)

    def guarded_os_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT):
            writes.append(str(path))
        return real_os_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(os, "open", guarded_os_open)
    client = TestClient(create_app(ENV), base_url=BASE)
    assert client.get("/token", params={"sub": "local-owner"}).status_code == 200
    monkeypatch.undo()
    assert writes == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("missing", ["AUTH_ISSUER", "AUTH_AUDIENCE", "OWNER_SUBJECT"])
def test_refuses_to_start_without_local_configuration(missing: str) -> None:
    env = {key: value for key, value in ENV.items() if key != missing}
    with pytest.raises(FakeIdpConfigurationError, match=missing):
        create_app(env)


def test_health_and_cors_for_the_studio_origin() -> None:
    client = TestClient(create_app(ENV), base_url=BASE)
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    other = client.get("/health", headers={"Origin": "http://evil.test.example"})
    assert "access-control-allow-origin" not in other.headers
    assert client.get("/docs").status_code == 404


@pytest.mark.parametrize(
    "host",
    ["localhost", "localhost:19000", "127.0.0.1", "127.0.0.1:52807", "fake-idp.invalid"],
)
def test_sl_3_allowed_hosts_are_served(host: str) -> None:
    """SL-3: the loopback names and the issuer's network alias, on any port."""
    client = TestClient(create_app(ENV), base_url=BASE)
    assert client.get("/health", headers={"Host": host}).status_code == 200
    token = client.get("/token", params={"sub": "local-owner"}, headers={"Host": host})
    assert token.status_code == 200


@pytest.mark.parametrize(
    "host",
    ["evil.example", "rebind.attacker.test:9000", "fake-idp", "192.168.1.5", "testserver"],
)
def test_sl_3_a_foreign_host_gets_400_and_no_token(host: str) -> None:
    """SL-3: a DNS-rebinding page sends its own name as Host; it gets 400 and no token."""
    client = TestClient(create_app(ENV), base_url=BASE)
    for path in ("/health", "/.well-known/jwks.json", "/token?sub=local-owner"):
        response = client.get(path, headers={"Host": host})
        assert response.status_code == 400, (host, path)
        assert "access_token" not in response.text
