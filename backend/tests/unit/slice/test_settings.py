"""Settings tests (Step 13; AC0.1a, BR1.3, NFR1.2)."""

from __future__ import annotations

from typing import Any

import pytest
from portfolio_api.settings import ConfigurationError, is_local_class_issuer, load_settings

BASE_ENV: dict[str, str] = {
    "AUTH_ISSUER": "https://issuer.test.example/",
    "AUTH_AUDIENCE": "portfolio-studio-api",
    "OWNER_SUBJECT": "owner-subject",
    "MONGO_URI": "mongodb://db.test.example:27017/?replicaSet=rs0",
    "SITE_DIR": "/site",
    "FIXTURE_DIR": "/app/fixtures",
    "RENDERER_COMMAND": "node /app/renderer/cli.mjs",
    "RENDERER_ASSETS_DIR": "/app/renderer/assets",
    "SITE_OWNER_NAME": "Placeholder Owner",
    "SITE_GITHUB_URL": "https://github.com/example",
}


def _env(**overrides: Any) -> dict[str, str]:
    env = {**BASE_ENV, **overrides}
    return {key: value for key, value in env.items() if value is not None}


@pytest.mark.parametrize(
    "issuer",
    [
        "http://issuer.test.example",
        "https://fake-idp.invalid",
        "https://host.local",
        "https://localhost:9000",
        "https://studio.localhost",
        "https://fake-idp",
        "https://127.0.0.1",
        "https://10.0.0.5",
        "https://[::1]",
        "https://169.254.1.1",
        "not a url",
    ],
)
def test_local_class_issuers(issuer: str) -> None:
    assert is_local_class_issuer(issuer)


@pytest.mark.parametrize(
    "issuer", ["https://issuer.test.example", "https://8.8.8.8", "https://a.b.c"]
)
def test_public_issuers_are_not_local_class(issuer: str) -> None:
    assert not is_local_class_issuer(issuer)


@pytest.mark.parametrize("app_env", [None, "", "production", "preview", "LOCAL"])
def test_ac0_1a_local_issuer_outside_local_mode_refuses_start_up(app_env: str | None) -> None:
    """AC0.1a: with a local-class issuer, anything but APP_ENV=local refuses to start."""
    with pytest.raises(ConfigurationError, match="APP_ENV=local"):
        load_settings(_env(AUTH_ISSUER="http://fake-idp.invalid", APP_ENV=app_env))


def test_ac0_1a_local_issuer_in_local_mode_is_accepted() -> None:
    settings = load_settings(_env(AUTH_ISSUER="http://fake-idp.invalid", APP_ENV="local"))
    assert settings.is_local
    assert settings.jwks_url == "http://fake-idp.invalid/.well-known/jwks.json"


def test_public_issuer_defaults() -> None:
    settings = load_settings(_env(APP_ENV="production"))
    assert settings.auth_issuer == "https://issuer.test.example"
    assert not settings.is_local
    assert settings.mongo_db == "portfolio_slice"
    assert settings.renderer_command == ("node", "/app/renderer/cli.mjs")
    assert settings.cors_origin == "http://localhost:5173"


@pytest.mark.parametrize("missing", ["AUTH_ISSUER", "AUTH_AUDIENCE", "OWNER_SUBJECT", "MONGO_URI"])
def test_required_settings(missing: str) -> None:
    with pytest.raises(ConfigurationError, match=missing):
        load_settings(_env(**{missing: None}))


def test_explicit_jwks_url_and_database_name() -> None:
    settings = load_settings(
        _env(AUTH_JWKS_URL="https://keys.test.example/jwks", MONGO_DB="other", CORS_ORIGIN="x")
    )
    assert settings.jwks_url == "https://keys.test.example/jwks"
    assert settings.mongo_db == "other"
    assert settings.cors_origin == "x"


@pytest.mark.parametrize(
    "issuer",
    [
        "https://x.invalid.",
        "https://localhost.",
        "https://studio.local.",
        "https://0x7f.1/",
        "https://0x7f000001",
        "https://2130706433",
        "https://0177.0.0.1",
        "https://127.1",
        "https://10.1",
        "https://0xa.0.0.5",
        "https://0",
        "https://[::ffff:127.0.0.1]",
        "https://[::]",
        "https://224.0.0.1",
    ],
)
def test_r04_trailing_dots_and_numeric_hosts_are_local_class(issuer: str) -> None:
    """R-04: hosts that only look public are still local-class."""
    assert is_local_class_issuer(issuer)
    with pytest.raises(ConfigurationError, match="APP_ENV=local"):
        load_settings(_env(AUTH_ISSUER=issuer, APP_ENV="production"))


@pytest.mark.parametrize(
    "issuer", ["https://8.8.8.8", "https://0x8.0x8.0x8.0x8", "https://issuer.test.example."]
)
def test_r04_public_numeric_and_trailing_dot_hosts_stay_public(issuer: str) -> None:
    assert not is_local_class_issuer(issuer)


@pytest.mark.parametrize("host", ["256.1.1.1", "1.2.3.4.5", "0x1g.example", "08.1"])
def test_r04_malformed_numeric_hosts_are_names(host: str) -> None:
    """Not a valid inet_aton form, so the dotted-name rule applies (public-looking)."""
    assert not is_local_class_issuer(f"https://{host}")


@pytest.mark.parametrize(
    "jwks_url",
    [
        "http://keys.test.example/jwks",
        "https://127.0.0.1/jwks",
        "https://0x7f.1/jwks",
        "https://keys.invalid./jwks",
        "https://10.0.0.5/jwks",
    ],
)
def test_r04_jwks_url_must_be_public_https_outside_local(jwks_url: str) -> None:
    """R-04: a public issuer cannot be paired with an http or private key-set address."""
    with pytest.raises(ConfigurationError, match="AUTH_JWKS_URL"):
        load_settings(_env(AUTH_JWKS_URL=jwks_url, APP_ENV="production"))
    local = load_settings(_env(AUTH_JWKS_URL=jwks_url, APP_ENV="local"))
    assert local.jwks_url == jwks_url


def test_reads_the_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _env(APP_ENV="production").items():
        monkeypatch.setenv(key, value)
    assert load_settings().owner_subject == "owner-subject"
