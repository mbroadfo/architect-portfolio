"""Owner authentication (BR1.1, NFR1.1, NFR1.4).

Every slice route depends on ``require_owner``. A request is accepted only when, in order:

1. a bearer token is present;
2. its signing algorithm is on the allow-list (RS256 or ES256; never ``none`` or HS*);
3. its signature verifies against the configured issuer's published signing keys;
4. ``iss`` equals the configured owner issuer and ``aud`` the configured API audience;
5. ``exp``, ``iat``, ``iss``, ``aud`` and ``sub`` are present and the token is not expired
   nor used before its start time (60 seconds of clock skew allowed);
6. ``sub`` equals the configured owner subject.

Failures 1 to 5 answer 401 (UNAUTHENTICATED); failure 6 answers 403 (NOT_OWNER). In every
case no handler runs. Email and name claims are never used. The key set is cached for at
most 10 minutes; an unknown key id triggers at most one refresh per 60 seconds; when the keys
cannot be fetched or parsed, the request is refused (fail closed).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from fastapi import Request

ALLOWED_ALGORITHMS: frozenset[str] = frozenset({"RS256", "ES256"})
REQUIRED_CLAIMS: list[str] = ["exp", "iat", "iss", "aud", "sub"]
LEEWAY_SECONDS = 60
KEY_CACHE_SECONDS = 600
UNKNOWN_KID_REFRESH_SECONDS = 60
JWKS_TIMEOUT_SECONDS = 3.0

Fetcher = Callable[[str], Mapping[str, Any]]


class AuthError(Exception):
    """The request is refused before any handler runs."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def unauthenticated(message: str) -> AuthError:
    """401: no valid owner token."""
    return AuthError(401, "UNAUTHENTICATED", message)


class KeySetUnavailableError(Exception):
    """The issuer's signing keys could not be fetched or parsed."""


def fetch_jwks(url: str) -> Mapping[str, Any]:
    """Fetch the issuer's JSON Web Key Set over HTTP."""
    try:
        response = httpx.get(url, timeout=JWKS_TIMEOUT_SECONDS, follow_redirects=False)
        response.raise_for_status()
        document = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise KeySetUnavailableError(f"cannot fetch the signing keys: {error}") from error
    if not isinstance(document, Mapping):
        raise KeySetUnavailableError("the signing key set is not a JSON object")
    return document


class JwksClient:
    """Caches the issuer's signing keys by key id (NFR1.4).

    - Keys are used for at most ``max_age`` seconds after a successful fetch; after that,
      a request needs a fresh fetch or it is refused (fail closed).
    - A failed refresh keeps the previous keys: a blip while looking up an unknown key id
      does not discard keys that are still fresh.
    - Refresh attempts, successful or not, are made at most once per ``refresh_interval``,
      so an issuer outage cannot turn every request into a blocking fetch.
    """

    def __init__(
        self,
        url: str,
        fetch: Fetcher = fetch_jwks,
        clock: Callable[[], float] = time.monotonic,
        max_age: float = KEY_CACHE_SECONDS,
        refresh_interval: float = UNKNOWN_KID_REFRESH_SECONDS,
    ) -> None:
        self._url = url
        self._fetch = fetch
        self._clock = clock
        self._max_age = max_age
        self._refresh_interval = refresh_interval
        self._keys: dict[str, jwt.PyJWK] | None = None
        self._fetched_at = 0.0
        self._attempted_at: float | None = None
        self._lock = threading.Lock()

    def _load(self) -> dict[str, jwt.PyJWK]:
        try:
            document = self._fetch(self._url)
            key_set = jwt.PyJWKSet.from_dict(dict(document))
        except jwt.PyJWTError as error:
            raise KeySetUnavailableError(f"cannot parse the signing keys: {error}") from error
        return {
            key.key_id: key
            for key in key_set.keys
            if key.key_id and key.key_type in ("EC", "RSA") and key.public_key_use != "enc"
        }

    def _fresh(self, now: float) -> bool:
        return self._keys is not None and now - self._fetched_at < self._max_age

    def _may_attempt(self, now: float) -> bool:
        return self._attempted_at is None or now - self._attempted_at >= self._refresh_interval

    def get_key(self, kid: str) -> jwt.PyJWK | None:
        """Return the key for ``kid``, refreshing when the keys are stale or the id is new.

        Raises KeySetUnavailableError when no fresh key set can be had (fail closed).
        """
        with self._lock:
            now = self._clock()
            fresh = self._fresh(now)
            if (not fresh or kid not in (self._keys or {})) and self._may_attempt(now):
                self._attempted_at = now
                try:
                    keys = self._load()
                except KeySetUnavailableError:
                    if not fresh:
                        raise
                else:
                    self._keys, self._fetched_at, fresh = keys, now, True
            if not fresh:
                raise KeySetUnavailableError(
                    "the signing keys are stale and a refresh is not yet allowed"
                )
            return (self._keys or {}).get(kid)


@dataclass(frozen=True)
class OwnerPrincipal:
    """The verified owner."""

    subject: str


class TokenVerifier:
    """Verifies bearer tokens against the configured owner identity (BR1.1)."""

    def __init__(self, jwks: JwksClient, issuer: str, audience: str, owner_subject: str) -> None:
        self._jwks = jwks
        self._issuer = issuer
        self._audience = audience
        self._owner_subject = owner_subject

    def _key_for(self, token: str) -> tuple[str, jwt.PyJWK]:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as error:
            raise unauthenticated("the token cannot be parsed") from error
        algorithm = header.get("alg")
        if algorithm not in ALLOWED_ALGORITHMS:
            raise unauthenticated("the token's signing algorithm is not allowed")
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid:
            raise unauthenticated("the token has no key id")
        try:
            key = self._jwks.get_key(kid)
        except KeySetUnavailableError as error:
            raise unauthenticated("the issuer's signing keys are unavailable") from error
        if key is None:
            raise unauthenticated("the token's key id is unknown")
        if key.algorithm_name != algorithm:
            raise unauthenticated("the token's algorithm does not match its key")
        return str(algorithm), key

    def verify(self, token: str) -> OwnerPrincipal:
        """Return the owner principal, or raise AuthError (401 or 403)."""
        algorithm, key = self._key_for(token)
        try:
            claims = jwt.decode(
                token,
                key=key.key,
                algorithms=[algorithm],
                audience=self._audience,
                issuer=self._issuer,
                leeway=LEEWAY_SECONDS,
                options={"require": REQUIRED_CLAIMS},
            )
        except jwt.PyJWTError as error:
            raise unauthenticated("the token is not valid for this API") from error
        subject = claims.get("sub")
        if subject != self._owner_subject:
            raise AuthError(403, "NOT_OWNER", "only the owner may use the Studio")
        return OwnerPrincipal(subject=str(subject))


def bearer_token(authorization: str | None) -> str:
    """Extract the token from an ``Authorization: Bearer <token>`` header."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise unauthenticated("a bearer token is required")
    return token.strip()


def require_owner(request: Request) -> OwnerPrincipal:
    """FastAPI dependency attached at router level to every slice route (BR1.1)."""
    verifier: TokenVerifier = request.app.state.token_verifier
    principal = verifier.verify(bearer_token(request.headers.get("Authorization")))
    request.state.owner = principal
    return principal
