"""Owner authentication tests (Step 13; AC0.1, BR1.1, NFR1.1, NFR1.4)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx
import pytest
from portfolio_api import auth
from portfolio_api.auth import AuthError, JwksClient, KeySetUnavailableError, TokenVerifier

from tests.unit.slice import tokens

JWKS_URL = f"{tokens.ISSUER}/.well-known/jwks.json"


class CountingFetcher:
    """Serves a fixed key set and counts fetches."""

    def __init__(self, document: Mapping[str, Any] | Exception) -> None:
        self.document = document
        self.calls = 0

    def __call__(self, url: str) -> Mapping[str, Any]:
        self.calls += 1
        if isinstance(self.document, Exception):
            raise self.document
        return self.document


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def ec_key() -> tokens.SigningKey:
    return tokens.ec_key()


def _verifier(fetcher: CountingFetcher, clock: FakeClock | None = None) -> TokenVerifier:
    client = JwksClient(JWKS_URL, fetch=fetcher, clock=clock or FakeClock())
    return TokenVerifier(client, tokens.ISSUER, tokens.AUDIENCE, tokens.OWNER)


def _status(verifier: TokenVerifier, token: str) -> int:
    try:
        verifier.verify(token)
    except AuthError as error:
        return error.status_code
    return 200


def test_ac0_1_owner_token_is_accepted(ec_key: tokens.SigningKey) -> None:
    """AC0.1: a valid ES256 token for the owner subject passes."""
    principal = _verifier(CountingFetcher(tokens.jwks(ec_key))).verify(tokens.sign(ec_key))
    assert principal.subject == tokens.OWNER


def test_ac0_1_rs256_owner_token_is_accepted() -> None:
    key = tokens.rsa_key()
    assert _status(_verifier(CountingFetcher(tokens.jwks(key))), tokens.sign(key)) == 200


def test_ac0_1_forged_signature_is_refused(ec_key: tokens.SigningKey) -> None:
    """AC0.1: a token signed by another key under the same key id answers 401."""
    forger = tokens.ec_key(kid=ec_key.kid)
    verifier = _verifier(CountingFetcher(tokens.jwks(ec_key)))
    assert _status(verifier, tokens.sign(forger)) == 401


@pytest.mark.parametrize("make", [tokens.unsigned, tokens.hs256], ids=["alg-none", "HS256"])
def test_ac0_1_unsigned_and_symmetric_tokens_are_refused(
    ec_key: tokens.SigningKey, make: Any
) -> None:
    """AC0.1: alg=none and HS256 are never accepted."""
    verifier = _verifier(CountingFetcher(tokens.jwks(ec_key)))
    assert _status(verifier, make(ec_key.kid)) == 401


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://other-issuer.test.example"},
        {"aud": "another-api"},
        {"exp": 1_000_000},
        {"iat": None},
        {"sub": None},
        {"nbf": 4_000_000_000},
    ],
    ids=["wrong-issuer", "wrong-audience", "expired", "no-iat", "no-sub", "not-yet-valid"],
)
def test_ac0_1_invalid_claims_are_refused(
    ec_key: tokens.SigningKey, overrides: dict[str, Any]
) -> None:
    """AC0.1: wrong issuer, wrong audience, expired or incomplete tokens answer 401."""
    verifier = _verifier(CountingFetcher(tokens.jwks(ec_key)))
    assert _status(verifier, tokens.sign(ec_key, tokens.claims(**overrides))) == 401


def test_expiry_within_the_60_second_leeway_is_accepted(ec_key: tokens.SigningKey) -> None:
    import time

    payload = tokens.claims(exp=int(time.time()) - 30)
    assert (
        _status(_verifier(CountingFetcher(tokens.jwks(ec_key))), tokens.sign(ec_key, payload))
        == 200
    )


def test_ac0_1_other_subject_is_forbidden(ec_key: tokens.SigningKey) -> None:
    """AC0.1: a valid token for another subject answers 403 (NOT_OWNER)."""
    verifier = _verifier(CountingFetcher(tokens.jwks(ec_key)))
    with pytest.raises(AuthError) as raised:
        verifier.verify(tokens.sign(ec_key, tokens.claims(sub="someone-else")))
    assert (raised.value.status_code, raised.value.code) == (403, "NOT_OWNER")


def test_garbage_and_keyless_tokens_are_refused(ec_key: tokens.SigningKey) -> None:
    verifier = _verifier(CountingFetcher(tokens.jwks(ec_key)))
    assert _status(verifier, "not-a-jwt") == 401
    import jwt as pyjwt

    no_kid = pyjwt.encode(tokens.claims(), ec_key.private_key, algorithm="ES256")
    assert _status(verifier, no_kid) == 401


def test_algorithm_must_match_the_key(ec_key: tokens.SigningKey) -> None:
    """An RS256 token naming an EC key id is refused."""
    rsa = tokens.rsa_key(kid=ec_key.kid)
    verifier = _verifier(CountingFetcher(tokens.jwks(ec_key)))
    assert _status(verifier, tokens.sign(rsa)) == 401


def test_ac0_1_unreachable_key_endpoint_fails_closed(ec_key: tokens.SigningKey) -> None:
    """NFR1.4: when the keys cannot be fetched, the request answers 401."""
    fetcher = CountingFetcher(KeySetUnavailableError("connection refused"))
    with pytest.raises(AuthError) as raised:
        _verifier(fetcher).verify(tokens.sign(ec_key))
    assert raised.value.status_code == 401
    assert "unavailable" in raised.value.message


def test_unparseable_key_set_fails_closed(ec_key: tokens.SigningKey) -> None:
    verifier = _verifier(CountingFetcher({"keys": [{"kty": "oct", "k": "c2VjcmV0"}]}))
    assert _status(verifier, tokens.sign(ec_key)) == 401


def test_ac0_1_repeated_unknown_key_ids_cause_a_single_fetch(ec_key: tokens.SigningKey) -> None:
    """NFR1.4: unknown key ids refresh at most once per 60 seconds."""
    fetcher = CountingFetcher(tokens.jwks(ec_key))
    clock = FakeClock()
    verifier = _verifier(fetcher, clock)
    assert _status(verifier, tokens.sign(ec_key)) == 200
    assert fetcher.calls == 1
    clock.now += 120
    for index in range(5):
        assert _status(verifier, tokens.sign(ec_key, kid=f"unknown-{index}")) == 401
    assert fetcher.calls == 2


def test_keys_are_cached_for_at_most_ten_minutes(ec_key: tokens.SigningKey) -> None:
    fetcher = CountingFetcher(tokens.jwks(ec_key))
    clock = FakeClock()
    verifier = _verifier(fetcher, clock)
    verifier.verify(tokens.sign(ec_key))
    clock.now += 599
    verifier.verify(tokens.sign(ec_key))
    assert fetcher.calls == 1
    clock.now += 2
    verifier.verify(tokens.sign(ec_key))
    assert fetcher.calls == 2


def test_r03_an_issuer_outage_causes_one_fetch_per_interval(ec_key: tokens.SigningKey) -> None:
    """R-03: with a failing key endpoint, requests fail closed without a fetch each time."""
    fetcher = CountingFetcher(KeySetUnavailableError("connection refused"))
    clock = FakeClock()
    verifier = _verifier(fetcher, clock)
    for _ in range(5):
        assert _status(verifier, tokens.sign(ec_key)) == 401
        clock.now += 1
    assert fetcher.calls == 1
    clock.now += 60
    assert _status(verifier, tokens.sign(ec_key)) == 401
    assert fetcher.calls == 2
    fetcher.document = tokens.jwks(ec_key)
    assert _status(verifier, tokens.sign(ec_key)) == 401
    assert fetcher.calls == 2
    clock.now += 60
    assert _status(verifier, tokens.sign(ec_key)) == 200
    assert fetcher.calls == 3


def test_r03_a_failed_refresh_keeps_the_previous_keys(ec_key: tokens.SigningKey) -> None:
    """R-03: an outage while looking up an unknown key id keeps the fresh keys in use."""
    fetcher = CountingFetcher(tokens.jwks(ec_key))
    clock = FakeClock()
    verifier = _verifier(fetcher, clock)
    assert _status(verifier, tokens.sign(ec_key)) == 200
    fetcher.document = KeySetUnavailableError("connection refused")
    clock.now += 61
    assert _status(verifier, tokens.sign(ec_key, kid="unknown")) == 401
    assert fetcher.calls == 2
    for _ in range(3):
        assert _status(verifier, tokens.sign(ec_key)) == 200
    assert fetcher.calls == 2


def test_r03_stale_keys_are_never_used_after_ten_minutes(ec_key: tokens.SigningKey) -> None:
    """NFR1.4: past the 10-minute cache, a failed refresh refuses the request."""
    fetcher = CountingFetcher(tokens.jwks(ec_key))
    clock = FakeClock()
    verifier = _verifier(fetcher, clock)
    assert _status(verifier, tokens.sign(ec_key)) == 200
    fetcher.document = KeySetUnavailableError("connection refused")
    clock.now += 601
    assert _status(verifier, tokens.sign(ec_key)) == 401
    clock.now += 1
    assert _status(verifier, tokens.sign(ec_key)) == 401
    assert fetcher.calls == 2


def test_rotated_key_is_picked_up_on_refresh(ec_key: tokens.SigningKey) -> None:
    new_key = tokens.ec_key(kid="ec-2")
    fetcher = CountingFetcher(tokens.jwks(ec_key))
    clock = FakeClock()
    verifier = _verifier(fetcher, clock)
    verifier.verify(tokens.sign(ec_key))
    fetcher.document = tokens.jwks(ec_key, new_key)
    clock.now += 61
    assert verifier.verify(tokens.sign(new_key)).subject == tokens.OWNER


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer ", "bearer"])
def test_ac0_1_missing_or_malformed_authorization_header(header: str | None) -> None:
    with pytest.raises(AuthError) as raised:
        auth.bearer_token(header)
    assert raised.value.status_code == 401


def test_bearer_token_is_extracted() -> None:
    assert auth.bearer_token("Bearer abc.def.ghi") == "abc.def.ghi"


def test_fetch_jwks_success_and_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    def respond(status: int, body: bytes) -> Any:
        def fake_get(url: str, **_: Any) -> httpx.Response:
            return httpx.Response(status, content=body, request=httpx.Request("GET", url))

        return fake_get

    monkeypatch.setattr(httpx, "get", respond(200, b'{"keys": []}'))
    assert auth.fetch_jwks(JWKS_URL) == {"keys": []}
    for status, body in [(500, b"{}"), (200, b"not json"), (200, b"[1, 2]")]:
        monkeypatch.setattr(httpx, "get", respond(status, body))
        with pytest.raises(KeySetUnavailableError):
            auth.fetch_jwks(JWKS_URL)
